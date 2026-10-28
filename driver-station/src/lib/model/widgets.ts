import type { Options } from './types';
import { format } from '$lib/utils';
export type Row = [string,string];
export class DriverPresenter {
  label = 'Device';
  rows(state:Options):Row[] { return Object.entries(state).map(([key,value])=>[key.replaceAll('_',' '),typeof value==='number'?format(value):String(value)]); }
}
export class EncoderPresenter extends DriverPresenter {
  rows(state:Options):Row[] { return [['Encoder ticks',format(state.ticks,0)],['Position',`${format(state.position)} ticks`],['Velocity',`${format(state.velocity)} ticks/s`]]; }
}
class MotorPresenter extends EncoderPresenter {
  label = 'DC motor';
  rows(state:Options):Row[] { return [['Output',state.enabled?'Enabled':'Disabled'],['Power',`${format(state.power*100,1)}%`],['Mode',['Power','Velocity','Target position'][state.mode]??String(state.mode)],['Shaft speed',`${format(state.shaft_rpm)} RPM`],['Maximum RPM',format(state.max_rpm,0)],['Ticks / revolution',format(state.ticks_per_revolution,1)],['Direction',state.direction===-1?'Reversed':'Forward'],...super.rows(state)]; }
}
class ServoPresenter extends DriverPresenter {
  label = 'Servo';
  rows(state:Options):Row[] { return [['Output',state.enabled?'PWM enabled':'PWM disabled'],['Position',`${format(state.position*100,1)}%`],['Pulse width',`${format(state.pulse_us,0)} µs`],['PWM period',`${format(state.period_us,0)} µs`]]; }
}
class OdometryPresenter extends EncoderPresenter {
  label = 'Odometry pod';
  rows(state:Options):Row[] { return [['Axis',state.axis.toUpperCase()],['Physical offset',`${format(state.offset_mm)} mm`],['Distance',`${format(state.distance_mm)} mm`],...super.rows(state)]; }
}
class PinpointPresenter extends DriverPresenter {
  label = 'goBILDA Pinpoint';
  rows(state:Options):Row[] { const status:Record<number,string>={1:'Ready',2:'Calibrating',4:'X pod missing',8:'Y pod missing',12:'Both pods missing'};return [['Status',status[state.status]??String(state.status)],['I²C address',`0x${Number(state.address).toString(16)}`],['X / Y',`${format(state.x_mm)} / ${format(state.y_mm)} mm`],['Heading',`${format(state.heading_rad*180/Math.PI)}°`],['Velocity X / Y',`${format(state.vx_mm_s)} / ${format(state.vy_mm_s)} mm/s`],['Yaw rate',`${format(state.yaw_rate_rad_s*180/Math.PI)}°/s`]]; }
}
// Register a presentation for each Python driver kind. Composite cards recurse.
export const driverWidgets = new Map<string,DriverPresenter>([['motor',new MotorPresenter()],['servo',new ServoPresenter()],['odometry',new OdometryPresenter()],['pinpoint',new PinpointPresenter()]]);
export const fallbackWidget = new DriverPresenter();
