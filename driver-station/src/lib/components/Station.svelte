<script lang="ts">
  import { onMount, untrack } from 'svelte';
  import { page } from '$app/state';
  import { goto } from '$app/navigation';
  import { slidingIndicator } from '$lib/actions/sliding-indicator';
  import { base } from '$app/paths';
  import { fade } from 'svelte/transition';
  import { LayoutDashboard, Cpu, Terminal, Gamepad2, Settings2, ChevronRight, SlidersHorizontal, Menu, ChevronDown } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Switch } from '$lib/components/ui/switch';
  import * as Collapsible from '$lib/components/ui/collapsible';
  import { milliseconds } from '$lib/model/diagnostics.svelte';
  import { Station } from '$lib/model/station.svelte';
  import { flatten } from '$lib/model/configuration';
  import Settings from './Settings.svelte';
  import ConfirmationDialog from './ConfirmationDialog.svelte';
  import DriverCard from './DriverCard.svelte';
  import GamepadCard from './GamepadCard.svelte';
  import GamepadSelector from './GamepadSelector.svelte';
  import ControllerPanel from './ControllerPanel.svelte';
  import Overview from './Overview.svelte';
  import Telemetry from './Telemetry.svelte';
  import HelpTooltip from './HelpTooltip.svelte';
  const station = new Station();
  const navigation = [{id:'overview',label:'Overview',icon:LayoutDashboard},{id:'devices',label:'Devices',icon:Cpu},{id:'telemetry',label:'Telemetry',icon:Terminal},{id:'gamepads',label:'Gamepads',icon:Gamepad2}];
  const path = $derived(page.url.pathname.slice(base.length).replace(/^\/+|\/+$/g,''));
  const isSettings = $derived(path==='settings'||path.startsWith('settings/')||path==='hardware'||path==='mechanisms');
  const settingsTab = $derived(isSettings ? path.split('/')[1]||(['hardware','mechanisms'].includes(path)?path:'hardware') : 'hardware');
  const view = $derived(isSettings?'settings':navigation.some(item=>item.id===path)?path:'overview');
  const current = $derived(view==='settings'?{label:'Settings'}:navigation.find(item=>item.id===view)!);
  let mobileNav = $state(false), deviceFilter = $state(''), motionOpen = $state(false);
  let vx=$state(0),vy=$state(0),yaw=$state(0);
  const devices = $derived(station.physical?.devices ?? []);
  const nestedDeviceCount = $derived(flatten(devices).length-devices.length);
  const filteredDevices = $derived(devices.filter(device=>`${device.name} ${device.type}`.toLowerCase().includes(deviceFilter.toLowerCase())));
  function openSettings(tab='hardware') { void goto(`${base}/settings/${tab}`);mobileNav=false; }
  $effect(()=>{path;mobileNav=false;untrack(()=>station.confirmation.cancel());});
  $effect(()=>{station.gamepads.allowed=!isSettings&&!station.confirmation.pending;station.gamepads.reset();});
  onMount(()=>{void station.mount();return()=>station.destroy();});
</script>
<svelte:head><title>{current.label} · ftcsim</title><meta name="description" content="Your local FTC Driver Station. Run robot code, inspect devices, and model mechanisms."/></svelte:head>
<svelte:window onfocus={()=>station.focus(true)} onblur={()=>station.focus(false)} onkeydown={event=>{if(station.confirmation.pending)return;if((event.metaKey||event.ctrlKey)&&event.key===','){event.preventDefault();openSettings();}else station.gamepads.key(event,true);}} onkeyup={event=>station.gamepads.key(event,false)} onstorage={event=>{station.hardware.storageChanged(event.key);station.mechanisms.storageChanged(event.key);}}/>
<svelte:document onvisibilitychange={()=>{if(!document.hidden)station.heartbeat();else station.gamepads.reset();}}/>
<div class="app-shell">
  <aside class="sidebar" class:mobile-open={mobileNav}>
    <a class="brand" href={`${base}/`} aria-label="ftcsim overview"><span>FTCSIM</span></a>
    <span class="eyebrow nav-caption">Workspace</span>
    <nav class="sliding-nav" use:slidingIndicator aria-label="Driver Station navigation">{#each navigation as item}<a href={item.id==='overview'?`${base}/`:`${base}/${item.id}`} aria-current={view===item.id?'page':undefined} onclick={()=>mobileNav=false}><item.icon size={16} strokeWidth={1.5}/><span>{item.label}</span>{#if item.id==='devices'}<span class="nav-count">{devices.length.toString().padStart(2,'0')}</span>{/if}</a>{/each}</nav>
    <div class="sidebar-bottom"><a class="settings-link" href={`${base}/settings/hardware`} aria-current={isSettings?'page':undefined} onclick={()=>mobileNav=false}><Settings2 size={16} strokeWidth={1.5}/><span>Settings</span><kbd>⌘ ,</kbd></a><div class="sidebar-connections" role="status" aria-label="Connection status">
      <button class="connection-row" title="Connection status and round-trip latency; open Connection settings for details" onclick={()=>openSettings('connection')}><span class="status-dot" class:offline={!station.simulatorConnected}></span><span>Simulator server</span><span class="connection-value">{station.simulatorConnected?station.diagnostics.simulator.ms===null?'Connected':milliseconds(station.diagnostics.simulator.ms):'Offline'}</span></button>
      <button class="connection-row" title="Connection status and round-trip latency; open Connection settings for details" onclick={()=>openSettings('connection')}><span class="status-dot" class:offline={!station.connected} class:connecting={station.connecting}></span><span>SDK</span><span class="connection-value">{station.connecting?'Connecting…':station.connected?station.diagnostics.sdk.ms===null?'Connected':milliseconds(station.diagnostics.sdk.ms):'Offline'}</span></button>
    </div></div>
  </aside>
  {#if mobileNav}<button class="mobile-scrim" aria-label="Close navigation" onclick={()=>mobileNav=false}></button>{/if}
  <div class="workspace" class:viewer-workspace={view==='overview'}>
    <header class="topbar"><div class="breadcrumb"><Button variant="ghost" size="icon" class="mobile-menu" aria-label="Toggle navigation" onclick={()=>mobileNav=!mobileNav}><Menu size={17}/></Button><span>Workspace</span><ChevronRight size={12}/><strong>{current.label}</strong></div></header>
    {#if view==='overview'}
      <Overview {station} onsettings={openSettings}/>
    {:else if view==='settings'}
      <main class="settings-page"><Settings {station} tab={settingsTab}/></main>
    {:else}
    <main>
      <div class="page-heading"><div><div class="eyebrow">Driver station</div><h1>{current.label}</h1></div></div>
      <ControllerPanel {station} onHardware={()=>openSettings('hardware')}/>
      {#key view}<div class="view-content" in:fade={{duration:160}}>
        {#if view==='devices'}
          <div class="section-toolbar"><span>{devices.length} hub devices · {nestedDeviceCount} nested encoders</span><label class="search-field"><span class="sr-only">Filter devices</span><input type="search" class="control" placeholder="Filter devices…" bind:value={deviceFilter}/></label></div><div class="device-grid">{#each filteredDevices as device (`${device.module}/${device.name}/${device.type}`)}<DriverCard {device}/>{:else}<div class="empty-state"><Cpu size={28} strokeWidth={1}/><h3>{devices.length?'No matching devices':'No hardware connected'}</h3><p>{devices.length?'Try a different device name.':'Add and apply your hardware map in Settings to inspect device state.'}</p>{#if !devices.length}<Button variant="outline" onclick={()=>openSettings('hardware')}>Configure hardware</Button>{/if}</div>{/each}</div>
          <Collapsible.Root class="panel motion-panel" bind:open={motionOpen}><Collapsible.Trigger class="motion-toggle"><span><SlidersHorizontal size={15}/>Sensor motion input</span><ChevronDown size={14} class={motionOpen?'rotate-180':''}/></Collapsible.Trigger><Collapsible.Content class="motion-content"><div class="label-with-help"><span class="eyebrow">Robot-relative motion</span><HelpTooltip label="About sensor motion input" text="Manual motion affects sensors that are not connected to a mechanism. Units are robot-relative."/></div><form class="motion-form" onsubmit={event=>{event.preventDefault();station.motion(vx,vy,yaw);}}>{#each ['Forward (mm/s)','Left (mm/s)','Yaw (deg/s)'] as label,index}<label class="field"><span>{label}</span><input class="control" type="number" step="any" required value={index===0?vx:index===1?vy:yaw} oninput={event=>{const n=Number(event.currentTarget.value);if(index===0)vx=n;else if(index===1)vy=n;else yaw=n;}}/></label>{/each}<Button variant="outline" type="submit" disabled={!station.physical?.connected}>Apply motion</Button><Button variant="outline" onclick={()=>{vx=vy=yaw=0;station.motion(0,0,0);}} disabled={!station.physical?.connected}>Stop motion</Button></form></Collapsible.Content></Collapsible.Root>
        {:else if view==='telemetry'}<Telemetry data={station.telemetry}/><section class="activity-panel"><div class="panel-heading"><h3>Session activity</h3><Button variant="ghost" size="sm" onclick={()=>station.events=[]}>Clear</Button></div>{#each station.events.toReversed() as event}<div class="activity-line"><time>{event.time}</time><span class="status-dot" class:offline={event.level==='error'}></span><span class:error-text={event.level==='error'}>{event.message}</span></div>{/each}</section>
        {:else if view==='gamepads'}<div class="gamepads-heading"><div class="gamepad-input-target"><span class="label-with-help">Keyboard &amp; virtual controls <HelpTooltip label="About gamepad selection" text="Keyboard and virtual controls affect the selected gamepad. Switching controllers releases all keyboard and virtual inputs."/></span><GamepadSelector gamepads={station.gamepads}/></div><div class="switch-label"><span>Enable input</span><Switch bind:checked={station.gamepads.enabled} aria-label="Enable gamepad input" onCheckedChange={checked=>{if(!checked)station.gamepads.reset();}}/></div></div><div class="gamepad-workspace"><GamepadCard gamepads={station.gamepads} index={station.gamepads.selected}/></div><div class="keyboard-guide"><span class="eyebrow">Keyboard / Gamepad {station.gamepads.selected+1}</span><div><kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd><span>Left stick</span><kbd>I</kbd><kbd>J</kbd><kbd>K</kbd><kbd>L</kbd><span>Right stick</span><kbd>Z</kbd><span>A</span><kbd>X</kbd><span>B</span><kbd>C</kbd><span>X</span><kbd>V</kbd><span>Y</span><kbd>Q</kbd><span>Left bumper</span><kbd>E</kbd><span>Right bumper</span><kbd>R</kbd><span>Left trigger</span><kbd>T</kbd><span>Right trigger</span></div></div>{/if}
      </div>{/key}
      <footer class="page-footer"><span>ftcsim<span class="muted"> / </span>Desktop simulation</span></footer>
    </main>
    {/if}
  </div>
</div>

<ConfirmationDialog confirmation={station.confirmation}/>
