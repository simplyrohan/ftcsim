<script lang="ts">
  import { onDestroy } from 'svelte';
  import DriverCard from './DriverCard.svelte';
  import { driverWidgets, fallbackWidget } from '$lib/model/widgets';
  import type { DeviceState } from '$lib/model/types';
  import { format } from '$lib/utils';
  let { device }: {device:DeviceState} = $props();
  let verbose = $state(false), moving = $state(false);
  let previousPosition:number|undefined, timer:ReturnType<typeof setTimeout>;
  const active = $derived(device.type==='motor' && !!device.state.enabled && (Math.abs(device.state.power??0)>.005 || Math.abs(device.state.shaft_rpm??0)>.1));
  $effect(()=>{
    if(device.type!=='servo')return;
    const position=Number(device.state.position);
    if(device.state.enabled && previousPosition!==undefined && Math.abs(position-previousPosition)>.00001){moving=true;clearTimeout(timer);timer=setTimeout(()=>moving=false,450);}
    else if(!device.state.enabled){moving=false;clearTimeout(timer);}
    previousPosition=position;
  });
  onDestroy(()=>clearTimeout(timer));
  const presenter = $derived(driverWidgets.get(device.type) ?? fallbackWidget);
</script>
<article class="device-card panel" class:composite-device={!!device.children?.length} class:motor-active={active} class:servo-active={moving}>
  <div class="device-primary">
  <div class="device-card-top"><div><h3>{device.name}</h3><p>{presenter.label}</p></div><span class="port-label">{device.module!==undefined?`H${device.module} / ${device.port}`:`IN ${String(device.port).toUpperCase()}`}</span></div>
  <div class="device-instrument">
    <svg viewBox="0 0 56 56" fill="none" aria-hidden="true"><circle cx="28" cy="28" r="22" opacity=".4"/>
      {#if device.type==='servo'}<path d="M28 28V10" transform={`rotate(${Number(device.state.position??.5)*180-90} 28 28)`}/><circle cx="28" cy="28" r="4"/>
      {:else if device.type==='pinpoint'}<path d="m28 9 6 22-6-4-6 4Z" transform={`rotate(${-Number(device.state.heading_rad??0)*180/Math.PI} 28 28)`}/>
      {:else}<g transform={`rotate(${Number(device.state.position??0)/(Number(device.state.ticks_per_revolution)||360)*360%360} 28 28)`}><path d="M28 8v14m0 12v14M8 28h14m12 0h14"/><circle cx="28" cy="28" r="6"/></g>{/if}
    </svg>
    <div class="device-reading">
      {#if device.type==='motor'}<strong>{format(device.state.shaft_rpm,1)}<small>RPM</small></strong><span>{format(device.state.power*100,0)}% power · {active?'Active':device.state.enabled?'Idle':'Disabled'}</span>
      {:else if device.type==='servo'}<strong>{format(device.state.position*100,1)}<small>%</small></strong><span>{moving?'Moving':device.state.enabled?'Holding position':'PWM disabled'}</span>
      {:else if device.type==='pinpoint'}<strong>{format(device.state.heading_rad*180/Math.PI,1)}<small>°</small></strong><span>X {format(device.state.x_mm,0)} · Y {format(device.state.y_mm,0)} mm</span>
      {:else if device.type==='odometry'}<strong>{format(device.state.ticks,0)}<small>ticks</small></strong><span>{String(device.state.axis??'').toUpperCase()} · {format(device.state.velocity,0)} ticks/s</span>
      {:else}<span>{presenter.rows(device.state).slice(0,2).map(([label,value])=>`${label}: ${value}`).join(' · ')}</span>{/if}
    </div>
  </div>
  <label class="device-verbose"><input type="checkbox" bind:checked={verbose} aria-label={`Verbose details for ${device.name}`}/>Verbose</label>
  {#if verbose}<dl class="data-rows">{#each presenter.rows(device.state) as [label,value]}<div><dt>{label}</dt><dd>{value}</dd></div>{/each}</dl>{/if}
  </div>
  {#if device.children?.length}<div class="nested-devices">{#each device.children as child (`${child.type}:${child.name}:${child.port}`)}<DriverCard device={child}/>{/each}</div>{/if}
</article>
