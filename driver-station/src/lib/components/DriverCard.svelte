<script lang="ts">
  import { Cpu } from '@lucide/svelte';
  import DriverCard from './DriverCard.svelte';
  import { driverWidgets, fallbackWidget } from '$lib/model/widgets';
  import type { DeviceState } from '$lib/model/types';
  import { format } from '$lib/utils';
  let { device }: {device:DeviceState} = $props();
  const presenter = $derived(driverWidgets.get(device.type) ?? fallbackWidget);
</script>
<article class="device-card panel">
  <div class="device-card-top"><div class="device-icon"><Cpu size={17} strokeWidth={1.4}/></div><div><h3>{device.name}</h3><p>{presenter.label}</p></div><span class="port-label">{device.module!==undefined?`H${device.module} / ${device.port}`:`IN ${String(device.port).toUpperCase()}`}</span></div>
  {#if device.type==='motor'}<div class="motor-readout"><span>{format(device.state.shaft_rpm,1)}<small>RPM</small></span><span class="muted">{device.state.enabled?'Output enabled':'Output disabled'}</span></div><div class="power-track"><div class="power-fill" style:width={`${Math.min(100,Math.abs(device.state.power)*100)}%`}></div></div>{/if}
  {#if device.type==='servo'}<div class="motor-readout"><span>{format(device.state.position*100,1)}<small>%</small></span><span class="muted">Servo position</span></div><meter min="0" max="1" value={device.state.position} aria-label={`${device.name} servo position`}></meter>{/if}
  <dl class="data-rows">{#each presenter.rows(device.state) as [label,value]}<div><dt>{label}</dt><dd>{value}</dd></div>{/each}</dl>
  {#if device.children?.length}<div class="nested-devices">{#each device.children as child}<DriverCard device={child}/>{/each}</div>{/if}
</article>
