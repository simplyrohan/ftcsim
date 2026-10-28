import {DriverWidget} from './base.js';
import {MotorWidget} from './motor.js';
import {ServoWidget} from './servo.js';
import {OdometryWidget} from './odometry.js';
import {PinpointWidget} from './pinpoint.js';

// Register each built-in widget here, with the Python driver's kind as its key.
const widgets = new Map([
  ['motor', MotorWidget], ['servo', ServoWidget],
  ['odometry', OdometryWidget], ['pinpoint', PinpointWidget],
]);

export class DriverPanel {
  constructor(container) { this.container = container; this.instances = new Map(); }
  update(devices) {
    const live = new Set();
    const visit = (device, parent, path) => {
      const key = `${path}/${device.name}:${device.type}`;
      live.add(key);
      if (!this.instances.has(key)) {
        const Widget = widgets.get(device.type) ?? DriverWidget;
        this.instances.set(key, new Widget());
      }
      const widget = this.instances.get(key);
      if (widget.element.parentNode !== parent) parent.append(widget.element);
      widget.update(device);
      for (const child of device.children) visit(child, widget.children, key);
    };
    for (const device of devices) visit(device, this.container, `hub${device.module}`);
    for (const [key, widget] of this.instances) {
      if (!live.has(key)) { widget.element.remove(); this.instances.delete(key); }
    }
  }
}
