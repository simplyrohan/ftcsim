<script lang="ts">
  import { ChevronDown } from '@lucide/svelte';
  import { format } from '$lib/utils';
  import type { MechanismState } from '$lib/model/types';
  import * as Collapsible from '$lib/components/ui/collapsible';
  let { mechanism }: {mechanism:MechanismState} = $props();
  const state=$derived(mechanism.state);
</script>

<div class="pose-readout"><div><span>X position</span><strong>{format(state.pose.x_mm,1)}<small>mm</small></strong></div><div><span>Y position</span><strong>{format(state.pose.y_mm,1)}<small>mm</small></strong></div><div><span>Heading</span><strong>{format(state.pose.heading_rad*180/Math.PI,1)}<small>deg</small></strong></div></div>
<Collapsible.Root class="scene-feedback">
  <Collapsible.Trigger class="scene-feedback-trigger">Wheel &amp; encoder feedback<ChevronDown size={13}/></Collapsible.Trigger>
  <Collapsible.Content>
  <div class="wheel-readouts">{#each Object.entries(state.wheel_speeds_mm_s) as [name,value]}<div><span>{name.replaceAll('_',' ')}</span><strong>{format(value,1)}<small>mm/s</small></strong></div>{/each}</div>
  {#if state.encoder_states?.length}<div class="tracking-encoders" aria-label="Drivetrain encoder feedback">{#each state.encoder_states as encoder (encoder.name)}<div><span>{encoder.port.toUpperCase()} · {encoder.name}</span><strong>{format(encoder.ticks,0)}<small>ticks</small></strong><span>{format(encoder.velocity,1)} ticks/s · {format(encoder.distance_mm,1)} mm</span></div>{/each}</div>{/if}
  <div class="mechanism-caption"><span>{state.pinpoint?`${state.pinpoint} · ${state.encoders.join(' / ')}`:'No Pinpoint linked · odometry is not driven by this mechanism'}</span></div>
  </Collapsible.Content>
</Collapsible.Root>
