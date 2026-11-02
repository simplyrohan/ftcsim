<script lang="ts">
  import { Collapsible as CollapsiblePrimitive } from 'bits-ui';
  import { slide } from 'svelte/transition';
  import { cubicOut } from 'svelte/easing';
  import { MediaQuery } from 'svelte/reactivity';
  import { cn, type WithoutChild } from '$lib/utils';
  let { ref=$bindable(null), children, class:className, ...restProps }: WithoutChild<CollapsiblePrimitive.ContentProps>=$props();
  const reducedMotion=new MediaQuery('(prefers-reduced-motion: reduce)');
</script>
<CollapsiblePrimitive.Content bind:ref {...restProps} forceMount>
  {#snippet child({props,open})}
    {#if open}
      <div {...props} data-slot="collapsible-content" class={cn('collapsible-panel',className)} transition:slide={{duration:reducedMotion.current?0:180,easing:cubicOut}}>
        {@render children?.()}
      </div>
    {/if}
  {/snippet}
</CollapsiblePrimitive.Content>
