<script lang="ts">
  import { Plus, Check, LoaderCircle, Layers } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import RobotConfigurationFiles from './RobotConfigurationFiles.svelte';
  import MechanismEditor from './MechanismEditor.svelte';
  import type { Station } from '$lib/model/station.svelte';
  let { station, active=true }: {station:Station;active?:boolean}=$props();
  const mechanisms=$derived(station.mechanisms);
  let selectedType=$state('mecanum'), selected=$state(0);
  const definition=$derived(mechanisms.definitions[selected]??mechanisms.definitions[0]);
  function add(){mechanisms.add(selectedType);const added=mechanisms.definitions.at(-1);if(added)selected=mechanisms.definitions.length-1;}
</script>
<div class="settings-heading"><div><h2>Mechanisms</h2><p>Build the robot’s motion, connect its parts, and give each one a model.</p></div><span class="pill">{mechanisms.definitions.length} configured</span></div>
<RobotConfigurationFiles {station}/>
<form onsubmit={event=>{event.preventDefault();void mechanisms.apply();}}>
  <div class="toolbar driver-picker"><label class="sr-only" for="mechanism-type">Mechanism type</label><select id="mechanism-type" class="control" bind:value={selectedType}>{#each mechanisms.catalog as type}<option value={type.type}>{type.label}</option>{/each}</select><Button variant="outline" type="button" size="sm" disabled={!mechanisms.loaded||mechanisms.busy||mechanisms.definitions.length>=64} onclick={add}><Plus size={14}/>Add mechanism</Button></div>
  {#if mechanisms.definitions.length}<div class="mechanism-selector" role="group" aria-label="Select mechanism">{#each mechanisms.definitions as item,index}<Button variant="ghost" type="button" size="sm" aria-pressed={definition===item} onclick={()=>selected=index}><Layers size={13}/>{item.name}</Button>{/each}</div>{/if}
  {#if definition}{#key definition}<MechanismEditor {definition} {station} {active}/>{/key}{:else}<div class="empty-state"><Layers size={27} strokeWidth={1}/><h3>Build your robot</h3><p>Add a drivetrain, or a custom mechanism for a turret, arm, or slide.</p></div>{/if}
  <p class="mechanism-help">Models, placement, and origin links save immediately in this browser. Update simulation only after changing driver bindings or motion settings; model files are never uploaded to Python.</p>
  <div class="settings-footer"><div><p role="status" class:error-text={!!mechanisms.storageError||mechanisms.loaded&&!!mechanisms.error||!!station.physical?.mechanism_error}>{mechanisms.storageError||mechanisms.error||station.physical?.mechanism_error||mechanisms.message||(mechanisms.synchronized?'Simulation is up to date.':'Draft has unapplied changes.')}</p><small>{station.active?'Stop the OpMode before applying motion changes.':!station.hardware.ready?'Apply the hardware map first.':'Updates driver bindings and motion parameters in Python. Resets drivetrain pose, preserving hardware encoder state.'}</small></div><Button variant="outline" type="submit" disabled={!mechanisms.canApply}>{#if mechanisms.busy}<LoaderCircle size={14} class="animate-spin"/>{:else}<Check size={14}/>{/if}{mechanisms.busy?'Updating simulation…':'Update simulation'}</Button></div>
</form>
