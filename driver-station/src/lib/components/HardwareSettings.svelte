<script lang="ts">
  import { Plus, Check, LoaderCircle, Cpu, Search } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import DeviceEditor from './DeviceEditor.svelte';
  import type { Station } from '$lib/model/station.svelte';
  import type { Device } from '$lib/model/types';
  let { station }: {station:Station} = $props();
  const hardware = $derived(station.hardware);
  let selectedType = $state('motor'), dragging = $state(false), filter = $state(''), editing = $state<Device>();
  const filtered = $derived(hardware.devices.filter(device=>`${device.name} ${device.type} ${(device.children??[]).map(child=>child.name).join(' ')}`.toLowerCase().includes(filter.toLowerCase())));
  function add() { const device=hardware.add(selectedType);if(device){filter='';editing=hardware.devices.find(item=>item.name===device.name);} }
</script>
<div class="settings-heading"><div><h2>Hardware map <span class="section-count">{hardware.count}</span></h2><p>Drivers plugged into your Control Hub. Names must match your robot code.</p></div></div>
{#if hardware.notes}<details class="file-notes"><summary>File notes</summary><p>{hardware.notes}</p></details>{/if}
<div class="configuration-toolbar">
  <label class="configuration-search"><Search size={14}/><Input type="search" aria-label="Filter hardware" placeholder="Find a driver…" bind:value={filter}/></label>
  <div class="configuration-add"><label class="sr-only" for="driver-type">Driver type</label><select id="driver-type" class="control" bind:value={selectedType} disabled={!hardware.loaded||hardware.busy}>{#each hardware.catalog as type}<option value={type.type}>{type.label}</option>{/each}</select><Button variant="outline" disabled={!hardware.loaded||hardware.busy||station.robotConfiguration.importing} onclick={add}><Plus size={14}/>Add driver</Button></div>
</div>
<div role="region" aria-label="Robot configuration file drop area" class="configuration-list" class:dragging ondragover={event=>{event.preventDefault();dragging=true;}} ondragleave={()=>dragging=false} ondrop={event=>{event.preventDefault();dragging=false;const files=event.dataTransfer?.files;if(files?.length===1)void station.robotConfiguration.importFile(files[0]);else station.robotConfiguration.message='Drop one robot configuration file at a time.';}}>
  {#each filtered as device (device)}<DeviceEditor {device} {hardware} bind:expanded={()=>editing===device,open=>editing=open?device:undefined}/>{:else}<div class="empty-state"><Cpu size={27} strokeWidth={1}/><h3>{hardware.devices.length?'No matching drivers':'Your hardware starts here'}</h3><p>{hardware.devices.length?'Try a different name or driver type.':'Add a driver above, or load a robot configuration.'}</p></div>{/each}
</div>
<div class="settings-footer">
  <div><p class:error-text={!!hardware.storageError||hardware.loaded&&!!hardware.error} role="status">{hardware.storageError||hardware.error||hardware.message||(hardware.synchronized?'Hardware map is applied.':'Draft has unapplied changes.')}</p><small>{station.active?'Stop the OpMode before applying changes.':!station.controller?'Connect as controller to apply.':`${hardware.devices.length} hub devices · ${hardware.count-hardware.devices.length} connected encoders · edits save automatically`}</small></div>
  <Button variant="outline" disabled={!hardware.canApply} onclick={()=>hardware.apply()}>{#if hardware.busy}<LoaderCircle size={14} class="animate-spin"/>{:else}<Check size={14}/>{/if}Apply to SDK</Button>
</div>
