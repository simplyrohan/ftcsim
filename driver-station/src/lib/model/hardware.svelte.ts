import type { Station } from './station.svelte';
import type { Device, DriverType } from './types';
import { canonical, copy, defaults, flatten, hardwareError, topology } from './configuration';
import { decodeHardwareMap, encodeHardwareMap, readHardwareFile, MAX_HARDWARE_MAP_BYTES } from './hardware-file';

export class HardwareConfiguration {
  devices = $state<Device[]>([]);
  remote = $state<Device[]>([]);
  catalog = $state<DriverType[]>([]);
  configured = $state(false);
  hasDraft = $state(false);
  hasSaved = $state(false);
  busy = $state(false);
  importing = $state(false);
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
  get ready() { return this.loaded && this.synchronized && !this.busy && !this.importing && !this.error; }
  get count() { return flatten(this.devices).length; }
  get canApply() { return !this.station.robotConfiguration.importing && this.loaded && this.station.canConfigure && !this.busy && !this.importing && !this.error; }
  load(endpoint:string) {
    this.epoch++; this.key = `ftcsim.hardware.v1:${encodeURIComponent(endpoint)}`;
    this.devices = []; this.remote = []; this.configured = false; this.hasDraft = false; this.hasSaved = false; this.notes = ''; this.busy = false; this.importing = false; this.message = ''; this.storageError = ''; this.restorePending = true;
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
  remove(device:Device,parent?:Device) { const list = parent?.children ?? this.devices; list.splice(list.indexOf(device),1); this.save(); }
  async importText(text:string,label='JSON') {
    if (new TextEncoder().encode(text).length > MAX_HARDWARE_MAP_BYTES) throw Error('Files must be at most 1 MiB.');
    const record = decodeHardwareMap(text);
    if (!this.loaded) throw Error('Wait for the driver catalog before importing.');
    const error = hardwareError(record.devices,this.catalog); if (error) throw Error(error);
    this.devices = record.devices; this.notes = record.notes ?? ''; this.save();
    this.message = `Loaded ${label} · ${this.count} devices. Apply the map while stopped.`;
  }
  async importFile(file:File) {
    if (this.importing || this.busy) return;
    const epoch = this.epoch; this.importing = true;
    try { if (file.size > MAX_HARDWARE_MAP_BYTES) throw Error('Files must be at most 1 MiB.'); const text = await readHardwareFile(file); if (epoch === this.epoch) await this.importText(String(text),file.name); }
    catch (error) { if (epoch === this.epoch) this.message = `File not loaded: ${error instanceof Error ? error.message : error}`; }
    finally { if (epoch === this.epoch) this.importing = false; }
  }
  exportFile() {
    if (this.error) { this.message = this.error; return; }
    const url = URL.createObjectURL(new Blob([encodeHardwareMap(this.devices,this.notes)],{type:'application/json'}));
    const link = document.createElement('a'); link.href = url; link.download = 'ftcsim-hardware-map.json'; document.body.append(link); link.click(); link.remove(); setTimeout(()=>URL.revokeObjectURL(url),30000);
    this.message = 'Hardware map saved to file.';
  }
  restore() {
    if (!this.restorePending || !this.loaded || !this.station.helloReceived || !this.station.canConfigure) return;
    this.restorePending = false;
    if (this.hasSaved && !this.sdkSynchronized && !this.error) void this.apply();
  }
  async apply() {
    if (!this.canApply) return;
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
