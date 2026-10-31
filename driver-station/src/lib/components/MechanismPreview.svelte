<script lang="ts">
  import RobotViewport from './RobotViewport.svelte';
  import { Switch } from '$lib/components/ui/switch';
  import type { Station } from '$lib/model/station.svelte';
  import type { Mechanism,MechanismState } from '$lib/model/types';
  import { flatten } from '$lib/model/configuration';
  import { format } from '$lib/utils';
  let { definition, station, active=true }: {definition:Mechanism;station:Station;active?:boolean}=$props();
  let preview=$state(false),input=$state(0);
  const actuator=$derived(flatten(station.hardware.devices).find(item=>item.name===definition.drivers.actuator));
  function rootOf(item:Mechanism) {
    let name=item.name,parent=item.visual?.parent;const seen=new Set([name]);
    while(parent&&!seen.has(parent)){seen.add(parent);name=parent;parent=station.mechanisms.definitions.find(candidate=>candidate.name===parent)?.visual?.parent;}
    return name;
  }
  const definitions=$derived(station.mechanisms.definitions.filter(item=>rootOf(item)===rootOf(definition)));
  const states=$derived.by(()=>{
    const devices=flatten(station.physical?.devices??[]);
    return definitions.map(item=>{
      if(item.type==='mecanum')return {name:item.name,type:item.type,drivers:item.drivers,state:{pose:{x_mm:0,y_mm:0,heading_rad:0},wheel_speeds_mm_s:{}}};
      const source=devices.find(device=>device.name===item.drivers.actuator);
      const position=item===definition&&preview?input:source?.type==='motor'?source.state.position/source.state.ticks_per_revolution*(source.state.direction??1):source?.state.position??item.options?.input_zero??0;
      return {name:item.name,type:item.type,drivers:item.drivers,state:{displacement:(position-(item.options?.input_zero??0))*(item.options?.travel??360)*(item.options?.direction??1)}};
    }) as MechanismState[];
  });
</script>
<aside class="mechanism-preview">
  <div class="mechanism-preview-heading"><span class="eyebrow">Live preview</span><span>Draft · not applied</span></div>
  <div class="mechanism-preview-canvas"><RobotViewport {active} preview diagnostics={station.diagnostics} label="Mechanism preview" showOrigins mechanisms={states} {definitions} selected={definition.name}/></div>
  {#if definition.type==='custom'}<div class="mechanism-preview-controls"><label class="preview-toggle"><Switch bind:checked={preview} size="sm" aria-label="Test input manually"/>Test input manually</label>{#if preview}<label class="field"><span>{actuator?.type==='servo'?'Servo position':'Motor revolutions'}<output>{format(input,2)}</output></span><input type="range" aria-label="Preview actuator position" min={actuator?.type==='servo'?0:-1} max="1" step="0.005" bind:value={input}/></label>{:else}<p>Following live actuator state. Enable manual input to test without running robot code.</p>{/if}</div>{/if}
</aside>
