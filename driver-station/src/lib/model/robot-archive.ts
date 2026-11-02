import { unzip, zip, strFromU8, strToU8, type Unzipped, type UnzipFileInfo } from 'fflate';
import { MAX_MODEL_BYTES, MAX_ROBOT_BYTES } from './model-assets';

const ROBOT_CONFIG_PATH='robot.json';
const MAX_CONFIG_BYTES=1024*1024;
function expand(data:Uint8Array,filter:(file:UnzipFileInfo)=>boolean):Promise<Unzipped> {
  return new Promise((resolve,reject)=>unzip(data,{filter},(error,files)=>error?reject(error):resolve(files)));
}
function validPath(path:string){return !path.startsWith('/') && !/[\\\0]/.test(path) && path.replace(/\/$/,'').split('/').every(part=>part!=='' && part!=='.' && part!=='..');}
export function modelPath(path:unknown):path is string{return typeof path==='string' && validPath(path) && /^models\/[^/]+\.glb$/i.test(path);}

/** Inspect ZIP metadata before allocating or decompressing any model data. */
export async function decodeRobotArchive(data:Uint8Array) {
  if(data.byteLength>MAX_ROBOT_BYTES)throw Error('Robot archives must be at most 64 MB.');
  if(data.byteLength<22 || data[0]!==0x50 || data[1]!==0x4b)throw Error('Expected an .fs robot archive (a ZIP containing robot.json and models).');
  const entries=new Map<string,UnzipFileInfo>();let total=0;
  await expand(data,file=>{
    if(!validPath(file.name) || entries.has(file.name))throw Error('The robot archive contains unsafe or duplicate file paths.');
    entries.set(file.name,file);total+=file.originalSize;
    if(entries.size>130 || total>MAX_ROBOT_BYTES)throw Error('The expanded robot archive exceeds its size or file-count limit.');
    if(file.name===ROBOT_CONFIG_PATH && file.originalSize>MAX_CONFIG_BYTES)throw Error('robot.json must be at most 1 MB.');
    if(modelPath(file.name) && file.originalSize>MAX_MODEL_BYTES)throw Error('GLB models may be at most 20 MB.');
    if(![0,8].includes(file.compression) || file.size>data.byteLength || file.compression===0&&file.size!==file.originalSize)throw Error('Unsupported or damaged ZIP entry.');
    return false;
  });
  if(!entries.has(ROBOT_CONFIG_PATH))throw Error('The robot archive is missing robot.json at its root.');
  const files=await expand(data,file=>file.name===ROBOT_CONFIG_PATH||modelPath(file.name));
  for(const [name,bytes] of Object.entries(files))if(bytes.byteLength!==entries.get(name)?.originalSize)throw Error(`Damaged archive entry: ${name}.`);
  const assets=new Map<string,ArrayBuffer>();
  for(const [path,bytes] of Object.entries(files))if(modelPath(path))assets.set(path,bytes.slice().buffer);
  return {text:strFromU8(files[ROBOT_CONFIG_PATH]),assets};
}

export async function encodeRobotArchive(record:object,models:Map<string,ArrayBuffer>):Promise<Uint8Array<ArrayBuffer>> {
  const json=strToU8(JSON.stringify(record,null,2)+'\n');
  if(json.byteLength>MAX_CONFIG_BYTES)throw Error('robot.json exceeds the 1 MB configuration limit.');
  let total=json.byteLength;
  const files:Record<string,Uint8Array|[Uint8Array,{level:0}]>={[ROBOT_CONFIG_PATH]:json};
  for(const [path,model] of models){
    if(!modelPath(path) || model.byteLength>MAX_MODEL_BYTES)throw Error('Invalid robot model file.');
    total+=model.byteLength;
    if(total>MAX_ROBOT_BYTES)throw Error('The combined robot configuration and models exceed 64 MB.');
    // GLBs commonly contain compressed textures. Store their original bytes intact.
    files[path]=[new Uint8Array(model),{level:0}];
  }
  const archive=await new Promise<Uint8Array<ArrayBuffer>>((resolve,reject)=>zip(files,{level:1},(error,bytes)=>error?reject(error):resolve(bytes)));
  if(archive.byteLength>MAX_ROBOT_BYTES)throw Error('The robot archive exceeds 64 MB. Use smaller models.');
  return archive;
}
