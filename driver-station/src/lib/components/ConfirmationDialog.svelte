<script lang="ts">
  import { AlertTriangle } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import * as Dialog from '$lib/components/ui/dialog';
  import type { Confirmation, ConfirmationRequest } from '$lib/model/confirmation.svelte';
  let {confirmation}:{confirmation:Confirmation}=$props();
  let cancel=$state.raw<HTMLButtonElement|null>(null);
  const pending=$derived(confirmation.pending);
  let previous=$state.raw<ConfirmationRequest|null>(null);
  $effect(()=>{if(pending)previous=pending;});
  const request=$derived(pending??previous);
  const allowed=$derived(request?.allowed?.()!==false);
  function restoreFocus(event:Event){
    event.preventDefault();
    const origin=confirmation.origin;confirmation.origin=null;
    if(origin?.isConnected&&!origin.matches(':disabled'))origin.focus({preventScroll:true});
    else document.querySelector<HTMLElement>('.settings-nav [data-state=active], .start-position-trigger, .settings-link')?.focus({preventScroll:true});
  }
</script>
<Dialog.Root open={!!pending} onOpenChange={open=>{if(!open)confirmation.cancel();}} onOpenChangeComplete={open=>{if(!open&&!confirmation.pending)previous=null;}}>
  <Dialog.Content class="confirmation-dialog" showCloseButton={false} onOpenAutoFocus={event=>{event.preventDefault();cancel?.focus();}} onCloseAutoFocus={restoreFocus}>
    <div class="confirmation-heading"><AlertTriangle size={20} strokeWidth={1.5}/><Dialog.Header><Dialog.Title>{request?.title??'Confirm action'}</Dialog.Title><Dialog.Description>{request?.description??''}</Dialog.Description></Dialog.Header></div>
    {#if request?.details?.length}<ul class="confirmation-details">{#each request.details as detail}<li>{detail}</li>{/each}</ul>{/if}
    {#if pending&&!allowed}<p class="confirmation-unavailable" role="status">The configuration or connection changed. Cancel and try again.</p>{/if}
    <Dialog.Footer><Button bind:ref={cancel} variant="outline" onclick={()=>confirmation.cancel()}>Cancel</Button><Button variant="outline" class={request?.destructive===false?'':'confirmation-destructive'} disabled={!pending||!allowed} onclick={()=>confirmation.accept()}>{request?.action??'Continue'}</Button></Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
