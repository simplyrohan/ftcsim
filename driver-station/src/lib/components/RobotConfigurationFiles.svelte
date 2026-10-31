<script lang="ts">
  import { Upload, Download, FileJson, FileArchive } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import type { Station } from '$lib/model/station.svelte';
  let { station }: {station:Station} = $props();
  const file = $derived(station.robotConfiguration);
  let input:HTMLInputElement;
  let pasteOpen = $state(false), pasted = $state('');
  async function loadPasted() { try { if(await file.importText(pasted,'pasted JSON'))pasteOpen=false; } catch(error) { file.message=`File not loaded: ${error instanceof Error?error.message:error}`; } }
</script>
<div class="robot-file-bar"><div class="robot-file-label"><FileArchive size={18} strokeWidth={1.5}/><div><strong>Robot file</strong><p>Hardware, mechanisms &amp; models in one .fs file.</p></div></div><div class="toolbar import-toolbar">
  <label class="file-button"><Upload size={14}/><span>Load robot</span><input bind:this={input} type="file" accept=".fs,.zip,.json,application/zip,application/json" aria-label="Load robot configuration file" title="Load an .fs robot archive" disabled={file.busy} onclick={()=>input.value=''} onchange={()=>{const selected=input.files?.[0];if(selected)void file.importFile(selected);}}/></label>
  <Button variant="outline" size="sm" disabled={file.busy || !!file.error} onclick={()=>file.exportFile()}><Download size={14}/>Save robot</Button>
  <Button variant="ghost" size="sm" aria-expanded={pasteOpen} onclick={()=>pasteOpen=!pasteOpen}><FileJson size={14}/>Paste JSON</Button>
</div></div>
{#if pasteOpen}<div class="paste-panel"><label class="field"><span>Robot configuration JSON</span><textarea class="control code-input" bind:value={pasted} spellcheck="false" placeholder="Paste a robot configuration…"></textarea></label><Button variant="outline" size="sm" onclick={loadPasted} disabled={!pasted.trim() || file.busy}>Load JSON</Button></div>{/if}
{#if file.message}<p class="fine-print file-message" role="status">{file.message}</p>{/if}
