<script lang="ts">
  import { Layers, Terminal, Gamepad2 } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import type { Station } from '$lib/model/station.svelte';
  import ControllerPanel from './ControllerPanel.svelte';
  import RobotViewport from './RobotViewport.svelte';
  import MechanismView from './MechanismView.svelte';
  import Telemetry from './Telemetry.svelte';
  import GamepadCard from './GamepadCard.svelte';
  import SelectField from './SelectField.svelte';
  let { station, onsettings, rendering=true }: {rendering?:boolean;station:Station;onsettings:(tab:string)=>void} = $props();
  let selected=$state(''), instrument=$state<''|'telemetry'|'gamepad'>('');
  const mechanisms=$derived(station.physical?.mechanisms ?? []);
  const active=$derived(mechanisms.find(item=>item.name===selected) ?? mechanisms[0]);
  function toggle(panel:'telemetry'|'gamepad') { instrument=instrument===panel?'':panel; }
</script>

<section class="overview-scene" class:instrument-open={!!instrument} aria-label="Robot simulation overview">
  <h1 class="sr-only">Overview</h1>
  <RobotViewport fieldControl active={rendering} diagnostics={station.diagnostics} {mechanisms} definitions={(station.physical?.mechanism_configuration ?? []).map(item=>({...item,visual:station.mechanisms.definitions.find(draft=>draft.name===item.name)?.visual}))} selected={active?.name ?? ''}/>
  <div class="scene-controller scene-overlay"><ControllerPanel {station} compact onHardware={()=>onsettings('hardware')}/></div>
  <aside class="scene-telemetry scene-overlay" class:instrument-visible={instrument==='telemetry'} id="overview-telemetry"><Telemetry data={station.telemetry} compact/></aside>
  <aside class="scene-gamepad scene-overlay" class:instrument-visible={instrument==='gamepad'} id="overview-gamepad"><GamepadCard gamepads={station.gamepads} index={station.gamepads.selected} compact/></aside>
  <section class="scene-drivebase scene-overlay panel" aria-label="Mechanism state">
    <div class="panel-heading"><div class="title-with-icon"><Layers size={14}/>
      {#if mechanisms.length>1}<SelectField id="scene-mechanism" aria-label="Viewed mechanism" class="scene-mechanism-select" items={mechanisms.map(mechanism=>({value:mechanism.name,label:mechanism.name}))} value={active?.name??''} onValueChange={next=>selected=next}/>
      {:else}<h3>{active?.name ?? 'Drivebase'}</h3>{/if}
    </div></div>
    {#if active}<MechanismView mechanism={active}/>{:else}<div class="scene-empty-state"><p>Add a mecanum drivetrain to see your robot move.</p><Button variant="outline" size="sm" onclick={()=>onsettings('mechanisms')}>Configure mechanism</Button></div>{/if}
  </section>
  <div class="scene-instrument-switch" role="group" aria-label="Overview overlays">
    <Button variant="outline" size="sm" aria-label="Telemetry" title="Toggle telemetry overlay" aria-controls="overview-telemetry" aria-expanded={instrument==='telemetry'} aria-pressed={instrument==='telemetry'} onclick={()=>toggle('telemetry')}><Terminal size={14}/><span class="scene-instrument-label">Telemetry</span></Button>
    <Button variant="outline" size="sm" aria-label="Gamepad" title="Toggle gamepad overlay" aria-controls="overview-gamepad" aria-expanded={instrument==='gamepad'} aria-pressed={instrument==='gamepad'} onclick={()=>toggle('gamepad')}><Gamepad2 size={14}/><span class="scene-instrument-label">Gamepad</span></Button>
  </div>
</section>
