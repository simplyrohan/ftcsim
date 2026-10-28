import {decodeHardwareMap, encodeHardwareMap, readHardwareFile, MAX_HARDWARE_MAP_BYTES} from './hardware-file.js';

/** Browser-owned hardware map. Python supplies field metadata, never persistence. */
const copy = value => JSON.parse(JSON.stringify(value));
const canonical = value => JSON.stringify(value, function (key, item) {
  if (item && !Array.isArray(item) && typeof item === 'object') {
    return Object.fromEntries(Object.keys(item).sort().map(name => [name, item[name]]));
  }
  return item;
});
const deviceCount = devices => devices.reduce((count, device) => count + 1 + deviceCount(device.children ?? []), 0);
const describe = devices => `${devices.length} hub devices · ${deviceCount(devices) - devices.length} connected encoders`;
// Physical snapshots contain live state rather than driver options. Compare the
// complete wiring tree, including encoders attached to a Pinpoint.
const topology = devices => devices.map(({name, type, module, port, children=[]}) =>
  canonical({name, type, module, port, children:topology(children)})).sort();
const node = (tag, text, className) => {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
};

export class HardwareMapEditor {
  constructor({send, changed}) {
    this.send = send;
    this.changed = changed;
    this.devices = [];
    this.remote = [];
    this.remoteConfigured = false;
    this.catalog = new Map();
    this.loaded = false;
    this.connected = false;
    this.active = false;
    this.busy = false;
    this.hasSaved = false;
    this.hasDraft = false;
    this.physical = null;
    this.application = null;
    this.observer = false;
    this.storageError = '';
    this.message = '';
    this.fileNotes = '';
    this.fileError = '';
    this.importing = false;
    this.fileOperation = 0;
    this.container = document.getElementById('hardwareDevices');
    this.form = document.getElementById('hardwareForm');
    this.typeSelect = document.getElementById('driverType');
    this.applyButton = document.getElementById('applyHardware');
    document.getElementById('addDriver').onclick = () => {
      const device = this.newDevice(this.typeSelect.value);
      if (!device) return;
      const schema = this.catalog.get(device.type);
      for (const port of schema.child_ports) {
        const childType = [...this.catalog.values()].find(type => type.connection === schema.child_connections[port]);
        if (childType) {
          device.children ??= [];
          device.children.push(this.newDevice(childType.type, device, port));
        }
      }
      this.devices.push(device);
      this.persist(); this.render();
    };
    this.fileInput = document.getElementById('hardwareFile');
    this.fileHelp = document.getElementById('hardwareFileHelp');
    // Keep the actual input visible and use its native activation. Synthetic
    // clicks on a hidden file input can be ignored by embedded browsers.
    this.fileInput.onclick = () => {
      this.fileInput.value = '';
      this.fileHelp.textContent = 'Choose a JSON file in the dialog. If no dialog opens, drop the file below or use Paste JSON instead.';
    };
    this.fileInput.onchange = () => {
      const file = this.fileInput.files[0];
      if (file) this.importFile(file);
    };
    this.fileInput.addEventListener('cancel', () => {
      this.fileHelp.textContent = 'File selection cancelled. The current map has not changed.';
    });
    const dropzone = document.getElementById('hardwareDropzone');
    dropzone.ondragover = event => {
      event.preventDefault(); event.dataTransfer.dropEffect = 'copy'; dropzone.classList.add('dragover');
    };
    dropzone.ondragleave = () => dropzone.classList.remove('dragover');
    dropzone.ondrop = event => {
      event.preventDefault(); dropzone.classList.remove('dragover');
      if (event.dataTransfer.files.length !== 1) {
        this.fileError = 'Drop one hardware-map JSON file at a time.'; this.notify(); return;
      }
      this.importFile(event.dataTransfer.files[0]);
    };
    document.getElementById('loadHardwareJson').onclick = () => {
      const text = document.getElementById('hardwareJson').value;
      if (!text.trim()) { this.fileError = 'Paste the hardware-map JSON before loading.'; this.notify(); return; }
      this.importFile({name:'pasted JSON', size:new TextEncoder().encode(text).length, text:async () => text});
    };
    document.getElementById('saveHardware').onclick = () => this.exportFile();
    this.form.onsubmit = event => { event.preventDefault(); this.apply(); };
    addEventListener('storage', event => {
      if (event.key === this.key || event.key === null) {
        this.load(this.endpoint);
        this.message = 'Hardware map changed in another tab. Apply it when stopped.';
        this.notify();
      }
    });
  }

  async initialize() {
    try {
      const response = await fetch('/sim/driver-types', {cache:'no-store'});
      if (!response.ok) throw Error('Cannot load driver types');
      const catalog = await response.json();
      this.catalog = new Map(catalog.map(type => [type.type, type]));
      if (catalog.some(type => !Array.isArray(type.options) || !Array.isArray(type.child_ports))) {
        throw Error('Driver metadata is out of date. Restart the simulator backend');
      }
      this.typeSelect.replaceChildren(...catalog.map(type => {
        const option = node('option', type.label); option.value = type.type; return option;
      }));
      this.loaded = true;
      this.render();
    } catch (error) {
      this.loaded = false;
      this.catalog = new Map();
      this.message = `${error.message}. Reload the page to retry.`;
    }
    this.notify();
  }

  load(endpoint) {
    this.endpoint = endpoint;
    this.key = `ftcsim.hardware.v1:${encodeURIComponent(endpoint)}`;
    this.devices = [];
    this.hasSaved = false;
    this.hasDraft = false;
    this.remote = [];
    this.remoteConfigured = false;
    this.busy = false;
    this.cancelApplication();
    this.message = '';
    this.storageError = '';
    this.fileNotes = ''; this.fileError = ''; this.importing = false; this.fileOperation++;
    try {
      const saved = localStorage.getItem(this.key);
      if (saved !== null) {
        const record = decodeHardwareMap(saved);
        this.devices = record.devices;
        this.fileNotes = record.notes ?? '';
        this.hasSaved = true;
        this.hasDraft = true;
      }
    } catch (error) {
      this.storageError = `Cannot read the saved hardware map: ${error.message}`;
    }
    document.getElementById('hardwareFiles').open = !this.hasDraft;
    document.getElementById('hardwareScope').textContent = `Browser storage · ${endpoint}`;
    this.render(); this.notify();
  }

  persist() {
    this.hasDraft = true;
    try {
      localStorage.setItem(this.key, JSON.stringify({version:1, devices:this.devices, ...(this.fileNotes ? {notes:this.fileNotes} : {})}));
      this.hasSaved = true;
      this.storageError = '';
      this.message = ''; this.fileError = '';
    } catch (error) {
      this.hasSaved = false;
      this.storageError = `Browser storage is unavailable: ${error.message}. This map still works in this tab; save it to a file before closing.`;
    }
    this.notify();
  }

  async importFile(file) {
    if (this.importing) return;
    const key = this.key, operation = ++this.fileOperation;
    this.importing = true; this.fileError = ''; this.fileHelp.textContent = `Loading ${file.name}…`; this.notify();
    try {
      if (file.size > MAX_HARDWARE_MAP_BYTES) throw Error('Hardware-map files must be at most 1 MiB.');
      const record = decodeHardwareMap(await readHardwareFile(file));
      if (!this.loaded) await this.initialize();
      if (this.key !== key || operation !== this.fileOperation) return;
      const error = this.loaded ? this.validationError(record.devices) : '';
      if (error) throw Error(error);
      // A browser storage failure must never discard a successfully read file.
      this.devices = record.devices; this.fileNotes = record.notes ?? '';
      this.persist();
      this.message = `Loaded ${file.name}: ${describe(this.devices)}. Apply to the SDK while stopped.`;
      this.fileHelp.textContent = `Loaded ${file.name}: ${describe(this.devices)}.`;
      document.getElementById('hardwareFiles').open = false;
      this.render();
    } catch (error) {
      if (this.key === key && operation === this.fileOperation) {
        this.fileError = `File not loaded: ${error.message}`;
        this.fileHelp.textContent = this.fileError;
      }
    } finally {
      if (operation === this.fileOperation) { this.importing = false; this.notify(); }
    }
  }

  exportFile() {
    if (!this.loaded || this.busy || this.importing) return;
    const error = this.validationError();
    if (error || !this.form.reportValidity()) { this.fileError = error || 'Complete the device fields before saving.'; this.notify(); return; }
    const url = URL.createObjectURL(new Blob([encodeHardwareMap(this.devices, this.fileNotes)], {type:'application/json'}));
    const link = document.createElement('a');
    link.href = url; link.download = 'ftcsim-hardware-map.json';
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
    this.fileError = ''; this.message = 'Hardware map downloaded as ftcsim-hardware-map.json.';
    this.notify();
  }

  setConnection(ready, active, observer=false) {
    this.connected = ready;
    this.active = active;
    this.observer = observer;
    this.notify();
  }

  setRemote(devices, configured) {
    this.remote = copy(devices);
    this.remoteConfigured = configured;
    this.notify();
  }

  setPhysicalState(state) {
    this.physical = state;
    this.finishApplication();
    this.notify();
  }

  get sdkSynchronized() { return this.hasDraft && this.remoteConfigured && canonical(this.devices) === canonical(this.remote); }
  physicalMatches(devices) { return this.physical?.connected === true && canonical(topology(devices)) === canonical(topology(this.physical.devices)); }
  get synchronized() { return this.sdkSynchronized && this.physicalMatches(this.devices); }

  get ready() { return this.loaded && this.synchronized && !this.busy && !this.importing && !this.validationError(); }

  validationError(devices=this.devices) {
    if (!this.loaded) return 'Loading driver types…';
    if (devices.length > 256) return 'A hardware map can contain at most 256 hub devices.';
    const names = new Set(), occupied = new Set();
    const visit = (device, parent) => {
      const schema = this.catalog.get(device?.type);
      if (!schema) return 'The map contains an unknown driver type.';
      if (typeof device.name !== 'string' || !device.name.trim()) return 'Every device needs a name.';
      if (/^hub\d+$/.test(device.name) || names.has(device.name)) return `Duplicate or reserved name: ${device.name}`;
      names.add(device.name);
      if (parent) {
        const parentSchema = this.catalog.get(parent.type);
        if (!parentSchema.child_ports.includes(device.port) || schema.connection !== parentSchema.child_connections[device.port] || 'module' in device) return `Invalid child connection for ${device.name}`;
      } else {
        if (!Number.isInteger(device.module) || device.module < 1 || device.module > 254) return `${device.name}: hub address must be 1–254.`;
        if (!Number.isInteger(device.port) || device.port < 0 || device.port >= schema.ports) return `${device.name}: invalid port.`;
        const slots = [schema.connection];
        if (schema.connection === 'motor') slots.push('encoder');
        for (const connection of slots) {
          const slot = `${device.module}:${connection}:${device.port}`;
          if (occupied.has(slot)) return `${device.name}: hub ${device.module} ${connection} port ${device.port} is occupied.`;
          occupied.add(slot);
        }
      }
      if (Object.keys(device.options ?? {}).some(name => !schema.options.some(option => option.name === name))) return `${device.name}: unknown driver option.`;
      for (const option of schema.options) {
        const value = device.options && option.name in device.options ? device.options[option.name] : option.default;
        if (option.type === 'number' && (typeof value !== 'number' || !Number.isFinite(value))) return `${device.name}: ${option.label} must be a number.`;
        if (option.min !== undefined && value < option.min) return `${device.name}: ${option.label} must be at least ${option.min}.`;
        if (option.choices && !option.choices.includes(value)) return `${device.name}: invalid ${option.label}.`;
      }
      if (device.type === 'servo' && (device.options?.max_pulse_us ?? 2500) <= (device.options?.min_pulse_us ?? 500)) return `${device.name}: maximum pulse must exceed minimum pulse.`;
      if (device.children !== undefined && !Array.isArray(device.children)) return `${device.name}: invalid child list.`;
      const childPorts = new Set();
      for (const child of device.children ?? []) {
        if (childPorts.has(child.port)) return `${device.name}: duplicate child input ${child.port}.`;
        childPorts.add(child.port);
        const error = visit(child, device);
        if (error) return error;
      }
      return '';
    };
    for (const device of devices) {
      const error = visit(device);
      if (error) return error;
    }
    return '';
  }

  notify() {
    const error = this.loaded ? this.validationError() : this.message || 'Loading driver types…';
    document.getElementById('hardwareNotice').textContent = this.storageError || this.fileError || error || this.message || (this.synchronized ? 'Saved in this browser and applied to the SDK.' : this.hasSaved ? 'Saved in this browser. Apply this map to the SDK while stopped.' : 'Add your hardware, then apply the map before INIT.');
    document.getElementById('hardwareNotice').classList.toggle('error', Boolean(this.storageError || this.fileError || error && this.loaded));
    document.getElementById('hardwareSummary').textContent = this.busy ? 'Applying hardware map…' : this.synchronized ? `Hardware map applied · ${describe(this.devices)}` : this.sdkSynchronized ? 'SDK configured; simulator devices do not match yet' : this.hasDraft ? `Hardware map has unapplied changes · ${describe(this.devices)}` : 'Configure a hardware map before INIT';
    document.getElementById('hardwareDeviceCount').textContent = describe(this.devices);
    document.getElementById('addDriver').disabled = !this.loaded || this.busy || this.importing;
    this.fileInput.disabled = this.importing;
    document.getElementById('loadHardwareJson').disabled = this.importing;
    document.getElementById('saveHardware').disabled = !this.loaded || this.busy || this.importing || Boolean(error);
    document.getElementById('hardwareFileNotes').textContent = this.fileNotes;
    document.getElementById('hardwareNotes').hidden = !this.fileNotes;
    this.typeSelect.disabled = !this.loaded || this.busy || this.importing;
    for (const input of this.container.querySelectorAll('input, select, button')) input.disabled = this.busy || this.importing;
    this.applyButton.disabled = !this.loaded || !this.connected || this.active || this.busy || this.importing || Boolean(error);
    document.getElementById('hardwareConnection').textContent = this.active ? 'STOP the OpMode before applying changes.' : this.connected ? 'Connected as controller · ready to apply' : this.observer ? 'Another DS tab controls the SDK. Close that tab, then click Connect here to apply.' : 'Connect as the SDK controller to apply this map.';
    this.changed();
  }

  restore() {
    if (this.loaded && this.connected && !this.active && this.hasSaved && !this.synchronized && !this.validationError()) this.apply();
  }

  apply() {
    if (this.busy || this.importing || !this.connected || this.active) return false;
    const error = this.validationError();
    if (!this.form.reportValidity() || error) { this.message = error; this.notify(); return false; }
    this.persist();
    const devices = copy(this.devices), key = this.key;
    const application = {devices, acknowledged:false};
    this.application = application;
    this.busy = true; this.message = ''; this.notify();
    const sent = this.send({type:'configure', devices}, reply => {
      if (this.key !== key || this.application !== application) return;
      if (reply.type === 'ack') {
        // A generic ACK is not proof of configuration. Require the SDK's hello
        // echo and matching physical drivers from the simulator before success.
        if (!this.remoteConfigured || canonical(this.remote) !== canonical(devices)) {
          this.cancelApplication(); this.busy = false;
          this.message = 'SDK acknowledged the request without confirming this map. Restart the SDK and reconnect.';
        } else {
          this.application.acknowledged = true;
          this.application.timer = setTimeout(() => {
            this.cancelApplication(); this.busy = false;
            this.message = 'SDK received the map, but the simulator did not create the matching drivers. Check that the SDK uses this simulator, then apply again.';
            this.notify();
          }, 3000);
          this.finishApplication();
        }
      } else {
        this.cancelApplication(); this.busy = false;
        this.message = `SDK rejected the map: ${reply.message}`;
      }
      this.notify();
    });
    if (!sent) { this.cancelApplication(); this.busy = false; this.message = 'SDK disconnected before the map could be applied.'; this.notify(); }
    return sent;
  }

  cancelApplication() {
    if (this.application) clearTimeout(this.application.timer);
    this.application = null;
  }

  finishApplication() {
    if (!this.application?.acknowledged || !this.physicalMatches(this.application.devices)) return;
    const applied = this.application.devices;
    this.cancelApplication(); this.busy = false;
    this.message = canonical(this.devices) === canonical(applied)
      ? `Hardware map applied: ${describe(applied)}. Return to Driver Station and press INIT.`
      : 'Previous map applied. Your current draft has unapplied changes.';
  }

  newDevice(type, parent, port) {
    const schema = this.catalog.get(type);
    if (!schema) return null;
    const names = new Set();
    const collect = devices => devices.forEach(device => { names.add(device.name); collect(device.children ?? []); });
    collect(this.devices);
    const stem = parent ? `${parent.name}_${port}` : type;
    let name = stem, suffix = 2;
    while (names.has(name)) name = `${stem}${suffix++}`;
    const options = Object.fromEntries(schema.options.map(option => [option.name, option.default]));
    if (parent) Object.assign(options, this.catalog.get(parent.type).child_defaults[port] ?? {});
    if (parent) return {name, type, port, options};
    const occupied = candidate => this.devices.some(device => device.module === 1 && device.port === candidate &&
      (this.catalog.get(device.type)?.connection === schema.connection || ['motor','encoder'].includes(schema.connection) && ['motor','encoder'].includes(this.catalog.get(device.type)?.connection)));
    return {name, type, module:1, port:Array.from({length:schema.ports}, (_, i) => i).find(candidate => !occupied(candidate)) ?? 0, options};
  }

  field(title, value, {type='text', choices, min, max, change}) {
    const label = node('label', title);
    const input = document.createElement(choices ? 'select' : 'input');
    if (choices) {
      for (const choice of choices) {
        const option = node('option', String(choice)); option.value = String(choice); input.append(option);
      }
    } else {
      input.type = type; input.required = true;
      if (type === 'number') input.step = 'any';
      if (min !== undefined) input.min = min;
      if (max !== undefined) input.max = max;
    }
    input.value = value ?? '';
    input.disabled = this.busy;
    input.addEventListener(choices ? 'change' : 'input', () => {
      const next = type === 'number' ? (input.value === '' ? null : Number(input.value)) : input.value;
      change(next); this.persist();
    });
    label.append(input);
    return label;
  }

  render() {
    this.container.replaceChildren();
    if (!this.devices.length) this.container.append(node('p', 'No devices added. Choose a driver above to start building your hardware map.', 'empty-state'));
    const renderDevice = (device, siblings, parent) => {
      const schema = this.catalog.get(device.type);
      const card = node('article', undefined, 'hardware-device');
      const header = node('div', undefined, 'row device-heading');
      const heading = node('h3', `${device.name || 'Unnamed'} · ${schema?.label ?? device.type}`);
      const remove = node('button', 'Remove', 'remove-device'); remove.type = 'button';
      remove.setAttribute('aria-label', `Remove ${device.name || device.type}`);
      remove.onclick = () => { siblings.splice(siblings.indexOf(device), 1); this.persist(); this.render(); };
      header.append(heading, remove); card.append(header);
      if (!schema) { card.append(node('p', 'Unknown driver type; remove this device and add a supported driver.')); return card; }
      const fields = node('div', undefined, 'hardware-fields');
      fields.append(this.field('Name', device.name, {change:value => { device.name = value; remove.setAttribute('aria-label', `Remove ${value || device.type}`); }}));
      if (parent) fields.append(node('p', `Connected to ${parent.name} · input ${device.port}`));
      else {
        fields.append(this.field('Hub address', device.module, {type:'number', min:1, max:254, change:value => device.module = value}));
        fields.append(this.field(`${schema.connection === 'i2c' ? 'I²C' : schema.connection} port`, device.port, {type:'number', choices:Array.from({length:schema.ports}, (_,i) => i), change:value => device.port = value}));
      }
      card.append(fields);
      const settings = node('fieldset'); settings.append(node('legend', 'Device settings'));
      const optionFields = node('div', undefined, 'hardware-fields');
      for (const option of schema.options) optionFields.append(this.field(option.label, device.options && option.name in device.options ? device.options[option.name] : option.default, {...option, change:value => { device.options ??= {}; device.options[option.name] = value; }}));
      settings.append(optionFields); card.append(settings);
      if (schema.child_ports.length) {
        const children = node('div', undefined, 'hardware-children');
        children.append(node('h4', 'Connected encoders'));
        device.children ??= [];
        for (const child of device.children) children.append(renderDevice(child, device.children, device));
        for (const port of schema.child_ports.filter(port => !device.children.some(child => child.port === port))) {
          const childType = [...this.catalog.values()].find(type => type.connection === schema.child_connections[port]);
          if (!childType) continue;
          const add = node('button', `Add ${port.toUpperCase()} ${childType.label.toLowerCase()}`); add.type = 'button';
          add.onclick = () => { device.children.push(this.newDevice(childType.type, device, port)); this.persist(); this.render(); };
          children.append(add);
        }
        card.append(children);
      }
      return card;
    };
    for (const device of this.devices) this.container.append(renderDevice(device, this.devices));
  }
}
