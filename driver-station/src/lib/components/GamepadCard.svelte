<script lang="ts">
  import { Gamepad2, RotateCcw } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import type { Gamepads } from '$lib/model/gamepads.svelte';
  import { axes, buttons } from '$lib/model/gamepads.svelte';
  import { format, pretty } from '$lib/utils';
  import GamepadSelector from './GamepadSelector.svelte';
  let { gamepads, index, compact = false }: {gamepads:Gamepads;index:number;compact?:boolean} = $props();
</script>
<article class="panel gamepad-card" class:compact>
  <div class="panel-heading"><div class="title-with-icon"><Gamepad2 size={16}/><h3>Gamepad{compact?'':` ${index+1}`}</h3></div>{#if compact}<GamepadSelector {gamepads} compact/>{/if}<Button variant="ghost" size="icon" aria-label={`Reset gamepad ${index+1}`} onclick={()=>{gamepads.virtual[index]={};}}><RotateCcw size={13}/></Button></div>
  <p class="gamepad-source">{gamepads.physical[index]}</p>
  <div class="stick-pair">{#each ['left','right'] as stick}<div class="stick-display"><div class="stick-axis x"></div><div class="stick-axis y"></div><div class="stick-dot" style:transform={`translate(${Number(gamepads.latest[index][`${stick}_stick_x`]||0)*33}px,${Number(gamepads.latest[index][`${stick}_stick_y`]||0)*33}px)`}></div><span>{stick.toUpperCase()}</span></div>{/each}</div>
  {#if !compact}
    <div class="axis-controls">{#each axes as axis}<label><span>{pretty(axis)}</span><output>{format(Number(gamepads.virtual[index][axis]||0),2)}</output><input type="range" min={axis.endsWith('trigger')?0:-1} max="1" step=".01" aria-label={`Gamepad ${index+1} ${axis}`} value={Number(gamepads.virtual[index][axis]||0)} oninput={event=>gamepads.virtual[index][axis]=Number(event.currentTarget.value)}/></label>{/each}</div>
    <div class="gamepad-buttons">{#each buttons as button}<Button variant="outline" size="sm" aria-pressed={!!gamepads.virtual[index][button]} class={gamepads.virtual[index][button]?'pressed':''} onclick={()=>gamepads.virtual[index][button]=!gamepads.virtual[index][button]}>{button.length===1?button.toUpperCase():pretty(button)}</Button>{/each}</div>
  {:else}<div class="gamepad-mini-buttons">{#each ['a','b','x','y'] as name}<span class:pressed={!!gamepads.latest[index][name]}>{name.toUpperCase()}</span>{/each}<small>WASD <span>move</span> / JL <span>turn</span></small></div>{/if}
</article>
