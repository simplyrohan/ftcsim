import {DriverWidget, format} from './base.js';
export class PinpointWidget extends DriverWidget {
  rows(s) {
    const status = {1:'Ready', 2:'Calibrating', 4:'X pod missing', 8:'Y pod missing', 12:'Both pods missing'};
    return [['I²C address', `0x${s.address.toString(16)}`], ['Status', status[s.status] ?? s.status],
      ['X / Y (mm)', `${format(s.x_mm)} / ${format(s.y_mm)}`],
      ['Heading (degrees)', format(s.heading_rad * 180 / Math.PI)],
      ['Velocity X / Y (mm/s)', `${format(s.vx_mm_s)} / ${format(s.vy_mm_s)}`],
      ['Yaw rate (degrees/s)', format(s.yaw_rate_rad_s * 180 / Math.PI)]];
  }
}
