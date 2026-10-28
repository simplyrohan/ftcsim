import {EncoderWidget} from './encoder.js';
import {format} from './base.js';
export class OdometryWidget extends EncoderWidget {
  rows(s) { return [['Axis', s.axis], ['Wheel offset (mm)', format(s.offset_mm)], ['Distance (mm)', format(s.distance_mm)], ...super.rows(s)]; }
}
