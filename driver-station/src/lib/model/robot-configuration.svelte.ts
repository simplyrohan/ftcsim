import { decodeRobotArchive, encodeRobotArchive, modelPath } from './robot-archive';
import { loadModel, saveModel, readBinaryFile, modelFromBase64, validateGLB, MAX_ROBOT_BYTES } from './model-assets';
import type { Station } from './station.svelte';
import type { Mechanism } from './types';
import { canonical, copy, flatten, hardwareError, mechanismError } from './configuration';
import { decodeHardwareMap, readHardwareFile } from './hardware-file';

export const ROBOT_CONFIGURATION_FORMAT = 'ftcsim.robot-configuration';
const summary=(drivers:number,mechanisms:number)=>`${drivers} driver${drivers===1?'':'s'} and ${mechanisms} mechanism${mechanisms===1?'':'s'}`;

/** A portable snapshot of both editors. Loading changes drafts, never live devices. */
export class RobotConfigurationFile {
  importing = $state(false);
  exporting = $state(false);
  message = $state('');
  constructor(private station:Station) {}
  get busy() { return this.importing || this.exporting || this.station.hardware.busy || this.station.mechanisms.busy; }
  get error() { return this.station.hardware.error || this.station.mechanisms.error; }
  async importText(text:string, label='JSON') {
    if(this.busy)throw Error('Wait for the current configuration operation to finish.');
    this.importing=true;
    try { return await this.importRecord(text,label); } finally { this.importing=false; }
  }
  private async importRecord(text:string, label:string, archiveAssets?:Map<string,ArrayBuffer>) {
    if (this.station.hardware.busy || this.station.mechanisms.busy) throw Error('Wait for configuration changes to finish applying.');
    if (new TextEncoder().encode(text).length > MAX_ROBOT_BYTES) throw Error('Robot configuration files must be smaller than 64 MB.');
    const record = JSON.parse(text);
    if (!record || record.format !== ROBOT_CONFIGURATION_FORMAT || record.version !== (archiveAssets?2:1) || !Array.isArray(record.mechanisms)) throw Error('Expected an ftcsim robot configuration with devices and mechanisms. Load .fs files using Load robot.');
    if (Object.keys(record).some(key=>!['format','version','devices','mechanisms','notes','assets'].includes(key))) throw Error('Unknown robot configuration fields.');
    const hardware = decodeHardwareMap(JSON.stringify({version:1, devices:record.devices, notes:record.notes}));
    const mechanisms:Mechanism[] = record.mechanisms;
    if (mechanisms.length > 64 || mechanisms.some(item=>!item || typeof item !== 'object' || Array.isArray(item) || typeof item.name !== 'string' || typeof item.type !== 'string' || !item.drivers || typeof item.drivers !== 'object' || Array.isArray(item.drivers) || Object.values(item.drivers).some(value=>typeof value !== 'string') || (item.options !== undefined && (!item.options || typeof item.options !== 'object' || Array.isArray(item.options))) || Object.keys(item).some(key=>!['name','type','drivers','options','visual'].includes(key)))) throw Error('Invalid mechanism definitions.');
    const {hardware:hw, mechanisms:mech} = this.station;
    if (!hw.loaded || !mech.loaded) throw Error('Wait for the driver and mechanism catalogs to load.');
    const error = hardwareError(hardware.devices, hw.catalog) || mechanismError(mechanisms, mech.catalog, hardware.devices);
    if (error) throw Error(error);
    const assets=record.assets ?? {};
    if (!assets || typeof assets!=='object' || Array.isArray(assets) || Object.keys(assets).length>64) throw Error('Invalid robot model assets.');
    const referenced=new Set(mechanisms.flatMap(item=>item.visual?.model ? [item.visual.model.id] : []));
    const decoded=new Map<string,ArrayBuffer>();
    for (const id of referenced) {
      if (!Object.hasOwn(assets,id)) throw Error('Robot configuration is missing an embedded GLB model.');
      if(archiveAssets){
        const path=assets[id];
        if(!modelPath(path)||!archiveAssets.has(path))throw Error(`Robot archive is missing model file: ${String(path)}.`);
        const data=archiveAssets.get(path)!;validateGLB(data);decoded.set(id,data);
      } else decoded.set(id,modelFromBase64(assets[id]));
    }
    const endpoint=this.station.endpoint;
    const before=canonical([hw.devices,hw.notes,mech.definitions]);
    const allowed=()=>endpoint===this.station.endpoint&&!hw.busy&&!mech.busy&&canonical([hw.devices,hw.notes,mech.definitions])===before;
    if((hw.devices.length||mech.definitions.length)&&!await this.station.confirmation.ask({title:'Replace robot configuration?',description:`Load “${label}” and replace the configuration saved in this browser.`,action:'Replace configuration',details:[`Replaces ${summary(hw.count,mech.definitions.length)} with ${summary(flatten(hardware.devices).length,mechanisms.length)}.`,'Save a robot file first if you want to keep the current setup.','The SDK and live simulation change only after you apply the imported configuration.'],allowed})){
      this.message='Import cancelled. Current robot configuration kept.';return false;
    }
    if(!allowed())throw Error('The robot configuration changed while loading. Load the file again.');
    // Give imported assets fresh IDs so a rejected import cannot overwrite a live model.
    const imported=new Map<string,string>();
    for (const [id,data] of decoded) { const replacement=crypto.randomUUID(); await saveModel(replacement,data); imported.set(id,replacement); }
    if (endpoint!==this.station.endpoint) throw Error('The SDK connection changed while loading the file. Load it again.');
    if(!allowed())throw Error('The robot configuration changed while loading. Load the file again.');
    for(const item of mechanisms)if(item.visual?.model)item.visual.model.id=imported.get(item.visual.model.id)!;
    // Validate the entire file before replacing either editor, including driver bindings.
    hw.devices = hardware.devices; hw.notes = hardware.notes ?? ''; mech.definitions = mechanisms;
    hw.restorePending = mech.restorePending = false;
    hw.save(); mech.save();
    this.message = `Loaded ${label} · ${hw.count} devices · ${mechanisms.length} mechanisms. Apply hardware first, then mechanisms.`;
    return true;
  }
  async importFile(file:File) {
    if (this.busy) return;
    this.importing = true;
    const endpoint = this.station.endpoint;
    try {
      if (file.size > MAX_ROBOT_BYTES) throw Error('Robot configuration files must be smaller than 64 MB.');
      if(file.name.toLowerCase().endsWith('.json')){
        const text=String(await readHardwareFile(file));
        if(endpoint!==this.station.endpoint)return;
        await this.importRecord(text,file.name);
      } else {
        const archive=await decodeRobotArchive(new Uint8Array(await readBinaryFile(file)));
        if(endpoint!==this.station.endpoint)return;
        await this.importRecord(archive.text,file.name,archive.assets);
      }
    } catch (error) { this.message = `File not loaded: ${error instanceof Error ? error.message : error}`; }
    finally { this.importing = false; }
  }
  async serialize() {
    if (this.error) throw Error(this.error);
    const assets:Record<string,string>={}, models=new Map<string,ArrayBuffer>();
    const devices=copy(this.station.hardware.devices), mechanisms=copy(this.station.mechanisms.definitions), notes=this.station.hardware.notes;
    for(const definition of mechanisms)if(definition.visual?.model){
      const model=definition.visual.model;
      if(!Object.hasOwn(assets,model.id)){
        const path=`models/model-${models.size+1}.glb`,data=await loadModel(model.id);validateGLB(data);
        assets[model.id]=path;models.set(path,data);
      }
    }
    return encodeRobotArchive({format:ROBOT_CONFIGURATION_FORMAT,version:2,...(notes?{notes}:{}),devices,mechanisms,...(models.size?{assets}:{})},models);
  }
  async exportFile() {
    if(this.busy)return;
    this.exporting=true;
    try {
      const url = URL.createObjectURL(new Blob([await this.serialize()],{type:'application/zip'}));
      const link = document.createElement('a'); link.href=url; link.download='ftcsim-robot.fs'; document.body.append(link); link.click(); link.remove(); setTimeout(()=>URL.revokeObjectURL(url),30000);
      this.message = 'Robot archive saved (.fs) with hardware, mechanisms, and GLB model files.';
    } catch (error) { this.message = String(error instanceof Error ? error.message : error); }
    finally { this.exporting=false; }
  }
}
