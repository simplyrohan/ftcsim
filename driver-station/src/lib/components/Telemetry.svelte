<script lang="ts">
  import { Terminal } from '@lucide/svelte';
  import CopyButton from './CopyButton.svelte';
  let { data, compact=false }: {data:Record<string,unknown>;compact?:boolean} = $props();
  // SDK-rendered telemetry lines use a NUL-prefixed internal ordering key.
  const rows=$derived(Object.entries(data).map(([key,value])=>({caption:key.startsWith('\0')?'':key,value:typeof value==='object'?JSON.stringify(value):String(value)})));
</script>
<section class="panel telemetry-panel" class:compact>
  <div class="panel-heading"><div class="title-with-icon"><Terminal size={15}/><h3>Telemetry</h3><span class="pill subtle">{Object.keys(data).length} entries</span></div><CopyButton label="Copy telemetry" value={rows.map(row=>`${row.caption?`${row.caption}: `:''}${row.value}`).join('\n')} disabled={!rows.length}/></div>
  <div class="telemetry-body">{#each rows as row}<div class="telemetry-line" class:rendered-line={!row.caption}>{#if row.caption}<span>{row.caption}</span>{/if}<strong>{row.value}</strong></div>{:else}<div class="empty-telemetry"><span class="terminal-prompt">›</span><span>Waiting for telemetry<span class="blink">_</span></span></div>{/each}</div>
</section>
