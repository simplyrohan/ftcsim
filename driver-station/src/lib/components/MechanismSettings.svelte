<script lang="ts">
  import { Plus, Trash2, Check, LoaderCircle, Layers } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import OptionField from './OptionField.svelte';
  import { flatten, optionValue } from '$lib/model/configuration';
  import type { Station } from '$lib/model/station.svelte';
  let { station }: {station:Station} = $props();
  const mechanisms = $derived(station.mechanisms);
  let selectedType = $state('mecanum');
</script>
<div class="settings-heading"><div><h2>Mechanisms</h2><p>Connect drivers to physical models. Your robot code sees only the devices.</p></div><span class="pill">{mechanisms.definitions.length} configured</span></div>
<form onsubmit={event=>{event.preventDefault();void mechanisms.apply();}}>
  <div class="toolbar driver-picker"><label class="sr-only" for="mechanism-type">Mechanism type</label><select id="mechanism-type" class="control" bind:value={selectedType}>{#each mechanisms.catalog as type}<option value={type.type}>{type.label}</option>{/each}</select><Button variant="outline" type="button" size="sm" disabled={!mechanisms.loaded || mechanisms.busy || mechanisms.definitions.length>=64} onclick={()=>mechanisms.add(selectedType)}><Plus size={14}/>Add mechanism</Button></div>
  <div class="configuration-list">
    {#each mechanisms.definitions as definition}
      {@const schema=mechanisms.catalog.find(item=>item.type===definition.type)}
      <article class="editor-card"><div class="editor-card-header"><div class="editor-title"><Layers size={15}/><strong>{definition.name}</strong><span class="muted">{schema?.label ?? definition.type}</span></div><Button variant="ghost" type="button" size="icon" aria-label={`Remove mechanism ${definition.name}`} disabled={mechanisms.busy} onclick={()=>mechanisms.remove(definition)}><Trash2 size={14}/></Button></div>
      <div class="editor-card-body"><label class="field"><span>Name</span><Input value={definition.name} oninput={event=>{definition.name=event.currentTarget.value;mechanisms.save();}} required disabled={mechanisms.busy}/></label>
      {#if schema}<div class="form-grid mechanism-bindings">
        {#each schema.drivers as slot}
          {@const candidates=flatten(station.hardware.devices).filter(device=>slot.types.includes(device.type))}
          <label class="field"><span>{slot.label}</span><select class="control" required={slot.required} disabled={mechanisms.busy} value={definition.drivers[slot.name] ?? ''} onchange={event=>{if(event.currentTarget.value)definition.drivers[slot.name]=event.currentTarget.value;else delete definition.drivers[slot.name];mechanisms.save();}}><option value="">{slot.required?'Choose a motor…':'No sensor connected'}</option>{#if definition.drivers[slot.name]&&!candidates.some(device=>device.name===definition.drivers[slot.name])}<option value={definition.drivers[slot.name]}>{definition.drivers[slot.name]} (unavailable)</option>{/if}{#each candidates as driver}<option value={driver.name}>{driver.name}</option>{/each}</select></label>
          {#if Object.keys(slot.children ?? {}).length}
            {@const bound=candidates.find(driver=>driver.name===definition.drivers[slot.name])}
            <div class="sensor-binding-note">
              {#if bound}
                <p>{bound.name} reads {Object.keys(slot.children ?? {}).map(port=>bound.children?.find(child=>child.port===port)?.name ?? `${port.toUpperCase()} pod missing`).join(' / ')}. This mechanism drives their encoder counts and the IMU's yaw.</p>
              {:else}
                <p>No localization sensor linked. The drivebase can move while the Pinpoint and its encoders stay independent.</p>
                {#if candidates.length===1}<Button variant="outline" type="button" size="sm" disabled={mechanisms.busy} onclick={()=>{definition.drivers[slot.name]=candidates[0].name;mechanisms.save();}}>Link {candidates[0].name}</Button>{/if}
              {/if}
            </div>
          {/if}
        {/each}
      </div><div class="section-rule"><span class="eyebrow">Physical dimensions &amp; mounting</span></div><div class="form-grid">
        {#each schema.options as option}<OptionField {option} disabled={mechanisms.busy} bind:value={()=>optionValue(definition.options,option),value=>{(definition.options??={})[option.name]=value;}} onchange={()=>mechanisms.save()}/>{/each}
      </div><p class="fine-print">{schema.description}</p>{/if}</div></article>
    {:else}<div class="empty-state"><Layers size={27} strokeWidth={1}/><h3>Give your robot a physical model</h3><p>Add a mecanum drivetrain and connect four motors, with optional Pinpoint odometry.</p></div>{/each}
  </div>
  <div class="settings-footer"><div><p role="status" class:error-text={!!mechanisms.storageError || mechanisms.loaded&&!!mechanisms.error || !!station.physical?.mechanism_error}>{mechanisms.storageError || mechanisms.error || station.physical?.mechanism_error || mechanisms.message || (mechanisms.synchronized?'Mechanisms are applied.':'Draft has unapplied changes.')}</p><small>{station.active?'Stop the OpMode before applying changes.':!station.hardware.ready?'Apply the hardware map first.':'Saved separately from the hardware map.'}</small></div><Button variant="outline" type="submit" disabled={!mechanisms.canApply}>{#if mechanisms.busy}<LoaderCircle size={14} class="animate-spin"/>{:else}<Check size={14}/>{/if}Apply to simulator</Button></div>
</form>
