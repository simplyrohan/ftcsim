import * as THREE from 'three';
import type { MechanismState, Options } from '$lib/model/types';

export interface MechanismVisual {
  object:THREE.Group;
  origin?:THREE.Object3D;
  configure?(definition:import('$lib/model/types').Mechanism):void;
  update(mechanism:MechanismState):void;
  animate(dt:number, smooth:boolean):void;
  dispose():void;
}

export function disposeObject(object:THREE.Object3D) {
  const geometries = new Set<THREE.BufferGeometry>(), materials = new Set<THREE.Material>();
  object.traverse(node=>{
    const mesh = node as THREE.Mesh;
    if (mesh.geometry) geometries.add(mesh.geometry);
    if (mesh.material) for (const material of Array.isArray(mesh.material)?mesh.material:[mesh.material]) materials.add(material);
  });
  geometries.forEach(geometry=>geometry.dispose());
  const textures=new Set<THREE.Texture>();
  for(const material of materials)for(const value of Object.values(material))if(value instanceof THREE.Texture)textures.add(value);
  textures.forEach(texture=>{const source=texture.source?.data;if(typeof ImageBitmap!=='undefined' && source instanceof ImageBitmap)source.close();texture.dispose();});
  materials.forEach(material=>material.dispose());
  object.removeFromParent();
}

/** A generic mecanum chassis. FTC +X/+Y maps to Three.js +X/-Z, with +Y up. */
export class MecanumVisual implements MechanismVisual {
  object = new THREE.Group();
  private target = new THREE.Vector3();
  private heading = 0;
  private initialized = false;
  private wheels = new Map<string,THREE.Group>();
  private speeds:Record<string,number> = {};
  private radius:number;

  constructor(options:Options = {}) {
    const length = (options.wheelbase_mm ?? 360)/1000;
    const width = (options.track_width_mm ?? 360)/1000;
    this.radius = (options.wheel_diameter_mm ?? 96)/2000;
    const frame = new THREE.MeshStandardMaterial({color:0x36363e,metalness:.65,roughness:.42});
    const deck = new THREE.MeshStandardMaterial({color:0x202025,metalness:.5,roughness:.5});
    const rubber = new THREE.MeshStandardMaterial({color:0x111115,roughness:.9});
    const metal = new THREE.MeshStandardMaterial({color:0xa0a0ad,metalness:.65,roughness:.45});
    const edges = new THREE.LineBasicMaterial({color:0xb6b6c2,transparent:true,opacity:.45});
    const box = (x:number,y:number,z:number, sx:number,sy:number,sz:number, material:THREE.Material, outline=false) => {
      const geometry = new THREE.BoxGeometry(sx,sy,sz);
      const mesh = new THREE.Mesh(geometry,material); mesh.position.set(x,y,z); this.object.add(mesh);
      if (outline) mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(geometry),edges));
      return mesh;
    };
    const base = this.radius+.045;
    box(0,base,0,length+.07,.055,width-.045,frame,true);
    box(0,base+.095,0,length+.025,.014,width-.07,deck,true);
    for (const x of [-length*.4,length*.4]) for (const z of [-width*.36,width*.36]) {
      const post = new THREE.Mesh(new THREE.CylinderGeometry(.008,.008,.1,8),metal);
      post.position.set(x,base+.05,z);this.object.add(post);
    }
    box(-length*.13,base+.118,0,length*.3,.032,width*.3,frame,true);
    box(length*.24,base+.111,0,.055,.02,.075,deck,true);
    // Direction arrow on the top deck points forward in the model's local +X.
    const arrow = new THREE.ArrowHelper(new THREE.Vector3(1,0,0),new THREE.Vector3(-.06,base+.132,0),.16,0xd1d1db,.035,.026);
    this.object.add(arrow);
    box(length/2+.037,base,0,.004,.008,width*.62,new THREE.MeshBasicMaterial({color:0xb8d2f4}));
    const placements = [
      ['front_left',length/2,-width/2,1],['front_right',length/2,width/2,-1],
      ['rear_left',-length/2,-width/2,-1],['rear_right',-length/2,width/2,1],
    ] as const;
    for (const [name,x,z,handedness] of placements) {
      const wheel = new THREE.Group();wheel.name=name;wheel.position.set(x,this.radius,z);
      const tire = new THREE.Mesh(new THREE.CylinderGeometry(this.radius*.88,this.radius*.88,.044,24),rubber);
      tire.rotation.x=Math.PI/2;wheel.add(tire);
      const hub = new THREE.Mesh(new THREE.CylinderGeometry(this.radius*.46,this.radius*.46,.047,16),metal);
      hub.rotation.x=Math.PI/2;wheel.add(hub);
      const rollerGeometry = new THREE.CylinderGeometry(this.radius*.16,this.radius*.16,.046,8);
      for (let i=0;i<8;i++) {
        const angle=i*Math.PI/4;
        const roller=new THREE.Mesh(rollerGeometry,frame);
        roller.position.set(Math.cos(angle)*this.radius*.86,Math.sin(angle)*this.radius*.86,0);
        roller.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),new THREE.Vector3(-Math.sin(angle),Math.cos(angle),handedness*.9).normalize());
        wheel.add(roller);
      }
      this.object.add(wheel);this.wheels.set(name,wheel);
    }
    const shadow = new THREE.Mesh(new THREE.CircleGeometry(Math.max(length,width)*.68,48),new THREE.MeshBasicMaterial({color:0x000000,transparent:true,opacity:.22,depthWrite:false}));
    shadow.rotation.x=-Math.PI/2;shadow.position.y=.002;shadow.scale.y=.8;this.object.add(shadow);
  }

  update(mechanism:MechanismState) {
    this.object.name=mechanism.name;
    const { pose, wheel_speeds_mm_s } = mechanism.state;
    if (!pose || ![pose.x_mm,pose.y_mm,pose.heading_rad].every(Number.isFinite)) return;
    this.target.set(pose.x_mm/1000,0,-pose.y_mm/1000);
    this.heading=pose.heading_rad;this.speeds=wheel_speeds_mm_s ?? {};
    if (!this.initialized) { this.object.position.copy(this.target);this.object.rotation.y=this.heading;this.initialized=true; }
  }

  animate(dt:number,smooth:boolean) {
    const blend=smooth?1-Math.exp(-dt*18):1;
    this.object.position.lerp(this.target,blend);
    const delta=this.heading-this.object.rotation.y;
    this.object.rotation.y+=Math.atan2(Math.sin(delta),Math.cos(delta))*blend;
    for (const [name,wheel] of this.wheels) {
      const speed=this.speeds[name];
      if (Number.isFinite(speed)) wheel.rotation.z=(wheel.rotation.z+speed/1000/this.radius*dt)%(Math.PI*2);
    }
  }

  dispose() { disposeObject(this.object); }
}
