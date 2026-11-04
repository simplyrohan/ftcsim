import type { Device, DeviceState, DriverType, Mechanism, MechanismType, Option } from './types';
export const copy = <T>(value:T):T => JSON.parse(JSON.stringify(value));
export const canonical = (value:unknown):string => JSON.stringify(value, (_key,item) => item && !Array.isArray(item) && typeof item === 'object' ? Object.fromEntries(Object.keys(item).sort().map(key => [key,item[key]])) : item);
export const flatten = <T extends {children?:T[]}>(devices:T[]):T[] => devices.flatMap(device => [device,...flatten<T>(device.children ?? [])]);
export const defaults = (schema:{options:Option[]}) => Object.fromEntries(schema.options.map(option => [option.name,option.default]));
export const optionValue = (options:Record<string,any>|undefined, option:Option) => options && option.name in options ? options[option.name] : option.default;
export const choiceValue = (choice:any) => typeof choice === 'object' ? choice.value : choice;
export const choiceLabel = (choice:any) => typeof choice === 'object' ? choice.label : String(choice);
export const topology = (devices:(Device|DeviceState)[]):string => canonical(devices.map(({name,type,module,port,children=[]}) => canonical({name,type,module,port:module===undefined?String(port):port,children:topology(children)})).sort());
function optionError(options:Record<string,any> = {}, schema:Option[]):string {
  if (Object.keys(options).some(key => !schema.some(option => option.name === key))) return 'Unknown configuration option.';
  for (const option of schema) {
    const value = option.name in options ? options[option.name] : option.default;
    if (option.type === 'number' && (typeof value !== 'number' || !Number.isFinite(value))) return `${option.label} must be a number.`;
    if (option.min !== undefined && value < option.min) return `${option.label} must be at least ${option.min}.`;
    if (option.max !== undefined && value > option.max) return `${option.label} must be at most ${option.max}.`;
    if (option.choices && !option.choices.some(choice => choiceValue(choice) === value)) return `Invalid ${option.label.toLowerCase()}.`;
  }
  return '';
}
export interface HardwareIssue { message:string; devices:Device[] }
export function hardwareIssues(devices:Device[], catalog:DriverType[]):HardwareIssue[] {
  const issues:HardwareIssue[]=[],names=new Map<string,Device>(),occupied=new Map<string,Device>();
  const report=(message:string,...devices:Device[])=>issues.push({message,devices});
  if(devices.length>256)report('A hardware map can contain at most 256 hub devices.');
  function visit(device:Device,parent?:Device) {
    const schema=catalog.find(type=>type.type===device.type);
    if(!schema){report(`Unknown driver type: ${device.type}.`,device);return;}
    if(typeof device.name!=='string'||!device.name.trim())report('Every driver needs a name.',device);
    else {
      const previous=names.get(device.name);
      if(previous)report(`Duplicate device name: “${device.name}”. Choose a unique name for each driver.`,previous,device);
      else if(/^hub\d+$/.test(device.name))report(`“${device.name}” is reserved for the simulator hub.`,device);
      names.set(device.name,device);
    }
    if(parent) {
      const owner=catalog.find(type=>type.type===parent.type)!;
      if(!owner.child_ports.includes(String(device.port))||schema.connection!==owner.child_connections[device.port]||device.module!==undefined)report(`${device.name}: invalid child connection.`,device,parent);
    } else {
      if(!Number.isInteger(device.module)||device.module!<1||device.module!>254)report(`${device.name}: hub address must be 1–254.`,device);
      if(!Number.isInteger(device.port)||Number(device.port)<0||Number(device.port)>=schema.ports)report(`${device.name}: invalid ${schema.connection} port.`,device);
      for(const space of schema.connection==='motor'?['motor','encoder']:[schema.connection]) {
        const key=`${device.module}:${space}:${device.port}`,previous=occupied.get(key);
        if(previous) {
          // A pair of motors already conflicts on the motor port.
          if(space!=='encoder'||previous.type!=='motor'||device.type!=='motor')report(`Port conflict: “${previous.name}” and “${device.name}” both use Hub ${device.module} ${space} port ${device.port}.`,previous,device);
        } else occupied.set(key,device);
      }
    }
    const error=optionError(device.options,schema.options);
    if(error)report(`${device.name}: ${error}`,device);
    if((schema.connection==='servo'||device.type==='octoquad_encoder')&&(device.options?.max_pulse_us??schema.options.find(option=>option.name==='max_pulse_us')?.default)<=(device.options?.min_pulse_us??schema.options.find(option=>option.name==='min_pulse_us')?.default))report(`${device.name}: maximum pulse must exceed minimum pulse.`,device);
    if(device.type==='octoquad_mk2'&&(device.options?.x_port??0)===(device.options?.y_port??1))report(`${device.name}: localizer X and Y must use different encoder channels.`,device);
    const childPorts=new Map<string,Device>();
    for(const child of device.children??[]) {
      const port=String(child.port),previous=childPorts.get(port);
      if(previous)report(`Port conflict: “${previous.name}” and “${child.name}” both use ${device.name} input ${port}.`,device,previous,child);
      else childPorts.set(port,child);
      visit(child,device);
    }
  }
  for(const device of devices)visit(device);
  return issues;
}
export function hardwareError(devices:Device[],catalog:DriverType[]):string { return hardwareIssues(devices,catalog)[0]?.message??''; }
export function mechanismError(definitions:Mechanism[], catalog:MechanismType[], devices:Device[]):string {
  const drivers = flatten(devices), claimed = new Set<string>(), names = new Set<string>();
  if (definitions.length > 64) return 'At most 64 mechanisms may be configured.';
  for (const definition of definitions) {
    const visualError = mechanismVisualError(definition,definitions); if (visualError) return visualError;
    const schema = catalog.find(type => type.type === definition.type);
    if (!schema) return `Unknown mechanism type: ${definition.type}.`;
    if (!definition.name.trim() || names.has(definition.name)) return 'Mechanisms need unique, nonempty names.';
    names.add(definition.name);
    if (Object.keys(definition.drivers).some(slot => !schema.drivers.some(item => item.name === slot))) return `${definition.name}: unknown driver slot.`;
    for (const slot of schema.drivers) {
      const name = definition.drivers[slot.name]; if (!name && !slot.required) continue;
      const driver = drivers.find(driver => driver.name === name && slot.types.includes(driver.type));
      if (!driver) return `${definition.name}: choose an available ${slot.label.toLowerCase()}.`;
      const consumed = [driver];
      for (const [port,requirement] of Object.entries(slot.children ?? {})) {
        const child = driver.children?.find(child => child.port === port);
        if (!child || child.type !== requirement.type || Object.entries(requirement.options ?? {}).some(([key,value]) => (child.options?.[key] ?? value) !== value)) return `${driver.name} needs its ${port.toUpperCase()} ${requirement.type} driver.`;
        consumed.push(child);
      }
      for (const item of schema.exclusive === false ? [] : consumed) { if (claimed.has(item.name)) return `${item.name} is already connected to a mechanism.`; claimed.add(item.name); }
    }
    const error = optionError(definition.options,schema.options); if (error) return `${definition.name}: ${error}`;
  }
  return '';
}

function mechanismVisualError(definition:Mechanism, definitions:Mechanism[]):string {
  const visual=definition.visual;
  if (visual===undefined) return '';
  if (!visual || typeof visual!=='object' || Array.isArray(visual) || Object.keys(visual).some(key=>!['model','position','rotation','scale','parent'].includes(key))) return `${definition.name}: invalid visual settings.`;
  for (const key of ['position','rotation'] as const) if (visual[key]!==undefined && (!Array.isArray(visual[key]) || visual[key]!.length!==3 || !visual[key]!.every(value=>typeof value==='number' && Number.isFinite(value)))) return `${definition.name}: ${key} needs three finite numbers.`;
  if (visual.scale!==undefined && (typeof visual.scale!=='number' || !Number.isFinite(visual.scale) || visual.scale<=0)) return `${definition.name}: model scale must be positive.`;
  if (visual.model!==undefined && (!visual.model || typeof visual.model!=='object' || typeof visual.model.id!=='string' || !visual.model.id || typeof visual.model.name!=='string' || Object.keys(visual.model).some(key=>!['id','name'].includes(key)))) return `${definition.name}: invalid model reference.`;
  if (visual.parent!==undefined && (typeof visual.parent!=='string' || visual.parent && !definitions.some(item=>item.name===visual.parent))) return `${definition.name}: choose an available mechanism origin.`;
  const seen=new Set([definition.name]); let parent=visual.parent;
  while(parent){ if(seen.has(parent))return `${definition.name}: mechanism origins cannot form a cycle.`; seen.add(parent); parent=definitions.find(item=>item.name===parent)?.visual?.parent; }
  return '';
}
export const mechanismPhysics = (definitions:Mechanism[]) => definitions.map(({visual,...definition})=>definition);
