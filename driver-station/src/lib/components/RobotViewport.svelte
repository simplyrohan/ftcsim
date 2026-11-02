<script lang="ts">
  import { onMount } from 'svelte';
  import { slidingIndicator } from '$lib/actions/sliding-indicator';
  import { Box, ScanLine, Crosshair, RotateCcw, Map, LoaderCircle } from '@lucide/svelte';
  import { Separator } from '$lib/components/ui/separator';
  import { Toolbar } from 'bits-ui';
  import TooltipButton from './TooltipButton.svelte';
  import type { Diagnostics } from '$lib/model/diagnostics.svelte';
  import type { Mechanism, MechanismState } from '$lib/model/types';
  import type { DrivebaseViewport, CameraView } from '$lib/scene/viewport';
  let { mechanisms, definitions, selected, showOrigins=false, active=true, preview=false, fieldControl=false, diagnostics, label='Overview' }: {fieldControl?:boolean;active?:boolean;preview?:boolean;diagnostics?:Diagnostics;label?:string;showOrigins?:boolean;mechanisms:MechanismState[];definitions:Mechanism[];selected:string} = $props();
  let canvas:HTMLCanvasElement;
  let viewport=$state.raw<DrivebaseViewport|null>(null);
  let view=$state<CameraView>('perspective'), follow=$state(true), error=$state(''), ready=$state(false);
  let field=$state(true),fieldStatus=$state('');
  let loading=$state<string[]>([]);
  $effect(()=>{if(active)viewport?.sync(mechanisms,definitions,selected);});
  $effect(()=>viewport?.setActive(active));
  $effect(()=>viewport?.setFollow(follow));
  $effect(()=>viewport?.setView(view));
  $effect(()=>{if(fieldControl)void viewport?.setField(field);});
  function toggleField(){field=!field;try{localStorage.setItem('ftcsim.fieldVisible',String(field));}catch{/* View remains usable without storage. */}}
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
      viewport=new DrivebaseViewport(canvas,message=>error=message,showOrigins,{preview,onMetrics:metrics?.report,onFieldStatus:message=>fieldStatus=message,onLoading:names=>loading=names});ready=true;
    } catch {if(!cancelled)error='3D rendering is unavailable in this browser. Robot controls are still available.';}
  }
  onMount(()=>{try{field=localStorage.getItem('ftcsim.fieldVisible')!=='false';}catch{/* Use the default. */}mounted=true;return()=>{cancelled=true;viewport?.dispose();viewport=null;metrics?.dispose();};});

</script>

<div class="robot-viewport">
  <canvas bind:this={canvas} aria-label="Live 3D robot simulation. Drag to orbit, scroll to zoom, right-drag to pan." tabindex="0"></canvas>
  {#if error}<p class="scene-render-message" role="status">{error}</p>{:else if !ready}<p class="scene-render-message">Preparing 3D view…</p>{/if}
  {#if loading.length}
    <div class="scene-loading" role="status" aria-live="polite" aria-atomic="true">
      <LoaderCircle size={14} class="animate-spin" aria-hidden="true"/>
      <span>Loading {loading[0]}</span>
    </div>
  {/if}
  <Toolbar.Root class="scene-camera-controls" aria-label="3D camera controls">
    <Toolbar.Group type="single" bind:value={()=>view,next=>{if(next)view=next as CameraView;}} aria-label="Camera view">
      {#snippet child({props})}
        <div {...props} class="scene-view-switch sliding-toggle" use:slidingIndicator>
          <Toolbar.GroupItem value="perspective" disabled={!ready}>{#snippet child({props})}<TooltipButton {...props} label="Perspective view" variant="outline" size="sm"><Box size={14}/><span class="scene-toolbar-label">Perspective</span></TooltipButton>{/snippet}</Toolbar.GroupItem>
          <Toolbar.GroupItem value="top" disabled={!ready}>{#snippet child({props})}<TooltipButton {...props} label="Top view" variant="outline" size="sm"><ScanLine size={14}/><span class="scene-toolbar-label">Top</span></TooltipButton>{/snippet}</Toolbar.GroupItem>
        </div>
      {/snippet}
    </Toolbar.Group>
    <Separator orientation="vertical" class="scene-toolbar-divider"/>
    {#if fieldControl}<Toolbar.Button aria-pressed={field} disabled={!ready} onclick={toggleField}>{#snippet child({props})}<TooltipButton {...props} label="Show field" variant="outline" size="sm"><Map size={14}/><span class="scene-toolbar-label">Field</span></TooltipButton>{/snippet}</Toolbar.Button>{/if}
    <Toolbar.Button aria-pressed={follow} disabled={!ready} onclick={()=>follow=!follow}>{#snippet child({props})}<TooltipButton {...props} label="Follow robot" variant="outline" size="sm"><Crosshair size={14}/><span class="scene-toolbar-label">Follow</span></TooltipButton>{/snippet}</Toolbar.Button>
    <Toolbar.Button disabled={!ready} onclick={()=>viewport?.recenter()}>{#snippet child({props})}<TooltipButton {...props} label="Recenter camera" hint="Recenter camera. Drag to orbit, scroll to zoom, right-drag to pan." variant="outline" size="sm"><RotateCcw size={14}/></TooltipButton>{/snippet}</Toolbar.Button>
  </Toolbar.Root>
  {#if fieldControl && fieldStatus}<p class="scene-field-status" role="status">{fieldStatus}</p>{/if}
</div>
