import { isDrivetrain } from '$lib/model/mechanism-types';
import * as THREE from 'three';
import { createGLTFLoader } from './gltf';
import { loadModel, validateGLB } from '$lib/model/model-assets';
import type { Mechanism, MechanismState } from '$lib/model/types';
import { DrivebaseVisual, disposeObject, type MechanismVisual } from './drivetrain';

export async function parseModel(data:ArrayBuffer) {
  validateGLB(data);
  const manager=new THREE.LoadingManager();
  manager.setURLModifier(url=>{if(!url.startsWith('blob:') && !url.startsWith('data:'))throw Error('The GLB contains an external resource. Embed textures and buffers before uploading.');return url;});
  const {loader,decoder}=createGLTFLoader(manager);
  try {return (await loader.parseAsync(data,'')).scene;}
  finally {decoder.dispose();}
}
const axisVectors={x:new THREE.Vector3(1,0,0),y:new THREE.Vector3(0,0,-1),z:new THREE.Vector3(0,1,0)};
const basis=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),-Math.PI/2);
function robotRotation(values:number[]=[0,0,0]) {
  return basis.clone().multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(...values.map(value=>THREE.MathUtils.degToRad(Number.isFinite(value)?value:0)) as [number,number,number],'ZYX'))).multiply(basis.clone().invert());
}

/** Preserve the uploaded origin: placement → actuator motion → unmodified GLB. */
export class UploadedVisual implements MechanismVisual {
  object=new THREE.Group();
  origin=new THREE.Group();
  private mount=new THREE.Group();
  private target=new THREE.Vector3();
  private heading=0;
  private amount=0;
  private displayed=0;
  private initialized=false;
  private disposed=false;
  private procedural?:DrivebaseVisual;
  private model?:THREE.Group;
  private modelScale=new THREE.Vector3(1,1,1);
  constructor(private definition:Mechanism, onError:(message:string)=>void, onLoading:(loading:boolean)=>void=()=>{}) {
    this.object.name=definition.name;
    this.object.add(this.mount);this.mount.add(this.origin);
    const visual=definition.visual ?? {};
    if(visual.model){onLoading(true);void loadModel(visual.model.id).then(parseModel).then(model=>{
      if(this.disposed){disposeObject(model);return;}
      // Uploaded node transforms are static; movement is applied to the mechanism pivot.
      model.traverse(node=>{node.updateMatrix();node.matrixAutoUpdate=false;});
      this.model=model;this.modelScale.copy(model.scale);this.applyScale();this.origin.add(model);
    }).catch(error=>{if(!this.disposed)onError(`${definition.name}: ${error instanceof Error?error.message:error}`);}).finally(()=>{if(!this.disposed)onLoading(false);});}
    else if(isDrivetrain(definition.type)){this.procedural=new DrivebaseVisual(definition.options,definition.type);this.origin.add(this.procedural.object);}
    else {
      const marker=new THREE.AxesHelper(.15);this.origin.add(marker);
      const pivot=new THREE.Mesh(new THREE.SphereGeometry(.012,12,8),new THREE.MeshStandardMaterial({color:0xa9ccf2}));this.origin.add(pivot);
    }
    this.configure(definition);
  }
  configure(definition:Mechanism) {
    // Keep Three.js objects outside Svelte's deep reactive graph.
    this.definition={...definition,options:{...definition.options},visual:definition.visual?{...definition.visual,position:[...(definition.visual.position??[0,0,0])],rotation:[...(definition.visual.rotation??[0,0,0])]}:undefined};
    const visual=this.definition.visual??{},position=visual.position??[0,0,0];
    this.mount.position.set(Number.isFinite(position[0])?position[0]/1000:0,Number.isFinite(position[2])?position[2]/1000:0,Number.isFinite(position[1])?-position[1]/1000:0);
    this.mount.quaternion.copy(robotRotation(visual.rotation));this.applyScale();
  }
  private applyScale(){const value=this.definition.visual?.scale,scale=typeof value==='number' && Number.isFinite(value) && value>0?value:1;if(this.model){this.model.scale.copy(this.modelScale).multiplyScalar(scale);this.model.updateMatrix();}if(this.procedural)this.procedural.object.scale.setScalar(scale);}
  update(mechanism:MechanismState) {
    if(isDrivetrain(this.definition.type)){
      const pose=mechanism.state.pose;
      if(pose && [pose.x_mm,pose.y_mm,pose.heading_rad].every(Number.isFinite)){
        this.target.set(pose.x_mm/1000,0,-pose.y_mm/1000);this.heading=pose.heading_rad;
        if(!this.initialized){this.object.position.copy(this.target);this.object.rotation.y=this.heading;}
      }
    } else this.amount=Number.isFinite(mechanism.state.displacement)?mechanism.state.displacement:0;
    this.procedural?.update({...mechanism,state:{...mechanism.state,pose:{x_mm:0,y_mm:0,heading_rad:0}}});
    if(!this.initialized){this.displayed=this.amount;this.initialized=true;}
  }
  animate(dt:number,smooth:boolean) {
    this.procedural?.animate(dt,smooth);
    const blend=smooth?1-Math.exp(-dt*18):1;
    if(isDrivetrain(this.definition.type)){
      this.object.position.lerp(this.target,blend);
      const delta=this.heading-this.object.rotation.y;this.object.rotation.y+=Math.atan2(Math.sin(delta),Math.cos(delta))*blend;
    } else {
      this.displayed+=(this.amount-this.displayed)*blend;
      const axis=axisVectors[this.definition.options?.axis as keyof typeof axisVectors] ?? axisVectors.z;
      this.origin.position.set(0,0,0);this.origin.quaternion.identity();
      if((this.definition.options?.motion??'rotation')==='rotation')this.origin.quaternion.setFromAxisAngle(axis,THREE.MathUtils.degToRad(this.displayed));
      else this.origin.position.copy(axis).multiplyScalar(this.displayed/1000);
    }
  }
  dispose(){this.disposed=true;disposeObject(this.object);}
}
