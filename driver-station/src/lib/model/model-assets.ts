export const MAX_MODEL_BYTES = 20 * 1024 * 1024;
export const MAX_ROBOT_BYTES = 64 * 1024 * 1024;
const cache = new Map<string,ArrayBuffer>();
let database:Promise<IDBDatabase>|undefined;
function db() {
  return database ??= new Promise<IDBDatabase>((resolve,reject)=>{
    const request=indexedDB.open('ftcsim-models',1);
    request.onupgradeneeded=()=>request.result.createObjectStore('models');
    request.onsuccess=()=>resolve(request.result);
    request.onerror=()=>{database=undefined;reject(Error('Model storage is unavailable. Enable browser storage to save GLB files.'));};
  });
}
export function readBinaryFile(file:Blob):Promise<ArrayBuffer> {
  return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result as ArrayBuffer);reader.onerror=()=>reject(Error('Unable to read this file.'));reader.onabort=()=>reject(Error('File reading cancelled.'));reader.readAsArrayBuffer(file);});
}
export function validateGLB(data:ArrayBuffer) {
  if(data.byteLength>MAX_MODEL_BYTES)throw Error('GLB models may be at most 20 MB.');
  if(data.byteLength<20)throw Error('This is not a binary glTF 2.0 (.glb) file.');
  const view=new DataView(data);
  if(view.getUint32(0,true)!==0x46546c67 || view.getUint32(4,true)!==2 || view.getUint32(8,true)!==data.byteLength || view.getUint32(16,true)!==0x4e4f534a)throw Error('Invalid GLB header. Export a binary glTF 2.0 file.');
  const length=view.getUint32(12,true);
  if(length>data.byteLength-20)throw Error('The GLB file is truncated.');
  const document=JSON.parse(new TextDecoder().decode(new Uint8Array(data,20,length)));
  if(document.asset?.version!=='2.0')throw Error('Only glTF 2.0 models are supported.');
  for(const entry of [...(document.buffers??[]),...(document.images??[])])if(entry.uri && !/^data:/.test(entry.uri))throw Error('Embed all textures and buffers in the GLB before uploading.');
  if((document.extensionsRequired??[]).some((name:string)=>['KHR_draco_mesh_compression','KHR_texture_basisu'].includes(name)))throw Error('Export without Draco or KTX2 compression. Meshopt-compressed GLBs are supported.');
}
export async function saveModel(id:string,data:ArrayBuffer) {
  validateGLB(data);
  const database=await db();
  await new Promise<void>((resolve,reject)=>{const transaction=database.transaction('models','readwrite');transaction.objectStore('models').put(data,id);transaction.oncomplete=()=>resolve();transaction.onerror=()=>reject(Error('Cannot save this model. Browser storage may be full.'));transaction.onabort=()=>reject(Error('Model storage was cancelled.'));});
  cache.set(id,data);
}
export async function loadModel(id:string):Promise<ArrayBuffer> {
  const existing=cache.get(id);if(existing)return existing;
  const database=await db();
  const value=await new Promise<ArrayBuffer|undefined>((resolve,reject)=>{const request=database.transaction('models').objectStore('models').get(id);request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(Error('Cannot read the saved GLB.'));});
  if(!value)throw Error('Model file is missing in this browser. Upload it again or load the complete robot configuration.');
  cache.set(id,value);return value;
}
export function modelFromBase64(value:unknown):ArrayBuffer {
  if(typeof value!=='string' || value.length>Math.ceil(MAX_MODEL_BYTES/3)*4)throw Error('Invalid embedded model.');
  const binary=atob(value),bytes=new Uint8Array(binary.length);for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);
  validateGLB(bytes.buffer);return bytes.buffer;
}
