import {DriverWidget, format} from './base.js';
export class EncoderWidget extends DriverWidget {
  rows(s) { return [['Encoder ticks', s.ticks], ['Position (ticks)', format(s.position)], ['Velocity (ticks/s)', format(s.velocity)]]; }
}
