<script lang="ts">
  import { Plus, Check, LoaderCircle, Cpu } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import RobotConfigurationFiles from './RobotConfigurationFiles.svelte';
  import DeviceEditor from './DeviceEditor.svelte';
  import type { Station } from '$lib/model/station.svelte';
  let { station }: {station:Station} = $props();
  const hardware = $derived(station.hardware);
  let selectedType = $state('motor'), dragging = $state(false);
</script>
<div class="settings-heading"><div><h2>Hardware map</h2><p>Connect drivers to your Control Hub. Match the names used in your robot code.</p></div><span class="pill">{hardware.count} devices</span></div>
<RobotConfigurationFiles {station}/>
{#if hardware.notes}<details class="file-notes"><summary>File notes</summary><p>{hardware.notes}</p></details>{/if}
<form onsubmit={event=>{event.preventDefault();void hardware.apply();}}>
  <div class="toolbar driver-picker"><label class="sr-only" for="driver-type">Driver type</label><select id="driver-type" class="control" bind:value={selectedType} disabled={!hardware.loaded || hardware.busy}>{#each hardware.catalog as type}<option value={type.type}>{type.label}</option>{/each}</select><Button variant="outline" type="button" size="sm" disabled={!hardware.loaded || hardware.busy} onclick={()=>hardware.add(selectedType)}><Plus size={14}/>Add driver</Button></div>
  <div role="region" aria-label="Robot configuration file drop area" class="configuration-list" class:dragging ondragover={event=>{event.preventDefault();dragging=true;}} ondragleave={()=>dragging=false} ondrop={event=>{event.preventDefault();dragging=false;const files=event.dataTransfer?.files;if(files?.length===1)void station.robotConfiguration.importFile(files[0]);else station.robotConfiguration.message='Drop one robot configuration file at a time.';}}>
    {#each hardware.devices as device}<DeviceEditor {device} {hardware}/>{:else}<div class="empty-state"><Cpu size={27} strokeWidth={1}/><h3>Your hardware starts here</h3><p>Add a driver above, drop a robot configuration here, or load an existing configuration.</p></div>{/each}
  </div>
  <div class="settings-footer">
    <div><p class:error-text={!!hardware.storageError || hardware.loaded && !!hardware.error} role="status">{hardware.storageError || hardware.error || hardware.message || (hardware.synchronized?'Hardware map is applied.':'Draft has unapplied changes.')}</p><small>{station.active?'Stop the OpMode before applying changes.':!station.controller?'Connect as controller to apply.':`${hardware.devices.length} hub devices · ${hardware.count-hardware.devices.length} connected encoders`}</small></div>
    <Button type="submit" variant="outline" disabled={!hardware.canApply}>{#if hardware.busy}<LoaderCircle size={14} class="animate-spin"/>{:else}<Check size={14}/>{/if}Apply to SDK</Button>
  </div>
</form>
