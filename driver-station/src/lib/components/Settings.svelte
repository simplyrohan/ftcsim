<script lang="ts">
  import { Cable, Cpu, Layers, RefreshCw } from '@lucide/svelte';
  import * as Dialog from '$lib/components/ui/dialog';
  import * as Tabs from '$lib/components/ui/tabs';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import HardwareSettings from './HardwareSettings.svelte';
  import MechanismSettings from './MechanismSettings.svelte';
  import type { Station } from '$lib/model/station.svelte';
  let { station, open=$bindable(false), tab=$bindable('hardware') }: {station:Station;open:boolean;tab:string} = $props();
  let endpoint = $state('');
  $effect(()=>{if(open)endpoint=station.endpoint;});
</script>
<Dialog.Root bind:open>
  <Dialog.Content class="settings-dialog">
    <div class="settings-dialog-header"><Dialog.Title>Settings</Dialog.Title><Dialog.Description>Configure your simulator workspace.</Dialog.Description></div>
    <Tabs.Root bind:value={tab} orientation="vertical" class="settings-layout">
      <Tabs.List class="settings-nav" aria-label="Settings sections">
        <span class="eyebrow">Workspace</span>
        <Tabs.Trigger value="connection"><Cable size={15}/>Connection</Tabs.Trigger>
        <Tabs.Trigger value="hardware"><Cpu size={15}/>Hardware map{#if station.hardware.hasDraft&&!station.hardware.synchronized}<span class="unsaved-dot"></span>{/if}</Tabs.Trigger>
        <Tabs.Trigger value="mechanisms"><Layers size={15}/>Mechanisms{#if station.mechanisms.hasSaved&&!station.mechanisms.synchronized}<span class="unsaved-dot"></span>{/if}</Tabs.Trigger>
      </Tabs.List>
      <div class="settings-content">
        <Tabs.Content value="connection"><div class="settings-heading"><div><h2>Connection</h2><p>Connect the Driver Station to your desktop Robot Controller.</p></div><Cable size={19}/></div>
          <form class="connection-form" onsubmit={event=>{event.preventDefault();station.endpoint=endpoint;station.connect();}}>
            <label class="field"><span>SDK WebSocket address</span><Input type="url" bind:value={endpoint} placeholder="ws://localhost:1115/ds" required/></label>
            <p class="fine-print">Start <code>./gradlew runSimulator</code> in your robot project, then connect here.</p>
            <Button variant="outline" type="submit" disabled={station.connecting}><RefreshCw size={14}/>{station.connecting?'Connecting…':'Reconnect'}</Button>
          </form>
          <div class="connection-facts"><div><span>Simulator server</span><strong>{station.simulatorConnected?'Connected':'Reconnecting…'}</strong></div><div><span>SDK</span><strong>{station.connecting?'Connecting…':station.connected?station.controller?'Connected · controller':'Connected · observer':'Disconnected'}</strong></div><div><span>SDK → simulator</span><strong>{!station.simulatorConnected?'Unknown':station.physical?.connected?'Connected':'Waiting for SDK'}</strong></div><div><span>Storage</span><strong>This browser · per SDK address</strong></div></div>
          <p class="fine-print">Hardware maps and mechanisms stay with this browser. Save your hardware map to a file to move it between workspaces.</p>
          {#if station.notice}<p class="form-notice" role="status">{station.notice}</p>{/if}
        </Tabs.Content>
        <Tabs.Content value="hardware"><HardwareSettings {station}/></Tabs.Content>
        <Tabs.Content value="mechanisms"><MechanismSettings {station}/></Tabs.Content>
      </div>
    </Tabs.Root>
  </Dialog.Content>
</Dialog.Root>
