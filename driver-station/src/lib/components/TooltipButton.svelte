<script lang="ts">
  import type { Snippet } from 'svelte';
  import * as Tooltip from '$lib/components/ui/tooltip';
  import { Button, type ButtonVariant, type ButtonSize } from '$lib/components/ui/button';
  import type { Tooltip as TooltipPrimitive } from 'bits-ui';
  let { label, hint, children, variant='ghost', size='icon', class:className, ...rest }: Omit<TooltipPrimitive.TriggerProps,'children'|'child'> & {label:string;hint?:string;children:Snippet;variant?:ButtonVariant;size?:ButtonSize}=$props();
</script>
<Tooltip.Root>
  <Tooltip.Trigger {...rest} aria-label={rest['aria-label']??label}>{#snippet child({props})}<Button {...props} data-slot="button" {variant} {size} class={className}>{@render children()}</Button>{/snippet}</Tooltip.Trigger>
  <Tooltip.Content sideOffset={8}>{hint??label}</Tooltip.Content>
</Tooltip.Root>
