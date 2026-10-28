/** UI counterparts of physical Python drivers. DOM nodes survive state updates. */
export const format = value => Number.isFinite(value) ? value.toFixed(2) : '—';

export class DriverWidget {
  constructor() {
    this.element = document.createElement('article');
    this.element.className = 'driver-widget';
    this.title = document.createElement('h3');
    this.location = document.createElement('small');
    this.values = document.createElement('dl');
    this.children = document.createElement('div');
    this.children.className = 'driver-children';
    this.element.append(this.title, this.location, this.values, this.children);
    this.fields = new Map();
  }
  update(device) {
    this.title.textContent = `${device.name} · ${device.type}`;
    this.location.textContent = device.module !== undefined
      ? `Hub ${device.module} · ${device.connection} ${device.port}`
      : `Input ${device.port}`;
    for (const [label, value] of this.rows(device.state)) {
      if (!this.fields.has(label)) {
        const term = document.createElement('dt'), detail = document.createElement('dd');
        term.textContent = label;
        this.values.append(term, detail);
        this.fields.set(label, detail);
      }
      this.fields.get(label).textContent = String(value);
    }
  }
  rows(state) { return Object.entries(state); }
}
