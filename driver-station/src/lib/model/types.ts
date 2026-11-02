export type Options = Record<string, any>;
type Port = number | string;
export interface Device { name: string; type: string; module?: number; port: Port; options?: Options; children?: Device[] }
interface Choice { value: string | number; label: string }
export interface Option { name: string; type: string; label: string; default: any; min?: number; max?: number; choices?: (string | number | Choice)[] }
export interface DriverType { type: string; label: string; connection: string; ports: number; child_ports: string[]; child_connections: Record<string,string>; child_defaults: Record<string,Options>; options: Option[]; presets?: { id: string; label: string; options: Options; source?: string }[] }
interface DriverSlot { name: string; label: string; types: string[]; required: boolean; children?: Record<string,{type:string; options:Options}> }
interface MechanismVisualConfig { model?: {id:string;name:string}; position?:number[]; rotation?:number[]; scale?:number; parent?:string }
export interface MechanismType { exclusive?:boolean; type: string; label: string; description: string; drivers: DriverSlot[]; options: Option[] }
export interface Mechanism { visual?:MechanismVisualConfig; name: string; type: string; drivers: Record<string,string>; options?: Options }
export interface DeviceState { name: string; type: string; module?: number; port: Port; connection: string; state: Options; children: DeviceState[] }
export interface MechanismState { name: string; type: string; drivers: Record<string,string>; state: Options }
export interface PhysicalState { connected: boolean; commands: number; devices: DeviceState[]; mechanisms: MechanismState[]; mechanism_configuration: Mechanism[]; mechanism_error: string; motion: {vx:number; vy:number; angular_velocity:number} }
export interface OpMode { name: string; flavor: string }
export interface LogEntry { id: number; time: string; message: string; level: 'info' | 'error' }
