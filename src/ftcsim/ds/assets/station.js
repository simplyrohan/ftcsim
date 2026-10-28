import {connectDrivers} from './drivers.js';
import {HardwareMapEditor} from './hardware.js';

const $ = id => document.getElementById(id), keys = new Set(), virtual = [{},{}];
let ws = null, controller = false, status = 'disconnected', seq = 0, focused = document.hasFocus();
let helloReceived = false, restorePending = true;
const pending = new Map();
const active = () => ['initialized','running'].includes(status);

function updateButtons() {
  const ready = controller && ws?.readyState === WebSocket.OPEN;
  $('init').disabled = !ready || active() || !hardware.ready;
  $('start').disabled = !ready || status !== 'initialized';
  $('stop').disabled = !ready;
  $('opmode').disabled = !ready || active();
}

function send(data, callback) {
  if (ws?.readyState !== WebSocket.OPEN) return false;
  data.id = ++seq;
  if (callback) {
    const timer = setTimeout(() => {
      if (pending.delete(data.id)) callback({type:'error', message:'SDK response timed out. Reconnect before trying again.'});
    }, 7000);
    pending.set(data.id, {callback, timer});
  }
  ws.send(JSON.stringify(data));
  return true;
}

const hardware = new HardwareMapEditor({send, changed:updateButtons});
function maybeRestore() {
  if (!restorePending || !hardware.loaded || !helloReceived || !controller || active() || ['connecting','disconnected'].includes(status)) return;
  restorePending = false;
  hardware.restore();
}

function failPending() {
  const callbacks = [...pending.values()]; pending.clear();
  for (const {callback, timer} of callbacks) { clearTimeout(timer); callback({type:'error', message:'SDK connection closed.'}); }
}

function connect() {
  let endpoint;
  try {
    const url = new URL($('endpoint').value);
    if (!['ws:','wss:'].includes(url.protocol)) throw Error('Use a ws:// SDK address.');
    endpoint = url.href;
  } catch (error) { $('message').textContent = `Invalid SDK address: ${error.message}`; return; }
  if (ws) ws.close();
  failPending(); reset();
  controller = false; status = 'connecting'; helloReceived = false; restorePending = true;
  hardware.load(endpoint);
  hardware.setConnection(false, false);
  try { localStorage.setItem('ftcsim.sdkEndpoint', endpoint); } catch { /* Hardware persistence reports storage errors separately. */ }
  const socket = new WebSocket(endpoint); ws = socket;
  socket.onopen = () => { if (ws !== socket) return; $('connection').textContent = 'SDK connected'; updateButtons(); };
  socket.onclose = () => {
    if (ws !== socket) return;
    failPending(); controller = false; status = 'disconnected';
    $('connection').textContent = 'SDK disconnected'; $('state').textContent = 'Disconnected';
    hardware.setConnection(false, false);
  };
  socket.onerror = () => { if (ws === socket) $('message').textContent = 'Cannot reach SDK. Start it, then Connect.'; };
  socket.onmessage = event => {
    if (ws !== socket) return;
    const m = JSON.parse(event.data);
    if (m.type === 'role') {
      controller = m.controller;
      $('connection').textContent = controller ? 'SDK connected · controller' : 'SDK connected · observer';
      hardware.setConnection(controller, active(), !controller);
    }
    if (m.type === 'hello') {
      helloReceived = true;
      $('opmode').replaceChildren(...m.opmodes.map(o => {
        const option = document.createElement('option'); option.value = o.name; option.textContent = `${o.name} (${o.flavor})`; return option;
      }));
      hardware.setRemote(m.devices, m.hardwareConfigured === true);
    }
    if (m.type === 'status') {
      status = m.state; $('state').textContent = m.state;
      $('elapsed').textContent = `${m.elapsed.toFixed(1)} s · hardware ${m.simulatorConnected ? 'connected' : 'disconnected'}`;
      $('opmode').value = m.selected; $('error').textContent = m.error;
      hardware.setConnection(controller, active(), !controller);
    }
    if (m.type === 'command' && m.name === 'CMD_SET_TELEMETRY_DISPLAY_FORMAT') $('telemetry').style.fontFamily = m.extra === 'MONOSPACE' ? 'monospace' : 'inherit';
    if (m.type === 'command') $('message').textContent = `SDK: ${m.name}`;
    if (m.type === 'telemetry') $('telemetry').textContent = Object.entries(m.data).map(([k,v]) => `${k}: ${v}`).join('\n') || '—';
    if (m.type === 'ack' || m.type === 'error') {
      const response = pending.get(m.id); pending.delete(m.id);
      if (response) { clearTimeout(response.timer); response.callback(m); }
      if (m.type === 'error') $('message').textContent = m.message;
    }
    maybeRestore(); updateButtons();
  };
}

function showPage() {
  const hardwarePage = location.pathname.replace(/\/$/,'') === '/ds/hardware';
  $('hardwarePage').hidden = !hardwarePage; $('stationPage').hidden = hardwarePage;
  $('hardwareLink').setAttribute('aria-current', hardwarePage ? 'page' : 'false');
  $('stationLink').setAttribute('aria-current', hardwarePage ? 'false' : 'page');
  document.title = hardwarePage ? 'Hardware map · FTC Driver Station' : 'FTC Desktop Driver Station';
  reset();
}
for (const link of document.querySelectorAll('nav a, [data-page-link]')) link.onclick = event => {
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  event.preventDefault(); history.pushState(null, '', link.href); showPage();
};
addEventListener('popstate', showPage);
$('connect').onclick = connect;
for (const command of ['init','start','stop']) $(command).onclick = () => {
  if (command === 'init' && !hardware.ready) return;
  send({type:command}, m => { $('message').textContent = m.type === 'ack' ? `${command.toUpperCase()} accepted` : m.message; });
};
$('opmode').onchange = () => send({type:'select', name:$('opmode').value});
const axes=['left_stick_x','left_stick_y','right_stick_x','right_stick_y','left_trigger','right_trigger'];
const buttons=['a','b','x','y','left_bumper','right_bumper','back','start','guide','left_stick_button','right_stick_button','dpad_up','dpad_down','dpad_left','dpad_right'];
for(let i=0;i<2;i++){const card=document.createElement('div');card.className='pad';card.innerHTML=`<h2>Gamepad ${i+1} <small id="pad${i}">virtual</small></h2>`;
for(const name of axes){const label=document.createElement('label');label.textContent=name.replaceAll('_',' ');const input=document.createElement('input');input.type='range';input.min=name.endsWith('trigger')?0:-1;input.max=1;input.step=.01;input.value=0;input.setAttribute('aria-label',`Gamepad ${i+1} ${name}`);input.oninput=()=>virtual[i][name]=Number(input.value);label.append(input);card.append(label);}
const row=document.createElement('div');row.className='row';for(const name of buttons){const button=document.createElement('button');button.textContent=name.replaceAll('_',' ');button.setAttribute('aria-pressed','false');button.onclick=()=>{virtual[i][name]=!virtual[i][name];button.classList.toggle('on',virtual[i][name]);button.setAttribute('aria-pressed',String(virtual[i][name]));};row.append(button);}card.append(row);$('pads').append(card);}
function reset(){keys.clear();for(const v of virtual)for(const k of Object.keys(v))delete v[k];document.querySelectorAll('.pad input').forEach(e=>e.value=0);document.querySelectorAll('.pad button').forEach(e=>{e.classList.remove('on');e.setAttribute('aria-pressed','false');});}
addEventListener('blur',()=>{focused=false;reset();});addEventListener('focus',()=>focused=true);
addEventListener('keydown',e=>{if(['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName))return;keys.add(e.code);if(e.code==='Space'||e.code.startsWith('Arrow'))e.preventDefault();});addEventListener('keyup',e=>keys.delete(e.code));
function gamepad(index,physical){if(!focused||$('stationPage').hidden)return {};if(physical){const data={};axes.forEach((name,i)=>data[name]=i<4?(Math.abs(physical.axes[i]||0)>.06?physical.axes[i]:0):physical.buttons[i===4?6:7]?.value||0);const order=[0,1,2,3,4,5,8,9,16,10,11,12,13,14,15];buttons.forEach((name,i)=>data[name]=!!physical.buttons[order[i]]?.pressed);return data;}
const result={...virtual[index]};if(index===0){const k=code=>keys.has(code)?1:0;result.left_stick_x=(result.left_stick_x||0)+k('KeyD')-k('KeyA');result.left_stick_y=(result.left_stick_y||0)+k('KeyS')-k('KeyW');result.right_stick_x=(result.right_stick_x||0)+k('KeyL')-k('KeyJ');result.right_stick_y=(result.right_stick_y||0)+k('KeyK')-k('KeyI');for(const [name,code]of Object.entries({a:'Space',b:'KeyB',x:'KeyX',y:'KeyY',left_bumper:'KeyQ',right_bumper:'KeyE',dpad_up:'ArrowUp',dpad_down:'ArrowDown',dpad_left:'ArrowLeft',dpad_right:'ArrowRight'}))result[name]=!!result[name]||keys.has(code);result.left_trigger=Math.max(result.left_trigger||0,k('KeyR'));result.right_trigger=Math.max(result.right_trigger||0,k('KeyF'));}axes.forEach(a=>{if(a in result)result[a]=Math.max(a.endsWith('trigger')?0:-1,Math.min(1,result[a]));});return result;}
setInterval(()=>{if(!controller||ws?.readyState!==WebSocket.OPEN)return;const pads=Array.from(navigator.getGamepads?.()||[]).filter(Boolean);for(let i=0;i<2;i++)$(`pad${i}`).textContent=pads[i]?.id||'virtual';send({type:'gamepads',gamepad1:gamepad(0,pads[0]),gamepad2:gamepad(1,pads[1])});},50);

let savedEndpoint;
try { savedEndpoint = localStorage.getItem('ftcsim.sdkEndpoint'); } catch { /* The editor displays storage errors. */ }
const queryPort = new URLSearchParams(location.search).get('sdk');
$('endpoint').value = queryPort ? `ws://${location.hostname}:${queryPort}/ds` : savedEndpoint || `ws://${location.hostname}:1115/ds`;
showPage(); connect(); connectDrivers(state => hardware.setPhysicalState(state));
hardware.initialize().then(maybeRestore);
