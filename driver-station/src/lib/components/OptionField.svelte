<script lang="ts">
  import { Input } from '$lib/components/ui/input';
  import SelectField from './SelectField.svelte';
  import { choiceLabel, choiceValue } from '$lib/model/configuration';
  import type { Option } from '$lib/model/types';
  let { option, value = $bindable(), disabled = false, onchange = () => {} }: {option:Option; value:any; disabled?:boolean; onchange?:()=>void} = $props();
</script>
<label class="field">
  <span>{option.label}</span>
  {#if option.choices}
    <SelectField aria-label={option.label} items={option.choices.map(choice=>({value:String(choiceValue(choice)),label:choiceLabel(choice)}))} {disabled} value={String(value??'')} onValueChange={next=>{value=option.type==='number'?Number(next):next;onchange();}}/>
  {:else if option.type === 'number'}
    <Input type="number" step="any" min={option.min} max={option.max} required {disabled} value={value ?? ''} oninput={(event)=>{value=event.currentTarget.value === '' ? null : Number(event.currentTarget.value);onchange();}} />
  {:else}
    <Input type="text" required {disabled} value={value ?? ''} oninput={(event)=>{value=event.currentTarget.value;onchange();}} />
  {/if}
</label>
