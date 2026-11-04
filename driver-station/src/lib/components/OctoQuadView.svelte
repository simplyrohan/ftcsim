<script lang="ts">
  import type { Options } from '$lib/model/types';
  import { format } from '$lib/utils';
  let {state}:{state:Options}=$props();
  const statuses:Record<number,string>={1:'Waiting for calibration',2:'IMU warming up',3:'Calibrating IMU',4:'Localizer ready',5:'Encoder interface · no IMU'};
</script>
<div class="octoquad-status">{state.has_imu?statuses[state.status]??'Unknown localizer state':'8-channel encoder interface'}</div>
{#if state.has_imu}<div class="octoquad-pose"><div><span>X</span><strong>{format(state.x_mm,1)}<small>mm</small></strong></div><div><span>Y</span><strong>{format(state.y_mm,1)}<small>mm</small></strong></div><div><span>Heading</span><strong>{format(state.heading_rad*180/Math.PI,1)}<small>°</small></strong></div></div>{/if}
<div class="octoquad-channels" aria-label="OctoQuad encoder channels">
  {#each state.channels??[] as channel (channel.port)}<div class:channel-active={!!channel.name&&Math.abs(channel.velocity_ticks_s)>.1} class:channel-empty={!channel.name}>
    <span>CH {channel.port}<small>{channel.mode==='pwm'?'PWM':'QUAD'}</small></span>
    <strong>{channel.name?format(channel.position,0):'—'}<small>{channel.mode==='pwm'?'µs':'ticks'}</small></strong>
    <span class="octoquad-channel-name">{channel.name??'Not connected'}</span>
    {#if channel.name}<span>{format(channel.velocity_ticks_s,0)} {channel.mode==='pwm'?'µs/s':'ticks/s'}</span>{/if}
  </div>{/each}
</div>
