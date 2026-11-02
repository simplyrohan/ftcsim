<script lang="ts">
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import { Cable, Cpu, Layers, RefreshCw, Activity } from '@lucide/svelte';
  import * as Tabs from '$lib/components/ui/tabs';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import PerformanceSettings from './PerformanceSettings.svelte';
  import HardwareSettings from './HardwareSettings.svelte';
  import MechanismSettings from './MechanismSettings.svelte';
  import RobotConfigurationFiles from './RobotConfigurationFiles.svelte';
  import HelpTooltip from './HelpTooltip.svelte';
  import type { Station } from '$lib/model/station.svelte';
  let { station, tab='hardware' }: {station:Station;tab?:string} = $props();
  const sections = [
    {id:'hardware',label:'Hardware map',icon:Cpu},
    {id:'mechanisms',label:'Mechanisms',icon:Layers},
    {id:'connection',label:'Connection',icon:Cable},
    {id:'performance',label:'Performance',icon:Activity}
  ];
  const section = $derived(sections.some(item=>item.id===tab)?tab:'hardware');
  let endpoint = $state('');
  $effect(()=>{endpoint=station.endpoint;});
</script>
<div class="page-heading"><div><div class="eyebrow">Workspace</div><h1>Settings</h1></div></div>
<Tabs.Root value={section} onValueChange={value=>{void goto(`${base}/settings/${value}`,{keepFocus:true,noScroll:true});}} class="settings-layout">
  <Tabs.List variant="line" class="settings-nav" aria-label="Settings sections">
    {#each sections as item}<Tabs.Trigger value={item.id}><item.icon size={15}/>{item.label}{#if item.id==='hardware'&&station.hardware.hasDraft&&!station.hardware.synchronized||item.id==='mechanisms'&&station.mechanisms.hasSaved&&!station.mechanisms.synchronized}<span class="unsaved-dot" aria-label="Unapplied changes"></span>{/if}</Tabs.Trigger>{/each}
  </Tabs.List>
  <div class="settings-content">
    {#if section==='hardware'||section==='mechanisms'}<RobotConfigurationFiles {station}/>{/if}
    <Tabs.Content value="hardware"><HardwareSettings {station}/></Tabs.Content>
    <Tabs.Content value="mechanisms"><MechanismSettings {station}/></Tabs.Content>
    <Tabs.Content value="connection">
      <div class="settings-heading"><h2>Connection <HelpTooltip label="About connections" text="Run ./gradlew runSimulator in your robot project to start the SDK. Both SDK and simulator connections retry automatically every 2 seconds while disconnected."/></h2></div>
      <form class="connection-form" onsubmit={event=>{event.preventDefault();station.endpoint=endpoint;station.connect();}}>
        <label class="field"><span>SDK WebSocket address</span><Input type="url" bind:value={endpoint} placeholder="ws://localhost:1115/ds" required/></label>
        <Button variant="outline" type="submit" disabled={station.connecting}><RefreshCw size={14}/>{station.connecting?'Connecting…':'Reconnect'}</Button>
      </form>
      <div class="connection-facts"><div><span>Simulator server</span><strong>{station.simulatorConnected?'Connected':'Reconnecting…'}</strong></div><div><span>SDK</span><strong>{station.connecting?'Connecting…':station.connected?station.controller?'Connected · controller':'Connected · observer':'Disconnected'}</strong></div><div><span>SDK → simulator</span><strong>{!station.simulatorConnected?'Unknown':station.physical?.connected?'Connected':'Waiting for SDK'}</strong></div><div><span class="label-with-help">Storage <HelpTooltip label="About browser storage" text="Hardware maps and mechanisms stay with this browser, per SDK address. Save a robot file to move your configuration and models between workspaces."/></span><strong>This browser · per SDK address</strong></div></div>
      {#if station.notice}<p class="form-notice" role="status">{station.notice}</p>{/if}
    </Tabs.Content>
    <Tabs.Content value="performance"><PerformanceSettings {station}/></Tabs.Content>
  </div>
</Tabs.Root>
