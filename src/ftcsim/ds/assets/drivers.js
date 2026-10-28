import {DriverPanel} from './widgets/index.js';

export function connectDrivers(onState) {
  const panel = new DriverPanel(document.getElementById('drivers'));
  const status = document.getElementById('physicalStatus');
  const message = document.getElementById('motionStatus');
  const form = document.getElementById('motion');
  let socket;
  const connect = () => {
    socket = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/sim/drivers`);
    socket.onmessage = event => {
      const data = JSON.parse(event.data);
      if (data.type === 'state') {
        status.textContent = `SDK ${data.connected ? 'connected' : 'disconnected'} · ${data.commands} Lynx commands · ${data.devices.length} hub devices`;
        panel.update(data.devices);
        onState(data);
        for (const button of form.querySelectorAll('button')) button.disabled = !data.connected;
        document.getElementById('motionCurrent').textContent = `Applied: ${data.motion.vx} mm/s forward, ${data.motion.vy} mm/s left, ${(data.motion.angular_velocity * 180 / Math.PI).toFixed(1)}°/s yaw`;
      }
      if (data.type === 'ack' || data.type === 'error') message.textContent = data.message;
    };
    socket.onclose = () => {
      onState(null);
      status.textContent = 'Simulator disconnected · reconnecting…';
      for (const button of form.querySelectorAll('button')) button.disabled = true;
      setTimeout(connect, 1000);
    };
    socket.onerror = () => socket.close();
  };
  form.addEventListener('submit', event => {
    event.preventDefault();
    if (socket.readyState !== WebSocket.OPEN) return;
    const values = new FormData(form);
    socket.send(JSON.stringify({type:'motion', vx:Number(values.get('vx')), vy:Number(values.get('vy')), angular_velocity:Number(values.get('yaw')) * Math.PI / 180}));
  });
  document.getElementById('stopMotion').onclick = () => {
    if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({type:'motion', vx:0, vy:0, angular_velocity:0}));
    form.reset();
  };
  connect();
}
