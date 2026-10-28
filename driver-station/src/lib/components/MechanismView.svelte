<script lang="ts">
  import type { MechanismState } from '$lib/model/types';
  import { mechanismWidgets } from '$lib/model/mechanism-widgets';
  let { mechanism }: {mechanism:MechanismState} = $props();
  const Widget = $derived(mechanismWidgets.get(mechanism.type));
</script>
{#if Widget}<Widget {mechanism}/>{:else}<div class="empty-state"><h3>{mechanism.name}</h3><pre>{JSON.stringify(mechanism.state,null,2)}</pre></div>{/if}
