/** Portable hardware-map files deliberately exclude SDK addresses and live state. */
const HARDWARE_MAP_FORMAT = 'ftcsim.hardware-map';

/** FileReader also works in embedded browsers that don't expose Blob.text(). */
export function readHardwareFile(file) {
  if (!(file instanceof Blob)) return file.text(); // Pasted JSON.
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(Error(reader.error?.message || 'The browser could not read this file.'));
    reader.onabort = () => reject(Error('File reading was cancelled.'));
    reader.readAsText(file);
  });
}

export function decodeHardwareMap(text) {
  const record = JSON.parse(text);
  if (!record || typeof record !== 'object' || Array.isArray(record) || record.version !== 1 || !Array.isArray(record.devices)) {
    throw Error('Expected a version 1 hardware-map file with a devices array.');
  }
  if (record.format !== undefined && record.format !== HARDWARE_MAP_FORMAT) throw Error('This file is not an ftcsim hardware map.');
  if (Object.keys(record).some(key => !['format','version','devices','notes'].includes(key))) throw Error('Unknown hardware-map file fields.');
  if (record.notes !== undefined && typeof record.notes !== 'string') throw Error('Hardware-map notes must be text.');
  if (record.devices.length > 256) throw Error('A map may contain at most 256 hub devices.');
  let count = 0;
  const check = (devices, depth=0) => {
    if (depth > 8) throw Error('Hardware-map nesting is too deep.');
    for (const device of devices) {
      if (++count > 1024) throw Error('Too many devices in the hardware map.');
      if (!device || typeof device !== 'object' || Array.isArray(device) || typeof device.name !== 'string' || typeof device.type !== 'string') throw Error('Every device needs a name and driver type.');
      if (Object.keys(device).some(key => !['name','type','module','port','options','children'].includes(key))) throw Error(`Unknown fields on ${device.name}.`);
      if (device.options !== undefined && (!device.options || typeof device.options !== 'object' || Array.isArray(device.options))) throw Error(`Invalid options on ${device.name}.`);
      if (device.type === 'motor' && device.options && 'max_ticks_per_second' in device.options) {
        const options = device.options;
        if ('max_rpm' in options) throw Error(`${device.name}: use max_rpm instead of max_ticks_per_second.`);
        const ticks = options.ticks_per_revolution ?? 537.7;
        if (typeof ticks !== 'number' || !Number.isFinite(ticks) || ticks <= 0 || typeof options.max_ticks_per_second !== 'number' || !Number.isFinite(options.max_ticks_per_second) || options.max_ticks_per_second <= 0) throw Error(`${device.name}: invalid motor speed or encoder resolution.`);
        options.max_rpm = options.max_ticks_per_second / ticks * 60;
        options.ticks_per_revolution = ticks;
        delete options.max_ticks_per_second;
      }
      if (device.children !== undefined) {
        if (!Array.isArray(device.children)) throw Error(`Invalid child list on ${device.name}.`);
        check(device.children, depth + 1);
      }
    }
  };
  check(record.devices);
  return {version:1, devices:record.devices, ...(record.notes ? {notes:record.notes} : {})};
}
