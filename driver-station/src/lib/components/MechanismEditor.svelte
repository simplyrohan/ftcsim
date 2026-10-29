<script lang="ts">
  import { Trash2, Box, Cable, SlidersHorizontal } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import OptionField from './OptionField.svelte';
  import MechanismModelEditor from './MechanismModelEditor.svelte';
  import MechanismPreview from './MechanismPreview.svelte';
  import { flatten, optionValue } from '$lib/model/configuration';
  import type { Station } from '$lib/model/station.svelte';
  import type { Mechanism } from '$lib/model/types';
  let { definition, station, active=true }: {definition:Mechanism;station:Station;active?:boolean}=$props();
  const mechanisms=$derived(station.mechanisms),schema=$derived(mechanisms.catalog.find(item=>item.type===definition.type));
  let tab=$state('connections');
  function rename(name:string){const previous=definition.name;definition.name=name;for(const item of mechanisms.definitions)if(item.visual?.parent===previous)item.visual.parent=name;mechanisms.save();}
  function options(group:string){return schema?.options.filter(option=>definition.type==='custom' || (group==='mounting'?option.name.endsWith('_direction'):!option.name.endsWith('_direction')))??[];}
</script>
<article class="mechanism-editor">
  <div class="mechanism-editor-identity"><label class="field"><span>Mechanism name</span><Input value={definition.name} required disabled={mechanisms.busy} onchange={event=>{const name=event.currentTarget.value.trim();if(!name||mechanisms.definitions.some(item=>item!==definition&&item.name===name)){event.currentTarget.value=definition.name;mechanisms.message='Choose a unique, nonempty mechanism name.';return;}rename(name);}}/></label><span class="pill">{schema?.label??definition.type}</span><Button variant="ghost" type="button" size="icon" aria-label={`Remove mechanism ${definition.name}`} disabled={mechanisms.busy} onclick={()=>mechanisms.remove(definition)}><Trash2 size={15}/></Button></div>
  <div class="mechanism-editor-layout"><div class="mechanism-editor-fields">
    <div class="mechanism-editor-tabs" role="group" aria-label="Mechanism editor sections"><Button type="button" variant="ghost" size="sm" aria-pressed={tab==='connections'} onclick={()=>tab='connections'}><Cable size={13}/>Connections</Button><Button type="button" variant="ghost" size="sm" aria-pressed={tab==='parameters'} onclick={()=>tab='parameters'}><SlidersHorizontal size={13}/>{definition.type==='custom'?'Motion':'Drive geometry'}</Button><Button type="button" variant="ghost" size="sm" aria-pressed={tab==='model'} onclick={()=>tab='model'}><Box size={13}/>Model &amp; origin</Button></div>
    {#if schema}
      {#if tab==='connections'}
        <section class="mechanism-section"><div class="mechanism-section-title"><span class="step-number">01</span><div><h3>{definition.type==='custom'?'Actuator source':'Wheel connections'}</h3><p>{definition.type==='custom'?'Read a driver’s position without changing its behavior.':'Match each wheel to its motor, viewed from above.'}</p></div></div>
        <div class="form-grid mechanism-bindings" class:wheel-binding-grid={definition.type==='mecanum'}>
          {#each schema.drivers as slot}
            {@const candidates=flatten(station.hardware.devices).filter(device=>slot.types.includes(device.type))}
            <label class="field" class:pinpoint-binding={slot.name==='pinpoint'}><span>{slot.label}</span><select class="control" required={slot.required} disabled={mechanisms.busy} value={definition.drivers[slot.name]??''} onchange={event=>{if(event.currentTarget.value)definition.drivers[slot.name]=event.currentTarget.value;else delete definition.drivers[slot.name];mechanisms.save();}}><option value="">{slot.required?'Choose a motor…':slot.name==='actuator'?'Unbound · static model':'No sensor connected'}</option>{#if definition.drivers[slot.name]&&!candidates.some(device=>device.name===definition.drivers[slot.name])}<option value={definition.drivers[slot.name]}>{definition.drivers[slot.name]} (unavailable)</option>{/if}{#each candidates as driver}<option value={driver.name}>{driver.name} · {driver.type}</option>{/each}</select></label>
            {#if slot.name==='pinpoint'}{@const bound=candidates.find(item=>item.name===definition.drivers[slot.name])}<p class="sensor-binding-note">{bound?`${bound.name} → ${(bound.children??[]).map(child=>child.name).join(' / ')}. The drivetrain updates these encoders and IMU yaw.`:'Optional: connect the Pinpoint and its two odometry pods to this drivebase.'}</p>{/if}
          {/each}
        </div></section>
        {#if definition.type==='mecanum'}<section class="mechanism-section"><div class="mechanism-section-title"><span class="step-number">02</span><div><h3>Wheel mounting</h3><p>Apply physical mounting reversal on top of each motor’s direction.</p></div></div><div class="form-grid">{#each options('mounting') as option}<OptionField {option} disabled={mechanisms.busy} bind:value={()=>optionValue(definition.options,option),value=>{(definition.options??={})[option.name]=value;}} onchange={()=>mechanisms.save()}/>{/each}</div></section>{:else}<p class="mechanism-help">Motor input is measured in output-shaft revolutions, including physical direction. Servo input is normalized from 0 to 1. A custom mechanism can observe a driver already used elsewhere.</p>{/if}
      {:else if tab==='parameters'}
        <section class="mechanism-section"><div class="mechanism-section-title"><span class="step-number">01</span><div><h3>{definition.type==='custom'?'Movement mapping':'Drive geometry'}</h3><p>{definition.type==='custom'?'Map actuator position to motion at the model origin.':'Dimensions determine wheel travel, strafe speed, and turning radius.'}</p></div></div>
        <div class="form-grid">{#each options('geometry') as option}
          {@const mapped=definition.type==='custom' && option.name==='travel'?{...option,label:`${definition.options?.motion==='translation'?'Millimeters':'Degrees'} per ${flatten(station.hardware.devices).find(item=>item.name===definition.drivers.actuator)?.type==='servo'?'full servo range (0 → 1)':'motor revolution'}`} : definition.type==='custom' && option.name==='input_zero'?{...option,label:'Input position at starting pose'} : option}
          <OptionField option={mapped} disabled={mechanisms.busy} bind:value={()=>optionValue(definition.options,option),value=>{(definition.options??={})[option.name]=value;}} onchange={()=>mechanisms.save()}/>
        {/each}</div>
        {#if definition.type==='custom'}<div class="motion-equation"><span>Movement = (input − starting input) × travel × direction</span><p>Axis is relative to the starting orientation. Z rotates a turret about the vertical axis; translation can model a slide. Servo positions hold when PWM is disabled.</p></div>{:else}<p class="mechanism-help">Motor RPM and encoder resolution come from the hardware map. External gearing is motor output turns per wheel turn; use 1 for direct drive.</p>{/if}</section>
      {:else}<MechanismModelEditor {definition} definitions={mechanisms.definitions} disabled={mechanisms.busy} onchange={()=>mechanisms.save()}/>{/if}
    {/if}
  </div><MechanismPreview {definition} {station} {active}/></div>
</article>
