<script lang="ts">
  import { CircleHelp } from '@lucide/svelte';
  import * as Tooltip from '$lib/components/ui/tooltip';
  let { text, label='Help' }: {text:string;label?:string}=$props();
  let open=$state(false);
</script>
<Tooltip.Root bind:open disableCloseOnTriggerClick>
  <Tooltip.Trigger type="button" class="help-trigger" aria-label={label} onclick={()=>open=true}><CircleHelp size={14}/></Tooltip.Trigger>
  <Tooltip.Content sideOffset={8} class="help-content">{text}</Tooltip.Content>
</Tooltip.Root>
