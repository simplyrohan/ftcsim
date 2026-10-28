<script lang="ts">
  import '../app.css';
  import Station from '$lib/components/Station.svelte';
  let { children } = $props();
</script>
<Station />
{@render children()}
