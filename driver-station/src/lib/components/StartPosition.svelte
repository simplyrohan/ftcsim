<script lang="ts">
  import { ChevronDown, MapPin, Save, Trash2 } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import * as Collapsible from '$lib/components/ui/collapsible';
  import type { Station } from '$lib/model/station.svelte';
  import { format } from '$lib/utils';
  import SelectField from './SelectField.svelte';
  import HelpTooltip from './HelpTooltip.svelte';
  let {station}:{station:Station}=$props();
  let open=$state(false),name=$state(''),preset=$state('');
  const positions=$derived(station.startPositions);
  const pose=$derived(positions.current);
  const editable=$derived(positions.editable);
  const id=$props.id();
  $effect(()=>{station.selected;preset='';name='';});
  function coordinate(key:'x_mm'|'y_mm'|'heading_deg',value:string){preset='';positions.update({[key]:value===''?NaN:Number(value)});}
</script>

<Collapsible.Root class="start-position" bind:open>
  <Collapsible.Trigger class="start-position-trigger" aria-label="Start position">
    <span><MapPin size={13}/>Start position</span>
    <span class="start-position-summary">{pose.enabled?`${format(pose.x_mm,0)}, ${format(pose.y_mm,0)} · ${format(pose.heading_deg,0)}°`:'Not set'}<ChevronDown size={13}/></span>
  </Collapsible.Trigger>
  <Collapsible.Content class="start-position-content">
    <div class="label-with-help"><label class="start-position-enable"><input type="checkbox" checked={pose.enabled} disabled={!editable} onchange={event=>positions.update({enabled:event.currentTarget.checked})}/>Place before INIT for this OpMode</label><HelpTooltip label="About start positions" text="Field center is (0, 0). +X is forward, +Y is left; heading is counterclockwise. Sensor origins stay under TeamCode control. Coordinates save automatically for this OpMode."/></div>
    {#if positions.drivetrains.length>1 || pose.mechanism && !positions.drivetrains.some(item=>item.name===pose.mechanism)}
      <label class="start-position-field" for={`${id}-drive`}>Drivetrain<SelectField id={`${id}-drive`} aria-label="Start position drivetrain" value={positions.target} disabled={!editable} items={[...(!positions.drivetrains.some(item=>item.name===positions.target)?[{value:positions.target,label:positions.target||'Select drivetrain'}]:[]),...positions.drivetrains.map(item=>({value:item.name,label:item.name}))]} onValueChange={next=>positions.update({mechanism:next})}/></label>
    {/if}
    <div class="start-position-coordinates">
      <label class="start-position-field" for={`${id}-x`}>X <small>mm</small><Input id={`${id}-x`} type="number" step="any" value={pose.x_mm} disabled={!editable} oninput={event=>coordinate('x_mm',event.currentTarget.value)}/></label>
      <label class="start-position-field" for={`${id}-y`}>Y <small>mm</small><Input id={`${id}-y`} type="number" step="any" value={pose.y_mm} disabled={!editable} oninput={event=>coordinate('y_mm',event.currentTarget.value)}/></label>
      <label class="start-position-field" for={`${id}-heading`}>Heading <small>°</small><Input id={`${id}-heading`} type="number" step="any" value={pose.heading_deg} disabled={!editable} oninput={event=>coordinate('heading_deg',event.currentTarget.value)}/></label>
    </div>
    <div class="start-position-presets"><SelectField id={`${id}-preset`} aria-label="Start position preset" value={preset} disabled={!editable || !positions.presets.length} items={[{value:'',label:'Load a preset…'},...positions.presets.map(item=>({value:item.id,label:item.name}))]} onValueChange={next=>{preset=next;positions.usePreset(preset);}}/><Button variant="ghost" size="icon" aria-label="Delete selected start preset" disabled={!editable || !preset} onclick={async()=>{if(await positions.deletePreset(preset))preset='';}}><Trash2 size={13}/></Button></div>
    <form class="start-position-presets" onsubmit={async event=>{event.preventDefault();if(await positions.savePreset(name)){name='';preset='';}}}><label class="sr-only" for={`${id}-name`}>Preset name</label><Input id={`${id}-name`} placeholder="Preset name" maxlength={80} bind:value={name} disabled={!editable}/><Button variant="outline" size="sm" type="submit" disabled={!editable || !name.trim() || ![pose.x_mm,pose.y_mm,pose.heading_deg].every(Number.isFinite)}><Save size={13}/>Save</Button></form>
    <div class="start-position-footer"><span>{!station.selected?'Select an OpMode to edit its start position.':station.active?'Stop the OpMode to edit.':!positions.drivetrains.length?'Apply a drivetrain in Settings.':''}</span><Button variant="outline" size="sm" disabled={!editable || !station.simulatorConnected || !positions.drivetrains.length} onclick={()=>positions.preview()}>{positions.busy?'Placing…':'Place now'}</Button></div>
    {#if positions.error}<p class="error-text" role="alert">{positions.error}</p>{/if}
  </Collapsible.Content>
</Collapsible.Root>
