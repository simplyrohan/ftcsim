<script lang="ts">
  import '../app.css';
  import Station from '$lib/components/Station.svelte';
  import * as Tooltip from '$lib/components/ui/tooltip';
  let { children } = $props();
</script>
<Tooltip.Provider delayDuration={0}>
  <Station />
  {@render children()}
</Tooltip.Provider>
