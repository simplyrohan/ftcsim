<script lang="ts">
  import { Terminal, Copy, Check } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  let { data, compact=false }: {data:Record<string,unknown>;compact?:boolean} = $props();
  let copied = $state(false);
  async function copy() { try { await navigator.clipboard.writeText(Object.entries(data).map(([key,value])=>`${key}: ${value}`).join('\n'));copied=true;setTimeout(()=>copied=false,1500); }catch{/* Clipboard may be unavailable in an embedded browser. */} }
</script>
<section class="panel telemetry-panel" class:compact>
  <div class="panel-heading"><div class="title-with-icon"><Terminal size={15}/><h3>Telemetry</h3><span class="pill subtle">{Object.keys(data).length} entries</span></div><Button variant="ghost" size="icon" aria-label="Copy telemetry" onclick={copy}>{#if copied}<Check size={14}/>{:else}<Copy size={14}/>{/if}</Button></div>
  <div class="telemetry-body">{#each Object.entries(data) as [key,value]}<div class="telemetry-line"><span>{key}</span><strong>{typeof value==='object'?JSON.stringify(value):String(value)}</strong></div>{:else}<div class="empty-telemetry"><span class="terminal-prompt">›</span><span>Waiting for telemetry<span class="blink">_</span><small>Output from your OpMode appears here.</small></span></div>{/each}</div>
</section>
