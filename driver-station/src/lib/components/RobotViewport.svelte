<script lang="ts">
  import { onMount } from 'svelte';
  import { Box, ScanLine, Crosshair, RotateCcw } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import type { Diagnostics } from '$lib/model/diagnostics.svelte';
  import type { Mechanism, MechanismState } from '$lib/model/types';
  import type { DrivebaseViewport, CameraView } from '$lib/scene/viewport';
  let { mechanisms, definitions, selected, showOrigins=false, active=true, preview=false, diagnostics, label='Overview' }: {active?:boolean;preview?:boolean;diagnostics?:Diagnostics;label?:string;showOrigins?:boolean;mechanisms:MechanismState[];definitions:Mechanism[];selected:string} = $props();
  let canvas:HTMLCanvasElement;
  let viewport=$state.raw<DrivebaseViewport|null>(null);
  let view=$state<CameraView>('perspective'), follow=$state(true), error=$state(''), ready=$state(false);
  $effect(()=>{if(active)viewport?.sync(mechanisms,definitions,selected);});
  $effect(()=>viewport?.setActive(active));
  $effect(()=>viewport?.setFollow(follow));
  $effect(()=>viewport?.setView(view));
  let mounted=$state(false),attempted=$state(false);
  let cancelled=false;
  let metrics:ReturnType<Diagnostics['registerView']>|undefined;
  $effect(()=>{if(mounted&&active&&!viewport&&!attempted)void initialize();});
  async function initialize(){
    attempted=true;
    try {
      const {DrivebaseViewport}=await import('$lib/scene/viewport');
      if(cancelled)return;
      if(!active){attempted=false;return;}
      metrics=diagnostics?.registerView(label);
      viewport=new DrivebaseViewport(canvas,message=>error=message,showOrigins,{preview,onMetrics:metrics?.report});ready=true;
    } catch {if(!cancelled)error='3D rendering is unavailable in this browser. Robot controls are still available.';}
  }
  onMount(()=>{mounted=true;return()=>{cancelled=true;viewport?.dispose();viewport=null;metrics?.dispose();};});

</script>

<div class="robot-viewport">
  <canvas bind:this={canvas} aria-label="Live 3D robot simulation. Drag to orbit, scroll to zoom, right-drag to pan." tabindex="0"></canvas>
  {#if error}<p class="scene-render-message" role="status">{error}</p>{:else if !ready}<p class="scene-render-message">Preparing 3D view…</p>{/if}
  <div class="scene-camera-controls" role="group" aria-label="3D camera controls">
    <Button variant="outline" size="sm" aria-label="Perspective view" title="Perspective view" aria-pressed={view==='perspective'} disabled={!ready} onclick={()=>view='perspective'}><Box size={14}/><span class="scene-toolbar-label">Perspective</span></Button>
    <Button variant="outline" size="sm" aria-label="Top view" title="Top view" aria-pressed={view==='top'} disabled={!ready} onclick={()=>view='top'}><ScanLine size={14}/><span class="scene-toolbar-label">Top</span></Button>
    <span class="scene-toolbar-divider"></span>
    <Button variant="outline" size="sm" aria-label="Follow robot" title="Follow robot" aria-pressed={follow} disabled={!ready} onclick={()=>follow=!follow}><Crosshair size={14}/><span class="scene-toolbar-label">Follow</span></Button>
    <Button variant="outline" size="sm" aria-label="Recenter camera" title="Recenter camera" disabled={!ready} onclick={()=>viewport?.recenter()}><RotateCcw size={14}/></Button>
  </div>
  <p class="scene-camera-hint">Drag to orbit <span>·</span> Scroll to zoom <span>·</span> Right-drag to pan</p>
</div>
