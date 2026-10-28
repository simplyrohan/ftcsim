<script lang="ts">
  import { Plus, Upload, Download, Check, LoaderCircle, FileJson, Cpu } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import DeviceEditor from './DeviceEditor.svelte';
  import type { Station } from '$lib/model/station.svelte';
  let { station }: {station:Station} = $props();
  const hardware = $derived(station.hardware);
  let selectedType = $state('motor'), pasted = $state(''), pasteOpen = $state(false), dragging = $state(false);
  let fileInput:HTMLInputElement;
  async function importPasted(){try{await hardware.importText(pasted,'pasted JSON');pasteOpen=false;}catch(error){hardware.message=`File not loaded: ${error instanceof Error?error.message:error}`;}}
</script>
<div class="settings-heading"><div><h2>Hardware map</h2><p>Connect drivers to your Control Hub. Match the names used in your robot code.</p></div><span class="pill">{hardware.count} devices</span></div>
<div class="toolbar import-toolbar">
  <label class="file-button"><Upload size={14}/><span>Load file</span><input bind:this={fileInput} type="file" accept=".json,application/json" aria-label="Load hardware map file" disabled={hardware.busy || hardware.importing} onclick={()=>fileInput.value=''} onchange={()=>{const file=fileInput.files?.[0];if(file)void hardware.importFile(file);}}/></label>
  <Button variant="outline" size="sm" disabled={!hardware.loaded || !!hardware.error || hardware.busy} onclick={()=>hardware.exportFile()}><Download size={14}/>Save file</Button>
  <Button variant="ghost" size="sm" onclick={()=>pasteOpen=!pasteOpen}><FileJson size={14}/>Paste JSON</Button>
  <span class="toolbar-note">Saved in this browser</span>
</div>
{#if pasteOpen}<div class="paste-panel"><label class="field"><span>Hardware-map JSON</span><textarea class="control code-input" bind:value={pasted} spellcheck="false" placeholder="Paste a hardware-map file…"></textarea></label><Button variant="outline" size="sm" onclick={importPasted} disabled={!pasted.trim() || hardware.busy}>Load JSON</Button></div>{/if}
{#if hardware.notes}<details class="file-notes"><summary>File notes</summary><p>{hardware.notes}</p></details>{/if}
<form onsubmit={event=>{event.preventDefault();void hardware.apply();}}>
  <div class="toolbar driver-picker"><label class="sr-only" for="driver-type">Driver type</label><select id="driver-type" class="control" bind:value={selectedType} disabled={!hardware.loaded || hardware.busy}>{#each hardware.catalog as type}<option value={type.type}>{type.label}</option>{/each}</select><Button variant="outline" type="button" size="sm" disabled={!hardware.loaded || hardware.busy} onclick={()=>hardware.add(selectedType)}><Plus size={14}/>Add driver</Button></div>
  <div role="region" aria-label="Hardware map file drop area" class="configuration-list" class:dragging ondragover={event=>{event.preventDefault();dragging=true;}} ondragleave={()=>dragging=false} ondrop={event=>{event.preventDefault();dragging=false;const files=event.dataTransfer?.files;if(files?.length===1)void hardware.importFile(files[0]);else hardware.message='Drop one hardware-map file at a time.';}}>
    {#each hardware.devices as device}<DeviceEditor {device} {hardware}/>{:else}<div class="empty-state"><Cpu size={27} strokeWidth={1}/><h3>Your hardware starts here</h3><p>Add a driver above, drop a hardware-map file here, or load an existing configuration.</p></div>{/each}
  </div>
  <div class="settings-footer">
    <div><p class:error-text={!!hardware.storageError || hardware.loaded && !!hardware.error} role="status">{hardware.storageError || hardware.error || hardware.message || (hardware.synchronized?'Hardware map is applied.':'Draft has unapplied changes.')}</p><small>{station.active?'Stop the OpMode before applying changes.':!station.controller?'Connect as controller to apply.':`${hardware.devices.length} hub devices · ${hardware.count-hardware.devices.length} connected encoders`}</small></div>
    <Button type="submit" variant="outline" disabled={!hardware.canApply}>{#if hardware.busy}<LoaderCircle size={14} class="animate-spin"/>{:else}<Check size={14}/>{/if}Apply to SDK</Button>
  </div>
</form>
