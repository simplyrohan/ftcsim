import {DriverWidget, format} from './base.js';
export class ServoWidget extends DriverWidget {
  constructor() {
    super();
    this.meter = document.createElement('meter');
    this.meter.min = 0; this.meter.max = 1;
    this.meter.setAttribute('aria-label', 'Servo position');
    this.element.insertBefore(this.meter, this.children);
  }
  update(device) { super.update(device); this.meter.value = device.state.position; }
  rows(s) { return [['Output', s.enabled ? 'Enabled' : 'Disabled'], ['Position', format(s.position)], ['Pulse (µs)', s.pulse_us], ['Period (µs)', s.period_us]]; }
}
