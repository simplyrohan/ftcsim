<script lang="ts">
  import { Box, Cable, SlidersHorizontal } from '@lucide/svelte';
  import { Input } from '$lib/components/ui/input';
  import * as Tabs from '$lib/components/ui/tabs';
  import OptionField from './OptionField.svelte';
  import MechanismModelEditor from './MechanismModelEditor.svelte';
  import MechanismPreview from './MechanismPreview.svelte';
  import SelectField from './SelectField.svelte';
  import HelpTooltip from './HelpTooltip.svelte';
  import { flatten, optionValue } from '$lib/model/configuration';
  import type { Station } from '$lib/model/station.svelte';
  import type { Mechanism } from '$lib/model/types';
  let { definition=$bindable(), station, active=true }: {definition:Mechanism;station:Station;active?:boolean}=$props();
  const mechanisms=$derived(station.mechanisms),schema=$derived(mechanisms.catalog.find(item=>item.type===definition.type));
  let tab=$state('connections');
  function rename(name:string){const previous=definition.name;definition.name=name;for(const item of mechanisms.definitions)if(item.visual?.parent===previous)item.visual.parent=name;mechanisms.save();}
  function options(group:string){return schema?.options.filter(option=>definition.type==='custom' || (group==='mounting'?option.name.endsWith('_direction'):!option.name.endsWith('_direction')))??[];}
</script>
<article class="mechanism-editor">
  <div class="mechanism-editor-identity"><label class="field"><span>Mechanism name</span><Input value={definition.name} required disabled={mechanisms.busy} onchange={event=>{const name=event.currentTarget.value.trim();if(!name||mechanisms.definitions.some(item=>item!==definition&&item.name===name)){event.currentTarget.value=definition.name;mechanisms.message='Choose a unique, nonempty mechanism name.';return;}rename(name);}}/></label></div>
  <div class="mechanism-editor-layout"><div class="mechanism-editor-fields">
    <Tabs.Root bind:value={tab} class="mechanism-tabs">
      <Tabs.List variant="line" class="mechanism-editor-tabs" aria-label="Mechanism editor sections"><Tabs.Trigger value="connections"><Cable size={14}/>Connections</Tabs.Trigger><Tabs.Trigger value="parameters"><SlidersHorizontal size={14}/>{definition.type==='custom'?'Motion':'Drive geometry'}</Tabs.Trigger><Tabs.Trigger value="model"><Box size={14}/>Model &amp; origin</Tabs.Trigger></Tabs.List>
    {#if schema}
      <Tabs.Content value="connections">
        <section class="mechanism-section"><div class="mechanism-section-title"><span class="step-number">01</span><h3>{definition.type==='custom'?'Actuator source':'Wheel connections'}<HelpTooltip label="About driver connections" text={definition.type==='custom'?'Read a driver’s position without changing its behavior. Motor input is output-shaft revolutions, including physical direction; servo input is 0 to 1. A driver can be observed by multiple mechanisms.':'Match each wheel to its motor, viewed from above.'}/></h3></div>
        <div class="form-grid mechanism-bindings" class:wheel-binding-grid={definition.type==='mecanum'}>
          {#each schema.drivers as slot}
            {@const candidates=flatten(station.hardware.devices).filter(device=>slot.types.includes(device.type))}
            <div class="field" class:pinpoint-binding={slot.name==='pinpoint'}><span>{slot.label}{#if slot.name==='pinpoint'}{@const bound=candidates.find(item=>item.name===definition.drivers[slot.name])}<HelpTooltip label="About Pinpoint feedback" text={bound?`${bound.name} → ${(bound.children??[]).map(child=>child.name).join(' / ')}. The drivetrain updates these encoders and IMU yaw.`:'Optional: connect the Pinpoint and its two odometry pods to this drivebase.'}/>{/if}</span><SelectField aria-label={slot.label} required={slot.required} disabled={mechanisms.busy} value={definition.drivers[slot.name]??''} items={[{value:'',label:slot.required?'Choose a motor…':slot.name==='actuator'?'Unbound · static model':'No sensor connected'},...(definition.drivers[slot.name]&&!candidates.some(device=>device.name===definition.drivers[slot.name])?[{value:definition.drivers[slot.name],label:`${definition.drivers[slot.name]} (unavailable)`}]:[]),...candidates.map(driver=>({value:driver.name,label:`${driver.name} · ${driver.type}`}))]} onValueChange={next=>{if(next)definition.drivers[slot.name]=next;else delete definition.drivers[slot.name];mechanisms.save();}}/></div>
          {/each}
        </div></section>
        {#if definition.type==='mecanum'}<section class="mechanism-section"><div class="mechanism-section-title"><span class="step-number">02</span><h3>Wheel mounting <HelpTooltip label="About wheel mounting" text="Apply physical mounting reversal on top of each motor’s direction."/></h3></div><div class="form-grid">{#each options('mounting') as option}<OptionField {option} disabled={mechanisms.busy} bind:value={()=>optionValue(definition.options,option),value=>{(definition.options??={})[option.name]=value;}} onchange={()=>mechanisms.save()}/>{/each}</div></section>{/if}
      </Tabs.Content>
      <Tabs.Content value="parameters">
        <section class="mechanism-section"><div class="mechanism-section-title"><span class="step-number">01</span><h3>{definition.type==='custom'?'Movement mapping':'Drive geometry'}<HelpTooltip label="About motion parameters" text={definition.type==='custom'?'Map actuator position to motion at the model origin. The axis follows the starting orientation. Z rotates about the vertical axis; translation can model a slide. Servo positions hold when PWM is disabled.':'Dimensions determine wheel travel, strafe speed, and turning radius. Motor RPM and encoder resolution come from the hardware map. External gearing is motor output turns per wheel turn; use 1 for direct drive.'}/></h3></div>
        <div class="form-grid">{#each options('geometry') as option}
          {@const mapped=definition.type==='custom' && option.name==='travel'?{...option,label:`${definition.options?.motion==='translation'?'Millimeters':'Degrees'} per ${flatten(station.hardware.devices).find(item=>item.name===definition.drivers.actuator)?.type==='servo'?'full servo range (0 → 1)':'motor revolution'}`} : definition.type==='custom' && option.name==='input_zero'?{...option,label:'Input position at starting pose'} : option}
          <OptionField option={mapped} disabled={mechanisms.busy} bind:value={()=>optionValue(definition.options,option),value=>{(definition.options??={})[option.name]=value;}} onchange={()=>mechanisms.save()}/>
        {/each}</div>
        {#if definition.type==='custom'}<div class="motion-equation"><span>Movement = (input − starting input) × travel × direction</span></div>{/if}</section>
      </Tabs.Content>
      <Tabs.Content value="model"><MechanismModelEditor bind:definition confirmation={station.confirmation} definitions={mechanisms.definitions} disabled={mechanisms.busy} onchange={()=>mechanisms.save()}/></Tabs.Content>
    {/if}
    </Tabs.Root>
  </div><MechanismPreview {definition} {station} {active}/></div>
</article>
