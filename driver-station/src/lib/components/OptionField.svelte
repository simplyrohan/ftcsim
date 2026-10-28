<script lang="ts">
  import { Input } from '$lib/components/ui/input';
  import { choiceLabel, choiceValue } from '$lib/model/configuration';
  import type { Option } from '$lib/model/types';
  let { option, value = $bindable(), disabled = false, onchange = () => {} }: {option:Option; value:any; disabled?:boolean; onchange?:()=>void} = $props();
</script>
<label class="field">
  <span>{option.label}</span>
  {#if option.choices}
    <select class="control" {disabled} value={value ?? ''} onchange={(event)=>{value = option.type === 'number' ? Number(event.currentTarget.value) : event.currentTarget.value; onchange();}}>
      {#each option.choices as choice}<option value={choiceValue(choice)}>{choiceLabel(choice)}</option>{/each}
    </select>
  {:else if option.type === 'number'}
    <Input type="number" step="any" min={option.min} max={option.max} required {disabled} value={value ?? ''} oninput={(event)=>{value=event.currentTarget.value === '' ? null : Number(event.currentTarget.value);onchange();}} />
  {:else}
    <Input type="text" required {disabled} value={value ?? ''} oninput={(event)=>{value=event.currentTarget.value;onchange();}} />
  {/if}
</label>
