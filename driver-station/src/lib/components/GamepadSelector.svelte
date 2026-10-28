<script lang="ts">
  import { Button } from '$lib/components/ui/button';
  import type { Gamepads } from '$lib/model/gamepads.svelte';
  let { gamepads, compact = false }: {gamepads:Gamepads;compact?:boolean} = $props();
  const controllers = [0,1] as const;
</script>

<div class="gamepad-selector" class:compact role="group" aria-label="Keyboard and virtual controller">
  {#each controllers as index}
    <Button variant="outline" size="sm" aria-label={`Control Gamepad ${index+1}`} aria-pressed={gamepads.selected===index} onclick={()=>gamepads.selectController(index)}>
      {compact?index+1:`Gamepad ${index+1}`}
    </Button>
  {/each}
</div>
