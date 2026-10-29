import type { ViewportStats } from '$lib/model/diagnostics.svelte';
import { UploadedVisual } from './models';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { MecanumVisual, disposeObject, type MechanismVisual } from './mecanum';
import type { Mechanism, MechanismState, Options } from '$lib/model/types';

// A new mechanism can register its own scene model without changing the viewport.
export const mechanismVisuals = new Map<string,(options:Options)=>MechanismVisual>([
  ['mecanum',options=>new MecanumVisual(options)],
]);
export type CameraView = 'perspective'|'top';

export class DrivebaseViewport {
  private scene=new THREE.Scene();
  private camera=new THREE.PerspectiveCamera(38,1,.01,120);
  private renderer:THREE.WebGLRenderer;
  private controls:OrbitControls;
  private observer:ResizeObserver;
  private intersection?:IntersectionObserver;
  private inView=true;
  private models=new Map<string,{visual:MechanismVisual;signature:string;configuration:string}>();
  private active='';
  private graphicsError='';
  private modelErrors=new Map<string,string>();
  private follow=true;
  private followPosition=new THREE.Vector3();
  private offset=new THREE.Vector3();
  private followInitialized=false;
  private previous=0;
  private visible=true;
  private disposed=false;
  private smooth=!matchMedia('(prefers-reduced-motion: reduce)').matches;
  private enabled=true;
  private maxFPS=60;
  private lastRendered=0;
  private statsSince=0;
  private frameCount=0;
  private renderTime=0;
  private modelBuilds=0;
  private view:CameraView='perspective';
  private visibility=()=>{ this.visible=!document.hidden;this.updateLoop(); };
  private contextLost=(event:Event)=>{event.preventDefault();this.renderer.setAnimationLoop(null);this.graphicsError='The 3D graphics context was lost. Reload this page to restore the viewer.';this.onError(this.graphicsError);};

  constructor(private canvas:HTMLCanvasElement,private onError:(message:string)=>void, private showOrigins=false, private options:{preview?:boolean;onMetrics?:(stats:ViewportStats)=>void}={}) {
    this.renderer=new THREE.WebGLRenderer({canvas,alpha:true,antialias:true,powerPreference:'high-performance'});
    this.renderer.setClearColor(0x000000,0);
    this.maxFPS=options.preview?30:60;
    this.renderer.setPixelRatio(Math.min(devicePixelRatio,options.preview?1:2));
    this.scene.fog=new THREE.Fog(0x0b0b0c,5,17);
    this.scene.add(new THREE.HemisphereLight(0xf0f0ff,0x23232b,2.6));
    const key=new THREE.DirectionalLight(0xffffff,3.2);key.position.set(2,5,3);this.scene.add(key);
    const rim=new THREE.DirectionalLight(0xb7c6e0,1.5);rim.position.set(-3,2,-3);this.scene.add(rim);
    for (const [divisions,opacity] of [[160,.32],[40,.26]]) {
      const grid=new THREE.GridHelper(40,divisions,0x545461,0x393941);
      const materials=Array.isArray(grid.material)?grid.material:[grid.material];
      materials.forEach(material=>{material.transparent=true;material.opacity=opacity;material.depthWrite=false;});
      grid.position.y=divisions===40?.001:0;this.scene.add(grid);
    }
    const origin=new THREE.Mesh(new THREE.RingGeometry(.055,.058,48),new THREE.MeshBasicMaterial({color:0x686875,transparent:true,opacity:.65,side:THREE.DoubleSide}));
    origin.rotation.x=-Math.PI/2;origin.position.y=.003;this.scene.add(origin);
    this.controls=new OrbitControls(this.camera,canvas);
    this.controls.enableDamping=this.smooth;this.controls.dampingFactor=.09;
    this.controls.minDistance=.65;this.controls.maxDistance=24;this.controls.maxPolarAngle=Math.PI/2-.035;
    this.controls.target.set(0,0,0);this.setView('perspective');
    this.observer=new ResizeObserver(()=>this.resize());this.observer.observe(canvas.parentElement!);
    this.resize();
    if(typeof IntersectionObserver!=='undefined'){this.intersection=new IntersectionObserver(entries=>{this.inView=entries[0].isIntersecting;this.updateLoop();});this.intersection.observe(canvas);}
    document.addEventListener('visibilitychange',this.visibility);
    canvas.addEventListener('webglcontextlost',this.contextLost);
    this.visibility();
  }

  private resize() {
    const {width,height}=this.canvas.parentElement!.getBoundingClientRect();
    if (!width || !height) return;
    this.camera.aspect=width/height;this.camera.updateProjectionMatrix();
    this.renderer.setSize(width,height,false);
  }

  sync(mechanisms:MechanismState[],definitions:Mechanism[],selected:string) {
    const present=new Set(mechanisms.map(item=>item.name));
    const definitionsByName=new Map(definitions.map(item=>[item.name,item]));
    const plans=mechanisms.map(mechanism=>{
      const definition=definitionsByName.get(mechanism.name)??{name:mechanism.name,type:mechanism.type,drivers:{}};
      const uploaded=mechanism.type==='custom'||!!definition.visual;
      const options=definition.options??{};
      // Geometry changes need rebuilding only for the procedural drivetrain.
      const geometry=mechanism.type==='mecanum'&&!definition.visual?.model?[options.wheelbase_mm,options.track_width_mm,options.wheel_diameter_mm]:null;
      return {mechanism,definition,uploaded,signature:JSON.stringify([mechanism.type,uploaded,definition.visual?.model?.id,geometry]),configuration:JSON.stringify([options,definition.visual])};
    });
    const rebuilding=plans.some(plan=>this.models.get(plan.mechanism.name)?.signature!==plan.signature)||[...this.models.keys()].some(name=>!present.has(name));
    if(rebuilding)for(const entry of this.models.values())entry.visual.object.removeFromParent();
    for(const [name,entry] of this.models)if(!present.has(name)){entry.visual.dispose();this.models.delete(name);this.modelErrors.delete(name);}
    for(const {mechanism,definition,uploaded,signature,configuration} of plans){
      const factory=mechanismVisuals.get(mechanism.type);if(!factory&&!uploaded)continue;
      let entry=this.models.get(mechanism.name);
      if(entry&&entry.signature!==signature){entry.visual.dispose();this.models.delete(mechanism.name);this.modelErrors.delete(mechanism.name);entry=undefined;}
      if(!entry){
        const visual=uploaded?new UploadedVisual(definition,message=>{this.modelErrors.set(mechanism.name,message);this.reportErrors();}):factory!(definition.options??{});
        entry={visual,signature,configuration};this.models.set(mechanism.name,entry);this.modelBuilds++;
        if(this.showOrigins)(visual.origin??visual.object).add(new THREE.AxesHelper(.12));
      } else if(entry.configuration!==configuration){entry.visual.configure?.(definition);entry.configuration=configuration;}
      entry.visual.update(mechanism);
    }
    for(const [name,entry] of this.models){
      const parent=definitionsByName.get(name)?.visual?.parent;
      const seen=new Set([name]);let ancestor=parent,cycle=false;
      while(ancestor){if(seen.has(ancestor)){cycle=true;break;}seen.add(ancestor);ancestor=definitionsByName.get(ancestor)?.visual?.parent;}
      const owner=!cycle&&parent?this.models.get(parent)?.visual:undefined;
      const target=owner?.origin??owner?.object??this.scene;
      if(entry.visual.object.parent!==target)target.add(entry.visual.object);
    }
    this.reportErrors();
    if(this.active!==selected){this.active=selected;this.followInitialized=false;if(this.follow)this.recenter();}
  }
  private reportErrors(){this.onError([this.graphicsError,...this.modelErrors.values()].filter(Boolean).join(' · '));}
  setActive(enabled:boolean){if(this.enabled===enabled)return;this.enabled=enabled;this.updateLoop();}
  private updateLoop(){this.previous=this.lastRendered=0;this.statsSince=performance.now();this.frameCount=this.renderTime=0;this.renderer.setAnimationLoop(this.visible&&this.enabled&&this.inView&&!this.graphicsError?this.render:null);if(!this.visible||!this.enabled||!this.inView)this.reportMetrics(false);}
  private reportMetrics(active:boolean){this.options.onMetrics?.({fps:active?this.frameCount*1000/Math.max(1,performance.now()-this.statsSince):0,renderMs:this.frameCount?this.renderTime/this.frameCount:0,drawCalls:this.renderer.info.render.calls,triangles:this.renderer.info.render.triangles,geometries:this.renderer.info.memory.geometries,textures:this.renderer.info.memory.textures,modelBuilds:this.modelBuilds,active});}

  private activePosition() { const visual=this.models.get(this.active)?.visual;return visual?(visual.origin ?? visual.object).getWorldPosition(new THREE.Vector3()):undefined; }

  setFollow(enabled:boolean) { if(this.follow===enabled)return;this.follow=enabled;this.followInitialized=false;if(enabled)this.recenter(); }

  setView(view:CameraView) {
    this.view=view;
    const target=this.activePosition() ?? new THREE.Vector3();
    this.controls.target.copy(target);
    this.camera.position.copy(target).add(view==='top'?new THREE.Vector3(0,2.8,.001):new THREE.Vector3(1.45,1.3,1.8));
    this.controls.update();this.followPosition.copy(target);this.followInitialized=true;
  }

  recenter() { this.setView(this.view); }

  private render=(now:number)=>{
    if(this.disposed || !this.visible || !this.enabled || !this.inView)return;
    if(this.lastRendered && now-this.lastRendered<1000/this.maxFPS-1)return;
    this.lastRendered=now;const started=performance.now();
    const dt=this.previous?Math.min((now-this.previous)/1000,.1):0;this.previous=now;
    for(const entry of this.models.values())entry.visual.animate(dt,this.smooth);
    const target=this.activePosition();
    if(this.follow && target){
      if(this.followInitialized){this.offset.copy(target).sub(this.followPosition);this.camera.position.add(this.offset);this.controls.target.add(this.offset);}
      else{this.offset.copy(target).sub(this.controls.target);this.camera.position.add(this.offset);this.controls.target.copy(target);this.followInitialized=true;}
      this.followPosition.copy(target);
    }
    this.controls.update();this.renderer.render(this.scene,this.camera);
    this.frameCount++;this.renderTime+=performance.now()-started;
    if(performance.now()-this.statsSince>=1000){this.reportMetrics(true);this.statsSince=performance.now();this.frameCount=this.renderTime=0;}
  };

  dispose() {
    if(this.disposed)return;this.disposed=true;
    this.renderer.setAnimationLoop(null);this.observer.disconnect();this.intersection?.disconnect();this.controls.dispose();
    document.removeEventListener('visibilitychange',this.visibility);this.canvas.removeEventListener('webglcontextlost',this.contextLost);
    for(const entry of this.models.values())entry.visual.object.removeFromParent();
    for(const entry of this.models.values())entry.visual.dispose();this.models.clear();
    disposeObject(this.scene);this.renderer.dispose();this.renderer.forceContextLoss();
  }
}
