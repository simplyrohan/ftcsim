<script lang="ts">
  import { ChevronRight, Play, Square, RotateCcw, Clock3 } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import type { Station } from '$lib/model/station.svelte';
  import { format } from '$lib/utils';
  let { station, onHardware, compact=false }: {station:Station;onHardware:()=>void;compact?:boolean} = $props();
</script>
<section class="controller-panel panel" class:controller-compact={compact} aria-label="Robot Controller">
        <div class="opmode-selector"><label for="opmode">OpMode</label><select id="opmode" class="opmode-select" disabled={!station.connected || !station.controller || station.active || !!station.pendingCommand} value={station.selected} onchange={event=>station.select(event.currentTarget.value)}>{#if !station.opmodes.length}<option value="">Select an OpMode</option>{/if}{#each station.opmodes as mode}<option value={mode.name}>{mode.name} · {mode.flavor}</option>{/each}</select></div>
        <div class="lifecycle-state"><span class="pill"><span class="status-dot" class:offline={!station.active}></span>{station.connected&&!station.connecting?station.status:'idle'}</span><span class="runtime"><Clock3 size={13}/>{format(station.elapsed,1)}<small>s</small></span></div>
        <div class="lifecycle-controls"><Button variant="outline" title={station.initReason} disabled={!station.canInit} onclick={()=>station.command('init')}><RotateCcw size={14}/>{station.pendingCommand==='init'?'Initializing…':'INIT'}</Button><Button variant="outline" disabled={!station.canStart} onclick={()=>station.command('start')}><Play size={14}/>{station.pendingCommand==='start'?'Starting…':'START'}</Button><Button variant="outline" disabled={!station.connected || !station.controller} onclick={()=>station.command('stop')}><Square size={13}/>{station.pendingCommand==='stop'?'Stopping…':'STOP'}</Button></div>
        <div class="controller-caption"><span class:error-text={!!station.error}>{station.error || (station.connected&&!station.connecting?(station.notice || station.initReason):'')}</span><button onclick={onHardware}><span class="status-dot" class:offline={!station.hardware.ready}></span>{station.hardware.ready?'Hardware applied':'Configure hardware'}<ChevronRight size={11}/></button></div>
      </section>
