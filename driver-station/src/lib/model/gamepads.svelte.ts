export const axes = ['left_stick_x','left_stick_y','right_stick_x','right_stick_y','left_trigger','right_trigger'];
export const buttons = ['a','b','x','y','left_bumper','right_bumper','back','start','guide','left_stick_button','right_stick_button','dpad_up','dpad_down','dpad_left','dpad_right'];
const keyboard:Record<string,string> = {a:'KeyZ',b:'KeyX',x:'KeyC',y:'KeyV',left_bumper:'KeyQ',right_bumper:'KeyE',dpad_up:'ArrowUp',dpad_down:'ArrowDown',dpad_left:'ArrowLeft',dpad_right:'ArrowRight'};
export class Gamepads {
  selected = $state<0|1>(0);
  virtual = $state<Record<string,number|boolean>[]>([{},{}]);
  physical = $state(['Virtual controller','Virtual controller']);
  latest = $state<Record<string,number|boolean>[]>([{},{}]);
  enabled = $state(true);
  allowed = $state(true);
  focused = true;
  private keys = new Set<string>();
  reset() { this.keys.clear(); this.virtual = [{},{}]; this.latest = [{},{}]; }
  selectController(index:0|1) {
    if (index === this.selected) return;
    this.reset();
    this.selected = index;
  }
  key(event:KeyboardEvent, down:boolean) {
    if (!down) { this.keys.delete(event.code); return; }
    const target = event.target as HTMLElement;
    if (event.defaultPrevented || target?.closest?.('input,textarea,select,[contenteditable],[role="combobox"],[role="listbox"],[role="menu"],[role="toolbar"],[data-slot="tooltip-trigger"]')) { this.keys.delete(event.code); return; }
    if (this.enabled) { this.keys.add(event.code); if (event.code.startsWith('Arrow')) event.preventDefault(); }
    else this.keys.delete(event.code);
  }
  sample() {
    let pads:Gamepad[] = [];
    try { pads = Array.from(navigator.getGamepads?.() || []).filter((pad):pad is Gamepad => pad !== null); } catch { /* Virtual controls remain available. */ }
    this.physical = [0,1].map(index => pads[index]?.id || 'Virtual controller');
    const frames = [0,1].map(index => {
      if (!this.focused || !this.enabled || !this.allowed || document.hidden) return {};
      const pad = pads[index];
      const frame:Record<string,number|boolean> = {...this.virtual[index]};
      if (pad) {
        axes.forEach((name,i)=>frame[name] = i < 4 ? Math.abs(pad.axes[i] || 0) > .06 ? pad.axes[i] : 0 : pad.buttons[i === 4 ? 6 : 7]?.value || 0);
        const order=[0,1,2,3,4,5,8,9,16,10,11,12,13,14,15]; buttons.forEach((name,i)=>frame[name]=Boolean(pad.buttons[order[i]]?.pressed));
      } else if (index === this.selected) {
        const k=(key:string)=>this.keys.has(key)?1:0;
        frame.left_stick_x = Number(frame.left_stick_x || 0)+k('KeyD')-k('KeyA');
        frame.left_stick_y = Number(frame.left_stick_y || 0)+k('KeyS')-k('KeyW');
        frame.right_stick_x = Number(frame.right_stick_x || 0)+k('KeyL')-k('KeyJ');
        frame.right_stick_y = Number(frame.right_stick_y || 0)+k('KeyK')-k('KeyI');
        for (const [name,key] of Object.entries(keyboard)) frame[name] = Boolean(frame[name]) || this.keys.has(key);
        frame.left_trigger = Math.max(Number(frame.left_trigger || 0),k('KeyR')); frame.right_trigger = Math.max(Number(frame.right_trigger || 0),k('KeyT'));
      }
      axes.forEach(axis=>{if(axis in frame)frame[axis]=Math.max(axis.endsWith('trigger')?0:-1,Math.min(1,Number(frame[axis])))});
      return frame;
    });
    this.latest = frames; return frames;
  }
}
