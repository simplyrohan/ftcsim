<script lang="ts">
  import * as Select from '$lib/components/ui/select';
  import type { Select as SelectPrimitive } from 'bits-ui';
  let { items, value=$bindable(''), onValueChange=()=>{}, disabled=false, required=false, placeholder='Select…', class:className='', ...props }: {
    items:{value:string;label:string;disabled?:boolean}[];
    value?:string;onValueChange?:(value:string)=>void;disabled?:boolean;required?:boolean;placeholder?:string;
  } & Omit<SelectPrimitive.TriggerProps,'value'|'disabled'|'children'|'child'> = $props();
  // Encode every value so optional bindings can offer a real, selectable empty value.
  const choices=$derived(items.map(item=>({...item,value:JSON.stringify(item.value)})));
</script>
<Select.Root type="single" items={choices} value={JSON.stringify(value)} {disabled} {required} allowDeselect={false} onValueChange={next=>{if(!next)return;value=JSON.parse(next);onValueChange(value);}}>
  <Select.Trigger {...props} class={className}><Select.Value {placeholder}/></Select.Trigger>
  <Select.Content align="start" collisionPadding={12}>
    <Select.Group>{#each choices as item (item.value)}<Select.Item value={item.value} label={item.label} disabled={item.disabled}>{item.label}</Select.Item>{/each}</Select.Group>
  </Select.Content>
</Select.Root>
