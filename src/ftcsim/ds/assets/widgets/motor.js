import {EncoderWidget} from './encoder.js';
import {format} from './base.js';
export class MotorWidget extends EncoderWidget {
  rows(s) { return [['Output', s.enabled ? 'Enabled' : 'Disabled'], ['Power', format(s.power)], ['Mode', ['Power', 'Velocity', 'Target position'][s.mode] ?? s.mode], ...super.rows(s)]; }
}
