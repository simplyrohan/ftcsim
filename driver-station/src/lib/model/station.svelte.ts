import { Diagnostics } from './diagnostics.svelte';
import { RobotConfigurationFile } from './robot-configuration.svelte';
import { HardwareConfiguration } from './hardware.svelte';
import { MechanismConfiguration } from './mechanisms.svelte';
import { Gamepads } from './gamepads.svelte';
import type { LogEntry, OpMode, PhysicalState } from './types';
import { copy } from './configuration';

export class Station {
  endpoint = $state('');
  connected = $state(false);
  simulatorConnected = $state(false);
  controller = $state(false);
  connecting = $state(false);
  status = $state('disconnected');
  selected = $state('');
  opmodes = $state<OpMode[]>([]);
  elapsed = $state(0);
  error = $state('');
  notice = $state('');
  pendingCommand = $state('');
  physical = $state<PhysicalState|null>(null);
  telemetry = $state<Record<string,unknown>>({});
  telemetryFormat = $state('MONOSPACE');
  events = $state<LogEntry[]>([]);
  diagnostics = new Diagnostics();
  helloReceived = false;
  hardware = new HardwareConfiguration(this);
  mechanisms = new MechanismConfiguration(this);
  robotConfiguration = new RobotConfigurationFile(this);
  gamepads = new Gamepads();
  private sdk:WebSocket|null = null;
  private simulator:WebSocket|null = null;
  private requests = new Map<number,{resolve:(data:any)=>void; reject:(error:Error)=>void; timer:ReturnType<typeof setTimeout>}>();
  private sequence = 0;
  private eventId = 0;
  private destroyed = false;
  private reconnectTimer?:ReturnType<typeof setTimeout>;
  private intervals:ReturnType<typeof setInterval>[] = [];
  get active() { return ['initialized','running'].includes(this.status); }
  get canConfigure() { return this.connected && this.controller && !['connecting','disconnected','initialized','running'].includes(this.status); }
  get canInit() { return this.connected && this.controller && !this.active && this.hardware.ready && !this.pendingCommand; }
  get canStart() { return this.connected && this.controller && this.status === 'initialized' && !this.pendingCommand; }
  get initReason() { return !this.connected ? 'Connect the Robot Controller to continue.' : !this.controller ? 'This tab is observing. Reconnect after the controller tab closes.' : this.active ? 'Stop this OpMode before initializing again.' : this.hardware.busy ? 'Applying the hardware map…' : !this.hardware.ready ? this.hardware.error || 'Apply your hardware map in Settings before INIT.' : this.pendingCommand ? 'Waiting for the Robot Controller…' : 'Ready to initialize.'; }
  log(message:string,level:'info'|'error'='info') { this.events = [...this.events.slice(-199),{id:++this.eventId,time:new Date().toLocaleTimeString('en-US',{hour12:false}),message,level}]; }
  async mount() {
    this.destroyed = false; this.diagnostics.start();
    let saved = ''; try { saved = localStorage.getItem('ftcsim.sdkEndpoint') || ''; } catch { /* Configuration models report storage errors. */ }
    const port = new URLSearchParams(location.search).get('sdk');
    this.endpoint = port ? `ws://${location.hostname}:${port}/ds` : import.meta.env.DEV ? __SDK_PROXY_TARGET__ : saved || `ws://${location.hostname}:1115/ds`;
    this.gamepads.focused = document.hasFocus();
    this.connect(); this.connectPhysical();
    this.intervals = [setInterval(()=>this.probeConnections(),2000),setInterval(()=>this.heartbeat(),250),setInterval(()=>{
      if (!this.connected || !this.controller) return;
      const [gamepad1,gamepad2] = this.gamepads.sample();
      const id=++this.sequence, probe=!document.hidden && this.diagnostics.sdk.begin(id,'WebSocket control ACK');
      if(!this.send({type:'gamepads',gamepad1,gamepad2,...(probe?{id}:{})}) && probe)this.diagnostics.sdk.reset();
    },50)];
    await this.loadCatalogs();
  }
  async loadCatalogs() {
    await Promise.all([
      (async()=>{try { const response = await fetch('/sim/driver-types',{cache:'no-store'}); if (!response.ok) throw Error('Cannot load driver catalog.'); this.hardware.catalog = await response.json(); this.hardware.loaded = true; this.restore(); } catch(error) { this.hardware.message = String(error); this.log(String(error),'error'); }})(),
      (async()=>{try { const response = await fetch('/sim/mechanism-types',{cache:'no-store'}); if (!response.ok) throw Error('Cannot load mechanism catalog.'); this.mechanisms.catalog = await response.json(); this.mechanisms.loaded = true; this.restore(); } catch(error) { this.mechanisms.message = String(error); this.log(String(error),'error'); }})()
    ]);
  }
  connect() {
    let endpoint:string;
    try { const url = new URL(this.endpoint); if (!['ws:','wss:'].includes(url.protocol)) throw Error('Use a ws:// or wss:// address.'); endpoint = url.href; }
    catch(error) { this.notice = String(error); return; }
    this.disconnect(); this.endpoint = endpoint; this.connecting = true; this.status = 'connecting'; this.error = ''; this.notice = ''; this.telemetry = {}; this.helloReceived = false;
    this.hardware.load(endpoint); this.mechanisms.load(endpoint);
    try { localStorage.setItem('ftcsim.sdkEndpoint',endpoint); } catch { /* Drafts still work in this tab. */ }
    const address = import.meta.env.DEV && endpoint === __SDK_PROXY_TARGET__ ? `${location.protocol === 'https:'?'wss:':'ws:'}//${location.host}/sdk` : endpoint;
    const socket = this.sdk = new WebSocket(address);
    socket.onopen = () => { if (this.sdk !== socket) return; this.connected = true; this.connecting = false; this.log('Robot Controller connected.'); };
    socket.onclose = () => { if (this.sdk !== socket) return; this.diagnostics.sdk.reset(); this.connected = this.controller = this.connecting = false; this.status = 'disconnected'; this.pendingCommand = ''; this.gamepads.reset(); this.failRequests(); this.log('Robot Controller disconnected.','error'); };
    socket.onerror = () => { if (this.sdk === socket) this.notice = 'Cannot reach the Robot Controller. Start runSimulator, then reconnect.'; };
    socket.onmessage = event => {
      if (this.sdk !== socket) return;
      try { this.receive(JSON.parse(event.data)); } catch(error) { this.log(`Invalid controller message: ${error}`,'error'); }
    };
  }
  private receive(data:any) {
    if (data.type === 'role') { this.controller = data.controller === true; this.heartbeat(); }
    if (data.type === 'hello') { this.opmodes = data.opmodes; this.hardware.remote = copy(data.devices); this.hardware.configured = data.hardwareConfigured === true; this.helloReceived = true; }
    if (data.type === 'status') {
      const previous = this.status;
      this.status = data.state; this.selected = data.selected; this.elapsed = data.elapsed; this.error = data.error;
      if (previous !== this.status) { this.log(`OpMode ${this.status}${this.error ? ` · ${this.error}` : ''}`,this.error?'error':'info'); if (!this.active) this.gamepads.reset(); }
    }
    if (data.type === 'telemetry') this.telemetry = data.data;
    if (data.type === 'command' && data.name === 'CMD_SET_TELEMETRY_DISPLAY_FORMAT') this.telemetryFormat = data.extra;
    if (data.type === 'error' || data.type === 'ack') {
      if(data.type==='ack')this.diagnostics.sdk.finish(data.id);
      const waiting = this.requests.get(data.id);
      if (waiting) { clearTimeout(waiting.timer); this.requests.delete(data.id); if (data.type === 'error') waiting.reject(Error(data.message)); else waiting.resolve(data); }
      else if (data.type === 'error') { this.notice = data.message; this.log(data.message,'error'); }
    }
    this.restore();
  }
  private restore() { this.hardware.restore(); this.mechanisms.restore(); }
  send(data:Record<string,unknown>) { if (this.sdk?.readyState !== WebSocket.OPEN) return false; this.sdk.send(JSON.stringify(data)); return true; }
  request(data:Record<string,unknown>):Promise<any> {
    return new Promise((resolve,reject)=>{
      const id = ++this.sequence;
      const timer = setTimeout(()=>{this.requests.delete(id);reject(Error('Controller response timed out. Reconnect and try again.'));},7000);
      this.requests.set(id,{resolve,reject,timer});
      if (!this.send({...data,id})) { clearTimeout(timer); this.requests.delete(id); reject(Error('Controller is disconnected.')); }
    });
  }
  async command(type:'init'|'start'|'stop') {
    if (!this.controller || !this.connected || this.pendingCommand && type !== 'stop' || type === 'init' && !this.canInit || type === 'start' && !this.canStart) return;
    this.pendingCommand = type; this.notice = '';
    if (type === 'stop' || type === 'init') this.gamepads.reset();
    try { this.heartbeat(); await this.request({type}); this.notice = type === 'stop' ? 'Stopped. Press INIT to run again.' : `${type === 'init'?'INIT':'START'} accepted.`; }
    catch(error) { this.notice = error instanceof Error ? error.message : String(error); this.log(this.notice,'error'); }
    finally { this.pendingCommand = ''; }
  }
  async select(name:string) { try { await this.request({type:'select',name}); } catch(error) { this.notice = String(error); } }
  heartbeat() { if (this.controller && this.connected) this.send({type:'heartbeat'}); }
  focus(focused:boolean) { this.gamepads.focused = focused; if (!focused) this.gamepads.reset(); else this.heartbeat(); }
  private connectPhysical() {
    if (this.destroyed) return;
    const socket = this.simulator = new WebSocket(`${location.protocol==='https:'?'wss:':'ws:'}//${location.host}/sim/drivers`);
    socket.onopen = () => { if (this.simulator === socket) this.simulatorConnected = true; };
    socket.onmessage = event => {
      if (this.simulator !== socket) return;
      try { const data = JSON.parse(event.data); if (data.type === 'state') { this.physical = data; this.restore(); } else if(data.type==='pong')this.diagnostics.simulator.finish(data.id); else if (data.type === 'error') this.notice = data.message; } catch(error) { this.log(`Invalid simulator message: ${error}`,'error'); }
    };
    socket.onclose = () => { if (this.simulator !== socket) return; this.diagnostics.simulator.reset(); this.simulatorConnected = false; this.physical = null; this.mechanisms.restorePending = true; if (!this.destroyed) this.reconnectTimer = setTimeout(()=>this.connectPhysical(),1000); };
    socket.onerror = () => socket.close();
  }
  private probeConnections() {
    if(document.hidden)return;
    if(this.simulator?.readyState===WebSocket.OPEN){const id=++this.sequence;if(this.diagnostics.simulator.begin(id))this.simulator.send(JSON.stringify({type:'ping',id}));}
    // Observers cannot send control frames. The SDK already serves a tiny HTTP service response.
    if(this.connected && !this.controller){
      const id=++this.sequence;
      if(this.diagnostics.sdk.begin(id,'HTTP (observer)')){
        const socket=this.sdk, endpoint=new URL(this.endpoint);
        endpoint.protocol=endpoint.protocol==='wss:'?'https:':'http:';
        const address=import.meta.env.DEV && this.endpoint===__SDK_PROXY_TARGET__?'/sdk':endpoint.href;
        void fetch(address,{mode:'no-cors',cache:'no-store',credentials:'omit',signal:AbortSignal.timeout(2500)}).then(()=>{if(this.sdk===socket)this.diagnostics.sdk.finish(id);}).catch(()=>{/* Probe expires independently; do not disturb robot controls. */});
      }
    }
  }
  motion(vx:number,vy:number,yaw:number) { if (this.simulator?.readyState === WebSocket.OPEN) this.simulator.send(JSON.stringify({type:'motion',vx,vy,angular_velocity:yaw*Math.PI/180})); }
  async waitFor(predicate:()=>boolean,timeout:number) {
    const start = Date.now();
    while (!predicate()) { if (this.destroyed || !this.connected) throw Error('Controller disconnected.'); if (Date.now()-start>timeout) throw Error('Simulator did not create the matching devices. Check its SDK connection.'); await new Promise(resolve=>setTimeout(resolve,50)); }
  }
  private failRequests() { for (const item of this.requests.values()) { clearTimeout(item.timer); item.reject(Error('Controller connection closed.')); } this.requests.clear(); }
  private disconnect() { this.diagnostics.sdk.reset(); const socket = this.sdk; this.sdk = null; socket?.close(); this.connected = this.controller = false; this.pendingCommand = ''; this.gamepads.reset(); this.failRequests(); }
  destroy() { this.diagnostics.destroy(); this.destroyed = true; this.disconnect(); clearTimeout(this.reconnectTimer); this.intervals.forEach(clearInterval); const socket = this.simulator; this.simulator = null; this.simulatorConnected = false; socket?.close(); }
}
