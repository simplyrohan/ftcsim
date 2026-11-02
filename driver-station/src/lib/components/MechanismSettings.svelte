<script lang="ts">
  import { Plus, Check, LoaderCircle, Layers, Pencil, Trash2, Box, Search } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import * as Collapsible from '$lib/components/ui/collapsible';
  import MechanismEditor from './MechanismEditor.svelte';
  import SelectField from './SelectField.svelte';
  import HelpTooltip from './HelpTooltip.svelte';
  import type { Station } from '$lib/model/station.svelte';
  import type { Mechanism } from '$lib/model/types';
  let { station }: {station:Station}=$props();
  const mechanisms=$derived(station.mechanisms);
  let selectedType=$state('mecanum'), editing=$state<Mechanism>(), filter=$state('');
  const filtered=$derived(mechanisms.definitions.filter(item=>`${item.name} ${item.type}`.toLowerCase().includes(filter.toLowerCase())));
  function add(){const count=mechanisms.definitions.length;mechanisms.add(selectedType);if(mechanisms.definitions.length>count){filter='';editing=mechanisms.definitions.at(-1);}}
</script>
<div class="settings-heading"><h2>Mechanisms <span class="section-count">{mechanisms.definitions.length}</span><HelpTooltip label="About mechanisms" text="Connect drivers to motion models and arrange your robot’s 3D parts. Models and placement save automatically. Update simulation after changing bindings or motion: this resets drivetrain pose and preserves encoder state."/></h2></div>
<div class="configuration-toolbar">
  <label class="configuration-search"><Search size={14}/><Input type="search" aria-label="Filter mechanisms" placeholder="Find a mechanism…" bind:value={filter}/></label>
  <div class="configuration-add"><SelectField id="mechanism-type" aria-label="Mechanism type" items={mechanisms.catalog.map(type=>({value:type.type,label:type.label}))} bind:value={selectedType} disabled={!mechanisms.loaded||mechanisms.busy}/><Button variant="outline" disabled={!mechanisms.loaded||mechanisms.busy||mechanisms.definitions.length>=64||station.robotConfiguration.importing} onclick={add}><Plus size={14}/>Add mechanism</Button></div>
</div>
<div class="configuration-list">
  {#each filtered as definition (definition)}
    {@const schema=mechanisms.catalog.find(item=>item.type===definition.type)}
    <Collapsible.Root open={editing===definition} onOpenChange={open=>editing=open?definition:undefined} class="editor-card mechanism-card">
      <div class="configuration-row">
        <span class="configuration-icon">{#if definition.type==='mecanum'}<Layers size={17} strokeWidth={1.5}/>{:else}<Box size={17} strokeWidth={1.5}/>{/if}</span>
        <div class="configuration-identity"><h3>{definition.name}</h3><p>{schema?.label??definition.type}<span class="summary-divider">·</span>{definition.type==='custom'?definition.drivers.actuator||'Static model':`${Object.values(definition.drivers).filter(Boolean).length} driver connections`}</p></div>
        <span class="configuration-meta">{definition.visual?.parent?`On ${definition.visual.parent}`:'World origin'}</span>
        <div class="configuration-actions">
          <Collapsible.Trigger>{#snippet child({props})}<Button {...props} variant="ghost" size="sm" aria-label={`${editing===definition?'Finish editing':'Edit'} mechanism ${definition.name}`}>{#if editing===definition}<Check size={13}/>Done{:else}<Pencil size={13}/>Edit{/if}</Button>{/snippet}</Collapsible.Trigger>
          <Button variant="ghost" size="icon-sm" aria-label={`Remove mechanism ${definition.name}`} disabled={mechanisms.busy} onclick={()=>mechanisms.remove(definition)}><Trash2 size={14}/></Button>
        </div>
      </div>
      <Collapsible.Content><MechanismEditor bind:definition={mechanisms.definitions[mechanisms.definitions.indexOf(definition)]} {station} active={editing===definition}/></Collapsible.Content>
    </Collapsible.Root>
  {:else}<div class="empty-state"><Layers size={27} strokeWidth={1}/><h3>{mechanisms.definitions.length?'No matching mechanisms':'Build your robot'}</h3><p>{mechanisms.definitions.length?'Try a different name or mechanism type.':'Add a drivetrain, or a custom mechanism for a turret, arm, or slide.'}</p></div>{/each}
</div>
<div class="settings-footer"><div><p role="status" class:error-text={!!mechanisms.storageError||mechanisms.loaded&&!!mechanisms.error||!!station.physical?.mechanism_error}>{mechanisms.storageError||mechanisms.error||station.physical?.mechanism_error||mechanisms.message||(mechanisms.synchronized?'Simulation is up to date.':'Draft has unapplied changes.')}</p>{#if station.active||!station.hardware.ready}<small>{station.active?'Stop the OpMode before applying motion changes.':'Apply the hardware map first.'}</small>{/if}</div><Button variant="outline" disabled={!mechanisms.canApply} onclick={()=>mechanisms.apply()}>{#if mechanisms.busy}<LoaderCircle size={14} class="animate-spin"/>{:else}<Check size={14}/>{/if}{mechanisms.busy?'Updating simulation…':'Update simulation'}</Button></div>
