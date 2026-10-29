/** Small, bounded probes. No telemetry history or per-frame reactive updates. */
export class RoundTrip {
  ms = $state<number|null>(null);
  average = $state<number|null>(null);
  timeouts = $state(0);
  transport = $state('WebSocket');
  private token:number|null=null;
  private started=0;
  private lastStarted=-Infinity;
  private timer?:ReturnType<typeof setTimeout>;
  get due(){return this.token===null && performance.now()-this.lastStarted>=2000;}
  begin(id:number,transport='WebSocket') {
    if(!this.due)return false;
    this.token=id;this.started=this.lastStarted=performance.now();this.transport=transport;
    this.timer=setTimeout(()=>{this.token=null;this.ms=null;this.timeouts++;},3000);
    return true;
  }
  finish(id:number){if(this.token===null||this.token!==id)return;clearTimeout(this.timer);this.token=null;this.ms=performance.now()-this.started;this.average=this.average===null?this.ms:this.average*.75+this.ms*.25;}
  reset(){clearTimeout(this.timer);this.token=null;this.ms=this.average=null;this.lastStarted=-Infinity;}
}
export interface ViewportStats {fps:number;renderMs:number;drawCalls:number;triangles:number;geometries:number;textures:number;modelBuilds:number;active:boolean}
export class Diagnostics {
  sdk=new RoundTrip();
  simulator=new RoundTrip();
  views=$state<Record<string,ViewportStats & {label:string}>>({});
  uiLag=$state(0);
  maxUiLag=$state(0);
  private expected=0;
  private timer?:ReturnType<typeof setInterval>;
  private nextView=0;
  private registrations=new Map<string,number>();
  start(){this.expected=performance.now()+500;this.timer=setInterval(()=>{const now=performance.now();if(!document.hidden){this.uiLag=Math.max(0,now-this.expected);this.maxUiLag=Math.max(this.maxUiLag,this.uiLag);}this.expected=now+500;},500);}
  registerView(label:string){const id=++this.nextView;this.registrations.set(label,id);return {report:(stats:ViewportStats)=>{if(this.registrations.get(label)===id)this.views[label]={label,...stats};},dispose:()=>{if(this.registrations.get(label)===id&&this.views[label])this.views[label]={...this.views[label],fps:0,active:false};}};}
  destroy(){clearInterval(this.timer);this.sdk.reset();this.simulator.reset();this.views={};}
}
export function milliseconds(value:number|null){return value===null?'—':`${value<10?value.toFixed(1):Math.round(value)} ms`;}
