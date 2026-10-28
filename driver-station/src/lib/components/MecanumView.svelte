<script lang="ts">
  import { MoveUpRight } from '@lucide/svelte';
  import { format } from '$lib/utils';
  import type { MechanismState } from '$lib/model/types';
  let { mechanism }: {mechanism:MechanismState} = $props();
  const state = $derived(mechanism.state);
  const x = $derived(state.pose.x_mm/5), y = $derived(-state.pose.y_mm/5);
  const heading = $derived(state.pose.heading_rad*180/Math.PI);
  const wheels = [['front_left',-35,-30],['front_right',23,-30],['rear_left',-35,14],['rear_right',23,14]] as const;
  const limit = $derived(Math.max(400,Math.abs(x)+80,(Math.abs(y)+80)/.62));
</script>
<div class="field-view">
  <svg viewBox={`${-limit} ${-limit*.62} ${limit*2} ${limit*1.24}`} role="img" aria-label={`${mechanism.name} drivetrain pose and wheel speeds`}>
    <defs><pattern id={`grid-${mechanism.name.replace(/\W/g,'')}`} width="60" height="60" patternUnits="userSpaceOnUse"><path d="M60 0H0V60" fill="none" stroke="currentColor" stroke-opacity=".09" stroke-width=".7"/></pattern></defs>
    <rect x={-limit} y={-limit*.62} width={limit*2} height={limit*1.24} fill={`url(#grid-${mechanism.name.replace(/\W/g,'')})`}/>
    <path d={`M${-limit} 0H${limit}M0 ${-limit*.62}V${limit*.62}`} stroke="currentColor" stroke-opacity=".16" stroke-width=".7" stroke-dasharray="3 5"/>
    <circle cx="0" cy="0" r="3" fill="currentColor" opacity=".35"/>
    <path d={`M0 0H${x}V${y}`} fill="none" stroke="currentColor" stroke-opacity=".3" stroke-dasharray="3 5"/>
    <g transform={`translate(${x},${y}) rotate(${-heading+90})`}>
      <circle r="65" fill="none" stroke="currentColor" stroke-opacity=".08"/>
      <rect x="-23" y="-38" width="46" height="76" rx="7" fill="var(--background)" stroke="currentColor" stroke-opacity=".7" stroke-width="1"/>
      <path d="M0 13V-17M-6-11 0-17 6-11" fill="none" stroke="currentColor" stroke-width="1.5"/>
      {#each wheels as [name,wx,wy]}<g><rect x={wx} y={wy} width="12" height="18" rx="2" fill="var(--background)" stroke="currentColor" stroke-opacity={Math.abs(state.wheel_speeds_mm_s[name])>.01?1:.35}/><path d={`M${wx+2} ${wy+4}l8 5m-8 1 8 5`} fill="none" stroke="currentColor" stroke-opacity=".3"/></g>{/each}
      <path d="M-15-46h30" stroke="currentColor" stroke-opacity=".2"/>
    </g>
    <text x={-limit+20} y={-limit*.62+25} fill="currentColor" opacity=".35" font-size="9" font-family="monospace" letter-spacing="2">TOP VIEW / IDEAL KINEMATICS</text>
    <text x={limit-20} y={limit*.62-16} fill="currentColor" opacity=".35" text-anchor="end" font-size="9" font-family="monospace">+X FORWARD · +Y LEFT</text>
  </svg>
  <span class="field-label"><span class="status-dot"></span>{mechanism.name}</span>
</div>
<div class="pose-readout"><div><span>X position</span><strong>{format(state.pose.x_mm,1)}<small>mm</small></strong></div><div><span>Y position</span><strong>{format(state.pose.y_mm,1)}<small>mm</small></strong></div><div><span>Heading</span><strong>{format(heading,1)}<small>deg</small></strong></div></div>
<div class="wheel-readouts">{#each Object.entries(state.wheel_speeds_mm_s) as [name,value]}<div><span>{name.replaceAll('_',' ')}</span><strong>{format(value,1)}<small>mm/s</small></strong></div>{/each}</div>
{#if state.encoder_states?.length}
  <div class="tracking-encoders" aria-label="Drivetrain encoder feedback">
    {#each state.encoder_states as encoder (encoder.name)}
      <div><span>{encoder.port.toUpperCase()} · {encoder.name}</span><strong>{format(encoder.ticks,0)}<small>ticks</small></strong><span>{format(encoder.velocity,1)} ticks/s · {format(encoder.distance_mm,1)} mm</span></div>
    {/each}
  </div>
{/if}
<div class="mechanism-caption"><MoveUpRight size={13}/><span>{state.pinpoint?`${state.pinpoint} · ${state.encoders.join(' / ')}`:'No Pinpoint linked · odometry is not driven by this mechanism'}</span><span>{format(state.velocity.vx_mm_s,1)} mm/s forward</span></div>
