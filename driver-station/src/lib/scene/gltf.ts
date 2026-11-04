import { base } from '$app/paths';
import type { LoadingManager } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

export function createGLTFLoader(manager?:LoadingManager) {
  // Decoder assets use their own manager; uploaded models cannot fetch external resources.
  const decoder=new DRACOLoader().setDecoderPath(`${base}/draco/`).setWorkerLimit(2);
  const loader=new GLTFLoader(manager).setDRACOLoader(decoder).setMeshoptDecoder(MeshoptDecoder);
  return {loader,decoder};
}
