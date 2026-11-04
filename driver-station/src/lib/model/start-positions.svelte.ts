import { isDrivetrain } from './mechanism-types';
import type { Station } from './station.svelte';

interface StartPose { x_mm:number; y_mm:number; heading_deg:number }
interface ModeStart extends StartPose { enabled:boolean; mechanism:string }
interface Preset extends StartPose { id:string; name:string }
const empty=():ModeStart=>({enabled:false,mechanism:'',x_mm:0,y_mm:0,heading_deg:0});
const valid=(value:any):value is StartPose=>!!value&&['x_mm','y_mm','heading_deg'].every(key=>typeof value[key]==='number'&&Number.isFinite(value[key]));

/** Field placement only. Sensor origins belong to TeamCode, never to the DS. */
export class StartPositions {
  modes=$state<Record<string,ModeStart>>({});
  presets=$state<Preset[]>([]);
  error=$state('');
  busy=$state(false);
  private storageKey='';
  constructor(private station:Station){}
  get current():ModeStart{return this.modes[this.station.selected]??empty();}
  get drivetrains(){return this.station.physical?.mechanisms.filter(item=>isDrivetrain(item.type))??[];}
  get target(){return this.current.mechanism||this.drivetrains[0]?.name||'';}
  get editable(){return !this.station.active&&!this.station.pendingCommand&&!this.busy&&!!this.station.selected;}
  load(endpoint:string){
    this.storageKey=`ftcsim.startPositions.v1:${encodeURIComponent(endpoint)}`;
    this.modes={};this.presets=[];this.error='';
    try {
      const saved=JSON.parse(localStorage.getItem(this.storageKey)||'null');
      if(!saved)return;
      if(saved.version!==1||!saved.modes||!Array.isArray(saved.presets))throw Error('Invalid saved start positions.');
      for(const [name,pose] of Object.entries(saved.modes))if(valid(pose)&&typeof (pose as ModeStart).enabled==='boolean'&&typeof (pose as ModeStart).mechanism==='string')this.modes[name]=pose as ModeStart;
      this.presets=saved.presets.filter((preset:any)=>typeof preset?.id==='string'&&typeof preset?.name==='string'&&valid(preset));
    }catch{this.error='Could not read saved start positions.';}
  }
  private save(){
    try{localStorage.setItem(this.storageKey,JSON.stringify({version:1,modes:this.modes,presets:this.presets}));this.error='';}
    catch{this.error='Could not save start positions. Changes are available in this tab.';}
  }
  update(changes:Partial<ModeStart>){if(!this.editable)return;this.modes[this.station.selected]={...this.current,...changes};this.save();}
  usePreset(id:string){const preset=this.presets.find(item=>item.id===id);if(preset)this.update({x_mm:preset.x_mm,y_mm:preset.y_mm,heading_deg:preset.heading_deg,enabled:true});}
  async savePreset(name:string){
    name=name.trim();if(!name||!valid(this.current)||!this.editable)return false;
    const pose={x_mm:this.current.x_mm,y_mm:this.current.y_mm,heading_deg:this.current.heading_deg};
    const existing=this.presets.find(item=>item.name===name);
    const key=this.storageKey,mode=this.station.selected;
    const allowed=()=>key===this.storageKey&&mode===this.station.selected&&this.editable&&(!existing||this.presets.includes(existing))&&JSON.stringify(pose)===JSON.stringify({x_mm:this.current.x_mm,y_mm:this.current.y_mm,heading_deg:this.current.heading_deg});
    if(existing&&!await this.station.confirmation.ask({title:`Replace preset “${name}”?`,description:'Overwrite this saved start position with the current coordinates and heading.',action:'Replace preset',allowed}))return false;
    if(!allowed())return false;
    this.presets=existing?this.presets.map(item=>item.id===existing.id?{...item,...pose}:item):[...this.presets,{id:crypto.randomUUID(),name,...pose}];
    this.save();return true;
  }
  async deletePreset(id:string){
    const preset=this.presets.find(item=>item.id===id),key=this.storageKey;
    const allowed=()=>key===this.storageKey&&this.editable&&!!preset&&this.presets.includes(preset);
    if(!allowed())return false;
    if(!await this.station.confirmation.ask({title:`Delete preset “${preset!.name}”?`,description:'Remove this named start-position preset from this browser.',action:'Delete preset',details:['Start coordinates already assigned to OpModes are kept.'],allowed})||!allowed())return false;
    this.presets=this.presets.filter(item=>item.id!==id);this.save();return true;
  }
  async place(){
    const pose=this.current;
    if(!valid(pose))throw Error('Enter finite start coordinates and heading.');
    if(!this.station.simulatorConnected)throw Error('Connect the simulator before placing the robot.');
    if(!this.drivetrains.some(item=>item.name===this.target))throw Error('Choose an applied drivetrain for the start position.');
    const response=await fetch('/sim/mechanisms/place',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mechanism:this.target,x_mm:pose.x_mm,y_mm:pose.y_mm,heading_deg:pose.heading_deg}),signal:AbortSignal.timeout(5000)});
    const result=await response.json();if(!response.ok)throw Error(result.message||'Could not place the robot.');
    this.station.physical=result;
  }
  async preview(){
    if(!this.editable)return;this.busy=true;this.error='';
    try{await this.place();}catch(error){this.error=error instanceof Error?error.message:String(error);}
    finally{this.busy=false;}
  }
}
