import { base } from '$app/paths';
import * as THREE from 'three';
import { createGLTFLoader } from './gltf';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { disposeObject } from './drivetrain';

/** Bundled field is in metres, X/Y on the mat and Z up. */
export async function loadField() {
  const {loader,decoder}=createGLTFLoader();
  let source:THREE.Group|undefined;
  const field=new THREE.Group();field.name='FTC field';
  try {
    source=(await loader.loadAsync(`${base}/models/field.glb`)).scene;
    source.rotation.x=-Math.PI/2;source.updateMatrixWorld(true);
    const mat=new THREE.Box3();
    source.traverse(node=>{if(node.name.includes('Soft_Tiles')||node.name.includes('Soft Tiles'))mat.union(new THREE.Box3().setFromObject(node));});
    if(mat.isEmpty())throw Error('The field model has no mat surface.');
    field.position.y=-mat.max.y;
    // Batch static geometry by material to reduce draw calls.
    const batches=new Map<THREE.Material,THREE.BufferGeometry[]>();
    source.traverse(node=>{
      if(!(node instanceof THREE.Mesh)||Array.isArray(node.material))return;
      const geometry=node.geometry.clone().applyMatrix4(node.matrixWorld);
      const batch=batches.get(node.material)??[];batch.push(geometry);batches.set(node.material,batch);
    });
    for(const [material,geometries] of batches){
      const merged=mergeGeometries(geometries);
      if(!merged)throw Error('Unable to prepare field geometry.');
      geometries.forEach(geometry=>geometry.dispose());
      if(material.transparent)material.depthWrite=false;
      const mesh=new THREE.Mesh(merged,material);mesh.updateMatrix();mesh.matrixAutoUpdate=false;field.add(mesh);
    }
    const originals=new Set<THREE.BufferGeometry>();
    source.traverse(node=>{if(node instanceof THREE.Mesh)originals.add(node.geometry);});
    originals.forEach(geometry=>geometry.dispose());
    return field;
  } catch(error){disposeObject(field);if(source)disposeObject(source);throw error;}
  finally {decoder.dispose();}
}
