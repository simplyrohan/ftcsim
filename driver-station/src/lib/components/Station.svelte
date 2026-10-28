<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { base } from '$app/paths';
  import { fade } from 'svelte/transition';
  import { LayoutDashboard, Cpu, Terminal, Gamepad2, Settings2, ChevronRight, Play, Square, RotateCcw, Layers, SlidersHorizontal, ArrowUpRight, Menu, Activity, ScanLine, Clock3, ChevronDown } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Switch } from '$lib/components/ui/switch';
  import { Station } from '$lib/model/station.svelte';
  import { format } from '$lib/utils';
  import { flatten } from '$lib/model/configuration';
  import Settings from './Settings.svelte';
  import DriverCard from './DriverCard.svelte';
  import GamepadCard from './GamepadCard.svelte';
  import GamepadSelector from './GamepadSelector.svelte';
  import MechanismView from './MechanismView.svelte';
  import Telemetry from './Telemetry.svelte';
  const station = new Station();
  const navigation = [{id:'overview',label:'Overview',icon:LayoutDashboard},{id:'devices',label:'Devices',icon:Cpu},{id:'telemetry',label:'Telemetry',icon:Terminal},{id:'gamepads',label:'Gamepads',icon:Gamepad2}];
  const path = $derived(page.url.pathname.slice(base.length).replace(/^\/+|\/+$/g,''));
  const view = $derived(navigation.some(item=>item.id===path)?path:'overview');
  const current = $derived(navigation.find(item=>item.id===view)!);
  let settingsOpen = $state(false), settingsTab = $state('hardware'), mobileNav = $state(false), deviceFilter = $state(''), motionOpen = $state(false);
  let vx=$state(0),vy=$state(0),yaw=$state(0);
  const devices = $derived(station.physical?.devices ?? []);
  const nestedDeviceCount = $derived(flatten(devices).length-devices.length);
  const filteredDevices = $derived(devices.filter(device=>`${device.name} ${device.type}`.toLowerCase().includes(deviceFilter.toLowerCase())));
  const mechanisms = $derived(station.physical?.mechanisms ?? []);
  const outputCount = $derived(devices.filter(device=>device.state.enabled).length);
  function openSettings(tab='hardware') { settingsTab=tab;settingsOpen=true;mobileNav=false; }
  $effect(()=>{if(path==='hardware'||path==='mechanisms'){settingsTab=path;settingsOpen=true;}mobileNav=false;});
  $effect(()=>{station.gamepads.allowed=!settingsOpen;station.gamepads.reset();});
  onMount(()=>{void station.mount();return()=>station.destroy();});
</script>
<svelte:head><title>{current.label} · ftcsim</title><meta name="description" content="Your local FTC Driver Station. Run robot code, inspect devices, and model mechanisms."/></svelte:head>
<svelte:window onfocus={()=>station.focus(true)} onblur={()=>station.focus(false)} onkeydown={event=>{if((event.metaKey||event.ctrlKey)&&event.key===','){event.preventDefault();settingsOpen=!settingsOpen;}else station.gamepads.key(event,true);}} onkeyup={event=>station.gamepads.key(event,false)} onstorage={event=>{station.hardware.storageChanged(event.key);station.mechanisms.storageChanged(event.key);}}/>
<svelte:document onvisibilitychange={()=>{if(!document.hidden)station.heartbeat();else station.gamepads.reset();}}/>
<div class="app-shell">
  <aside class="sidebar" class:mobile-open={mobileNav}>
    <a class="brand" href={`${base}/`} aria-label="ftcsim overview"><svg width="25" height="25" viewBox="0 0 30 30" fill="none" aria-hidden="true"><path d="M5 6h21M5 15h15M5 24h9M5 6v22" stroke="currentColor" stroke-width="2"/></svg><span>ftcsim<span class="brand-dot">.</span></span><span class="brand-tag">DESKTOP</span></a>
    <span class="eyebrow nav-caption">Workspace</span>
    <nav aria-label="Driver Station navigation">{#each navigation as item}<a href={item.id==='overview'?`${base}/`:`${base}/${item.id}`} aria-current={view===item.id?'page':undefined} onclick={()=>mobileNav=false}><item.icon size={16} strokeWidth={1.5}/><span>{item.label}</span>{#if item.id==='devices'}<span class="nav-count">{devices.length.toString().padStart(2,'0')}</span>{/if}</a>{/each}</nav>
    <div class="sidebar-bottom"><button class="settings-link" onclick={()=>openSettings()}><Settings2 size={16} strokeWidth={1.5}/><span>Settings</span><kbd>⌘ ,</kbd></button><div class="sidebar-connections" role="status" aria-label="Connection status">
      <button class="connection-row" onclick={()=>openSettings('connection')}><span class="status-dot" class:offline={!station.simulatorConnected}></span><span>Simulator server</span><span class="connection-value">{station.simulatorConnected?'Connected':'Offline'}</span></button>
      <button class="connection-row" onclick={()=>openSettings('connection')}><span class="status-dot" class:offline={!station.connected} class:connecting={station.connecting}></span><span>SDK</span><span class="connection-value">{station.connecting?'Connecting…':station.connected?'Connected':'Offline'}</span></button>
    </div></div>
  </aside>
  {#if mobileNav}<button class="mobile-scrim" aria-label="Close navigation" onclick={()=>mobileNav=false}></button>{/if}
  <div class="workspace">
    <header class="topbar"><div class="breadcrumb"><Button variant="ghost" size="icon" class="mobile-menu" aria-label="Toggle navigation" onclick={()=>mobileNav=!mobileNav}><Menu size={17}/></Button><span>Workspace</span><ChevronRight size={12}/><strong>{current.label}</strong></div><div class="topbar-right"><button class="topbar-settings" aria-label="Open settings" onclick={()=>openSettings('connection')}><SlidersHorizontal size={15}/></button></div></header>
    <main>
      <div class="page-heading"><div><div class="eyebrow">Driver station</div><h1>{current.label}</h1><p>{view==='overview'?'Your robot, in real time.':view==='devices'?'Inspect every driver and its live physical state.':view==='telemetry'?'A direct line to your running robot code.':'Physical, virtual, and keyboard controls.'}</p></div><Button variant="outline" class="configure-button" onclick={()=>openSettings(view==='devices'?'hardware':'mechanisms')}><Settings2 size={14}/>Configure<ChevronRight size={12}/></Button></div>
      <section class="controller-panel panel" aria-label="Robot Controller">
        <div class="opmode-selector"><label for="opmode">OpMode</label><select id="opmode" class="opmode-select" disabled={!station.connected || !station.controller || station.active || !!station.pendingCommand} value={station.selected} onchange={event=>station.select(event.currentTarget.value)}>{#if !station.opmodes.length}<option value="">Select an OpMode</option>{/if}{#each station.opmodes as mode}<option value={mode.name}>{mode.name} · {mode.flavor}</option>{/each}</select></div>
        <div class="lifecycle-state"><span class="pill"><span class="status-dot" class:offline={!station.active}></span>{station.connected&&!station.connecting?station.status:'idle'}</span><span class="runtime"><Clock3 size={13}/>{format(station.elapsed,1)}<small>s</small></span></div>
        <div class="lifecycle-controls"><Button variant="outline" title={station.initReason} disabled={!station.canInit} onclick={()=>station.command('init')}><RotateCcw size={14}/>{station.pendingCommand==='init'?'Initializing…':'INIT'}</Button><Button variant="outline" disabled={!station.canStart} onclick={()=>station.command('start')}><Play size={14}/>{station.pendingCommand==='start'?'Starting…':'START'}</Button><Button variant="outline" disabled={!station.connected || !station.controller} onclick={()=>station.command('stop')}><Square size={13}/>{station.pendingCommand==='stop'?'Stopping…':'STOP'}</Button></div>
        <div class="controller-caption"><span class:error-text={!!station.error}>{station.error || (station.connected&&!station.connecting?(station.notice || station.initReason):'')}</span><button onclick={()=>openSettings('hardware')}><span class="status-dot" class:offline={!station.hardware.ready}></span>{station.hardware.ready?'Hardware applied':'Configure hardware'}<ChevronRight size={11}/></button></div>
      </section>
      {#key view}<div class="view-content" in:fade={{duration:160}}>
        {#if view==='overview'}
          <div class="metrics-strip"><div><span>Hardware devices</span><strong>{devices.length.toString().padStart(2,'0')}<small>connected</small></strong></div><div><span>Mechanisms</span><strong>{mechanisms.length.toString().padStart(2,'0')}<small>configured</small></strong></div><div><span>Active outputs</span><strong>{outputCount.toString().padStart(2,'0')}<small>of {devices.filter(device=>['motor','servo'].includes(device.type)).length}</small></strong></div><div><span>Lynx commands</span><strong>{format(station.physical?.commands,0)}</strong></div></div>
          <div class="overview-grid"><section class="panel drivetrain-panel"><div class="panel-heading"><div class="title-with-icon"><ScanLine size={15}/><h3>Drivebase</h3></div><button class="text-button" onclick={()=>openSettings('mechanisms')}>Configure<ArrowUpRight size={12}/></button></div>{#if mechanisms.length}<MechanismView mechanism={mechanisms[0]}/>{:else}<div class="field-empty"><div class="empty-grid"></div><Layers size={28} strokeWidth={1}/><h3>A home for your drivebase</h3><p>Connect your motors to a mechanism<br/>to see your robot come to life.</p><Button variant="outline" size="sm" onclick={()=>openSettings('mechanisms')}>Set up a mechanism<ArrowUpRight size={13}/></Button></div>{/if}</section><div class="overview-right"><Telemetry data={station.telemetry} compact/><GamepadCard gamepads={station.gamepads} index={station.gamepads.selected} compact/></div></div>
          {#if mechanisms.length>1}<div class="device-grid more-mechanisms">{#each mechanisms.slice(1) as mechanism}<section class="panel"><div class="panel-heading"><h3>{mechanism.name}</h3></div><MechanismView {mechanism}/></section>{/each}</div>{/if}
          <section class="activity-panel"><div class="panel-heading"><div class="title-with-icon"><Activity size={14}/><h3>Session activity</h3></div><span class="eyebrow">Latest events</span></div>{#each station.events.slice(-3).reverse() as event}<div class="activity-line"><time>{event.time}</time><span class="status-dot" class:offline={event.level==='error'}></span><span class:error-text={event.level==='error'}>{event.message}</span></div>{:else}<p class="fine-print">Connection and OpMode events will appear here.</p>{/each}</section>
        {:else if view==='devices'}
          <div class="section-toolbar"><span>{devices.length} hub devices · {nestedDeviceCount} nested encoders</span><label class="search-field"><span class="sr-only">Filter devices</span><input type="search" class="control" placeholder="Filter devices…" bind:value={deviceFilter}/></label></div><div class="device-grid">{#each filteredDevices as device (`${device.module}/${device.name}/${device.type}`)}<DriverCard {device}/>{:else}<div class="empty-state"><Cpu size={28} strokeWidth={1}/><h3>{devices.length?'No matching devices':'No hardware connected'}</h3><p>{devices.length?'Try a different device name.':'Add and apply your hardware map in Settings to inspect device state.'}</p>{#if !devices.length}<Button variant="outline" onclick={()=>openSettings('hardware')}>Configure hardware</Button>{/if}</div>{/each}</div>
          <section class="panel motion-panel"><button class="motion-toggle" onclick={()=>motionOpen=!motionOpen} aria-expanded={motionOpen}><span><SlidersHorizontal size={15}/>Sensor motion input</span><ChevronDown size={14} class={motionOpen?'rotate-180':''}/></button>{#if motionOpen}<p class="fine-print">Manual motion for sensors that are not connected to a mechanism. Units are robot-relative.</p><form class="motion-form" onsubmit={event=>{event.preventDefault();station.motion(vx,vy,yaw);}}>{#each ['Forward (mm/s)','Left (mm/s)','Yaw (deg/s)'] as label,index}<label class="field"><span>{label}</span><input class="control" type="number" step="any" required value={index===0?vx:index===1?vy:yaw} oninput={event=>{const n=Number(event.currentTarget.value);if(index===0)vx=n;else if(index===1)vy=n;else yaw=n;}}/></label>{/each}<Button variant="outline" type="submit" disabled={!station.physical?.connected}>Apply motion</Button><Button variant="outline" onclick={()=>{vx=vy=yaw=0;station.motion(0,0,0);}} disabled={!station.physical?.connected}>Stop motion</Button></form>{/if}</section>
        {:else if view==='telemetry'}<Telemetry data={station.telemetry}/><section class="activity-panel"><div class="panel-heading"><h3>Session activity</h3><Button variant="ghost" size="sm" onclick={()=>station.events=[]}>Clear</Button></div>{#each station.events.toReversed() as event}<div class="activity-line"><time>{event.time}</time><span class="status-dot" class:offline={event.level==='error'}></span><span class:error-text={event.level==='error'}>{event.message}</span></div>{/each}</section>
        {:else if view==='gamepads'}<div class="gamepads-heading"><div class="gamepad-input-target"><span>Keyboard &amp; virtual controls</span><GamepadSelector gamepads={station.gamepads}/></div><div class="switch-label"><span>Enable input</span><Switch bind:checked={station.gamepads.enabled} aria-label="Enable gamepad input" onCheckedChange={checked=>{if(!checked)station.gamepads.reset();}}/></div></div><p class="fine-print" role="status">Keyboard input controls Gamepad {station.gamepads.selected+1}. Switching controllers releases all keyboard and virtual inputs.</p><div class="gamepad-workspace"><GamepadCard gamepads={station.gamepads} index={station.gamepads.selected}/></div><div class="keyboard-guide"><span class="eyebrow">Keyboard / Gamepad {station.gamepads.selected+1}</span><div><kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd><span>Left stick</span><kbd>I</kbd><kbd>J</kbd><kbd>K</kbd><kbd>L</kbd><span>Right stick</span><kbd>Z</kbd><span>A</span><kbd>X</kbd><span>B</span><kbd>C</kbd><span>X</span><kbd>V</kbd><span>Y</span><kbd>Q</kbd><span>Left bumper</span><kbd>E</kbd><span>Right bumper</span><kbd>R</kbd><span>Left trigger</span><kbd>T</kbd><span>Right trigger</span></div></div>{/if}
      </div>{/key}
      <footer class="page-footer"><span>ftcsim<span class="muted"> / </span>Desktop simulation</span></footer>
    </main>
  </div>
</div>
<Settings {station} bind:open={settingsOpen} bind:tab={settingsTab}/>
