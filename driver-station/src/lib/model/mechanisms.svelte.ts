import { isDrivetrain } from './mechanism-types';
import type { Station } from './station.svelte';
import type { Mechanism, MechanismType } from './types';
import { canonical, copy, defaults, mechanismError, mechanismPhysics } from './configuration';

export class MechanismConfiguration {
  definitions = $state<Mechanism[]>([]);
  catalog = $state<MechanismType[]>([]);
  hasSaved = $state(false);
  busy = $state(false);
  applyMs = $state<number|null>(null);
  serverMs = $state<number|null>(null);
  loaded = $state(false);
  message = $state('');
  storageError = $state('');
  restorePending = true;
  private key = '';
  private epoch = 0;
  constructor(private station:Station) {}
  get error() { return this.loaded ? mechanismError(this.definitions,this.catalog,this.station.hardware.devices) : 'Loading mechanism catalog…'; }
  get synchronized() { const state = this.station.physical; return Boolean(state && !state.mechanism_error && canonical(mechanismPhysics(this.definitions)) === canonical(state.mechanism_configuration) && state.mechanisms.length === this.definitions.length); }
  get canApply() { return !this.station.robotConfiguration.importing && this.loaded && this.station.canConfigure && this.station.hardware.ready && !this.busy && !this.error && !this.synchronized; }
  load(endpoint:string) {
    this.epoch++; this.key = `ftcsim.mechanisms.v1:${encodeURIComponent(endpoint)}`; this.definitions = []; this.hasSaved = false; this.busy = false; this.applyMs=this.serverMs=null; this.message = ''; this.storageError = ''; this.restorePending = true;
    try {
      const text = localStorage.getItem(this.key);
      if (text === null) return;
      const record = JSON.parse(text);
      if (record.version !== 1 || !Array.isArray(record.mechanisms) || record.mechanisms.length > 64 || record.mechanisms.some((item:any) => !item || typeof item.name !== 'string' || typeof item.type !== 'string' || !item.drivers || typeof item.drivers !== 'object' || Array.isArray(item.drivers) || item.options != null && (typeof item.options !== 'object' || Array.isArray(item.options)))) throw Error('Invalid saved mechanism configuration.');
      this.definitions = record.mechanisms; this.hasSaved = true;
      for (const definition of this.definitions) {
        if (definition.type !== 'mecanum' || !definition.options || !('ticks_per_revolution' in definition.options)) continue;
        const old = definition.options.ticks_per_revolution; delete definition.options.ticks_per_revolution;
        if (Object.entries(definition.drivers).some(([slot,name]) => slot !== 'pinpoint' && (this.station.hardware.devices.find(driver => driver.name === name)?.options?.ticks_per_revolution ?? 537.7) !== old)) {
          this.restorePending = false; this.message = 'Review encoder resolution on each motor, then apply this mechanism.';
        }
      }
    } catch (error) { this.storageError = `Cannot read saved mechanisms: ${error instanceof Error ? error.message : error}`; }
  }
  save() {
    this.restorePending = false; this.message = '';
    try { localStorage.setItem(this.key,JSON.stringify({version:1,mechanisms:this.definitions})); this.hasSaved = true; this.storageError = ''; }
    catch { this.hasSaved = false; this.storageError = 'Browser storage is unavailable. Changes remain in this tab.'; }
  }
  storageChanged(key:string|null) { if (key === this.key || key === null) { this.load(this.station.endpoint); this.restorePending = false; this.message = 'Mechanisms changed in another tab. Apply while stopped.'; } }
  add(type:string) {
    const schema = this.catalog.find(item => item.type === type); if (!schema || this.definitions.length >= 64) return;
    let name = type, suffix = 2; while (this.definitions.some(item => item.name === name)) name = `${type}${suffix++}`;
    this.definitions.push({name,type,drivers:{},options:defaults(schema),...(type==='custom'?{visual:{parent:this.definitions.find(item=>isDrivetrain(item.type))?.name??''}}:{})}); this.save();
  }
  async remove(definition:Mechanism) {
    const epoch=this.epoch;
    const allowed=()=>epoch===this.epoch&&!this.busy&&!this.station.robotConfiguration.busy&&this.definitions.includes(definition);
    if(!allowed())return;
    const children=this.definitions.filter(item=>item.visual?.parent===definition.name).map(item=>item.name);
    const details=[...(children.length?[`Attached mechanisms ${children.join(', ')} will need a new origin.`]:[]),'Its drivers remain in the hardware map.','The deletion saves immediately. Update simulation to remove the live mechanism.'];
    if(!await this.station.confirmation.ask({title:`Delete mechanism “${definition.name}”?`,description:'Remove this mechanism, its settings, and its model assignment from your robot configuration.',action:'Delete mechanism',details,allowed})||!allowed())return;
    this.definitions.splice(this.definitions.indexOf(definition),1);this.save();
  }
  restore() {
    if (!this.restorePending || !this.hasSaved || !this.station.physical) return;
    if(this.synchronized){this.restorePending=false;return;}
    if(!this.canApply)return;
    this.restorePending = false; void this.apply({confirm:false});
  }
  async apply({confirm=true}:{confirm?:boolean}={}) {
    if (!this.canApply) return;
    const before=canonical(mechanismPhysics(this.definitions)),currentEpoch=this.epoch;
    const allowed=()=>currentEpoch===this.epoch&&this.canApply&&canonical(mechanismPhysics(this.definitions))===before;
    if(confirm&&this.station.physical?.mechanisms.length&&!await this.station.confirmation.ask({title:'Update simulation?',description:'Recreate the simulation mechanisms using your saved draft.',action:'Update simulation',details:['Drivetrain poses reset to the world origin.','Driver and encoder states are preserved.'],allowed}))return;
    if(!allowed())return;
    this.save(); const epoch = this.epoch, definitions = copy(mechanismPhysics(this.definitions)); this.busy = true; const started=performance.now(); this.serverMs=null;
    try {
      const response = await fetch('/sim/mechanisms',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mechanisms:definitions}),signal:AbortSignal.timeout(7000)});
      const timing=response.headers?.get('Server-Timing')?.match(/mechanisms;dur=([\d.]+)/);
      const state = await response.json();
      if (epoch !== this.epoch) return;
      if(timing)this.serverMs=Number(timing[1]);
      if (!response.ok) throw Error(state.message || 'Simulator rejected configuration.');
      if (epoch !== this.epoch) return;
      if (state.mechanism_error || canonical(state.mechanism_configuration) !== canonical(definitions) || state.mechanisms?.length !== definitions.length) throw Error('Simulator did not confirm the configuration.');
      this.station.physical = state; this.message = `Simulation updated · ${Math.round(performance.now()-started)} ms. Drivetrain pose reset; model files stay in this browser.`; this.station.log(this.message);
    } catch (error) { if (epoch === this.epoch) { const reason=error instanceof Error&&['TimeoutError','AbortError'].includes(error.name)?'The simulator did not reply within 7 seconds. Check its connection and the Performance panel.':error instanceof Error?error.message:String(error);this.message = `Simulation not updated: ${reason}`; this.station.log(this.message,'error'); } }
    finally { if (epoch === this.epoch) { this.applyMs=performance.now()-started; this.busy = false; } }
  }
}
