<script lang="ts">
  import { Terminal, Copy, Check } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  let { data, compact=false }: {data:Record<string,unknown>;compact?:boolean} = $props();
  let copied = $state(false);
  // SDK-rendered telemetry lines use a NUL-prefixed internal ordering key.
  const rows=$derived(Object.entries(data).map(([key,value])=>({caption:key.startsWith('\0')?'':key,value:typeof value==='object'?JSON.stringify(value):String(value)})));
  async function copy() { try { await navigator.clipboard.writeText(rows.map(row=>`${row.caption?`${row.caption}: `:''}${row.value}`).join('\n'));copied=true;setTimeout(()=>copied=false,1500); }catch{/* Clipboard may be unavailable in an embedded browser. */} }
</script>
<section class="panel telemetry-panel" class:compact>
  <div class="panel-heading"><div class="title-with-icon"><Terminal size={15}/><h3>Telemetry</h3><span class="pill subtle">{Object.keys(data).length} entries</span></div><Button variant="ghost" size="icon" aria-label="Copy telemetry" onclick={copy}>{#if copied}<Check size={14}/>{:else}<Copy size={14}/>{/if}</Button></div>
  <div class="telemetry-body">{#each rows as row}<div class="telemetry-line" class:rendered-line={!row.caption}>{#if row.caption}<span>{row.caption}</span>{/if}<strong>{row.value}</strong></div>{:else}<div class="empty-telemetry"><span class="terminal-prompt">›</span><span>Waiting for telemetry<span class="blink">_</span><small>Output from your OpMode appears here.</small></span></div>{/each}</div>
</section>
