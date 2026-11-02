import type { Station } from './station.svelte';
import type { Device, DriverType } from './types';
import { canonical, copy, defaults, flatten, hardwareError, topology } from './configuration';
import { decodeHardwareMap } from './hardware-file';

export class HardwareConfiguration {
  devices = $state<Device[]>([]);
  remote = $state<Device[]>([]);
  catalog = $state<DriverType[]>([]);
  configured = $state(false);
  hasDraft = $state(false);
  hasSaved = $state(false);
  busy = $state(false);
  notes = $state('');
  message = $state('');
  storageError = $state('');
  loaded = $state(false);
  restorePending = true;
  private key = '';
  private epoch = 0;
  constructor(private station:Station) {}
  get error() { return this.loaded ? hardwareError(this.devices,this.catalog) : 'Loading driver catalog…'; }
  get sdkSynchronized() { return this.hasDraft && this.configured && canonical(this.devices) === canonical(this.remote); }
  get synchronized() { return this.sdkSynchronized && this.station.physical?.connected === true && topology(this.devices) === topology(this.station.physical.devices); }
  get ready() { return this.loaded && this.synchronized && !this.busy && !this.error; }
  get count() { return flatten(this.devices).length; }
  get canApply() { return !this.station.robotConfiguration.importing && this.loaded && this.station.canConfigure && !this.busy && !this.error; }
  load(endpoint:string) {
    this.epoch++; this.key = `ftcsim.hardware.v1:${encodeURIComponent(endpoint)}`;
    this.devices = []; this.remote = []; this.configured = false; this.hasDraft = false; this.hasSaved = false; this.notes = ''; this.busy = false; this.message = ''; this.storageError = ''; this.restorePending = true;
    try {
      const text = localStorage.getItem(this.key);
      if (text !== null) { const record = decodeHardwareMap(text); this.devices = record.devices; this.notes = record.notes ?? ''; this.hasDraft = this.hasSaved = true; }
    } catch (error) { this.storageError = `Cannot read saved map: ${error instanceof Error ? error.message : error}`; }
  }
  save() {
    this.hasDraft = true; this.message = '';
    try { localStorage.setItem(this.key,JSON.stringify({version:1,devices:this.devices,notes:this.notes})); this.hasSaved = true; this.storageError = ''; }
    catch { this.hasSaved = false; this.storageError = 'Browser storage is unavailable. Save this map to a file before closing.'; }
  }
  storageChanged(key:string|null) { if (key === this.key || key === null) { this.load(this.station.endpoint); this.restorePending = false; this.message = 'Map changed in another tab. Apply the draft while stopped.'; } }
  add(type:string, parent?:Device, port?:string) {
    const schema = this.catalog.find(item => item.type === type); if (!schema) return;
    const names = new Set(flatten(this.devices).map(device => device.name));
    const stem = parent ? `${parent.name}_${port}` : type; let name = stem, suffix = 2;
    while (names.has(name)) name = `${stem}${suffix++}`;
    const options = defaults(schema);
    if (parent) {
      Object.assign(options,this.catalog.find(item => item.type === parent.type)?.child_defaults[port!] ?? {});
      const device = {name,type,port:port!,options}; (parent.children ??= []).push(device); this.save(); return device;
    }
    const used = (candidate:number) => this.devices.some(device => device.module === 1 && device.port === candidate && (this.catalog.find(item => item.type === device.type)?.connection === schema.connection || ['motor','encoder'].includes(schema.connection) && ['motor','encoder'].includes(this.catalog.find(item => item.type === device.type)?.connection ?? '')));
    const device:Device = {name,type,module:1,port:Array.from({length:schema.ports},(_,i)=>i).find(port => !used(port)) ?? 0,options};
    this.devices.push(device);
    for (const port of schema.child_ports) { const child = this.catalog.find(item => item.connection === schema.child_connections[port]); if (child) this.add(child.type,device,port); }
    this.save(); return device;
  }
  async remove(device:Device,parent?:Device) {
    const epoch=this.epoch,list=parent?.children??this.devices;
    const allowed=()=>epoch===this.epoch&&!this.busy&&!this.station.robotConfiguration.busy&&list.includes(device);
    if(!allowed())return;
    const removed=flatten([device]),names=new Set([...removed.map(item=>item.name),...(parent?[parent.name]:[])]);
    const affected=this.station.mechanisms.definitions.filter(item=>Object.values(item.drivers).some(name=>names.has(name))).map(item=>item.name);
    const details=[...(removed.length>1?[`Also deletes connected encoders: ${removed.slice(1).map(item=>item.name).join(', ')}.`]:[]),...(affected.length?[`Used by ${affected.join(', ')}. Review these mechanisms’ driver connections afterward.`]:[]),'The deletion saves immediately. Apply the hardware map to update the SDK.'];
    if(!await this.station.confirmation.ask({title:`Delete driver “${device.name}”?`,description:'Remove this driver from your robot configuration.',action:'Delete driver',details,allowed})||!allowed())return;
    list.splice(list.indexOf(device),1);this.save();
  }
  restore() {
    if (!this.restorePending || !this.loaded || !this.station.helloReceived || !this.station.canConfigure) return;
    this.restorePending = false;
    if (this.hasSaved && !this.sdkSynchronized && !this.error) void this.apply({confirm:false});
  }
  async apply({confirm=true}:{confirm?:boolean}={}) {
    if (!this.canApply) return;
    const before=canonical(this.devices),currentEpoch=this.epoch;
    const allowed=()=>currentEpoch===this.epoch&&this.canApply&&canonical(this.devices)===before;
    if(confirm&&this.configured&&!await this.station.confirmation.ask({title:'Replace SDK hardware?',description:'Apply this hardware map and recreate the SDK’s drivers.',action:'Apply hardware map',details:['Current driver state, including encoder readings and Pinpoint position, will reset.','Your saved configuration and mechanism model files are kept.'],allowed}))return;
    if(!allowed())return;
    this.save(); const epoch = this.epoch, devices = copy(this.devices); this.busy = true;
    try {
      await this.station.request({type:'configure',devices});
      if (epoch !== this.epoch) return;
      if (!this.configured || canonical(devices) !== canonical(this.remote)) throw Error('SDK did not confirm this map. Restart the SDK and reconnect.');
      await this.station.waitFor(()=>this.station.physical?.connected === true && topology(devices) === topology(this.station.physical.devices),3000);
      if (epoch === this.epoch) { this.message = `Applied ${flatten(devices).length} devices to the SDK.`; this.station.log(this.message); }
    } catch (error) { if (epoch === this.epoch) { this.message = `Map not applied: ${error instanceof Error ? error.message : error}`; this.station.log(this.message,'error'); } }
    finally { if (epoch === this.epoch) { this.busy = false; this.station.mechanisms.restore(); } }
  }
}
