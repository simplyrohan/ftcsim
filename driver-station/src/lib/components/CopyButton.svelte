<script lang="ts">
  import { onDestroy } from 'svelte';
  import { Copy, Check } from '@lucide/svelte';
  import TooltipButton from './TooltipButton.svelte';
  let { value, label='Copy', disabled=false }: {value:string;label?:string;disabled?:boolean}=$props();
  let feedback=$state(''),timer:ReturnType<typeof setTimeout>|undefined,disposed=false;
  onDestroy(()=>{disposed=true;clearTimeout(timer);});
  async function copy(){
    try{await navigator.clipboard.writeText(value);if(!disposed)feedback='Copied';}
    catch{if(!disposed)feedback='Unable to copy. Check clipboard access.';}
    if(disposed)return;
    clearTimeout(timer);timer=setTimeout(()=>feedback='',1500);
  }
</script>
<TooltipButton label={feedback||label} aria-label={label} variant="ghost" size="icon" {disabled} onclick={copy}>{#if feedback==='Copied'}<Check size={14}/>{:else}<Copy size={14}/>{/if}</TooltipButton>
<span class="sr-only" role="status">{feedback}</span>
