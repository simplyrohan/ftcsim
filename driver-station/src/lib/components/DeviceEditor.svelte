<script lang="ts">
  import { Trash2, Plus, CornerDownRight, ChevronDown, Cpu } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import OptionField from './OptionField.svelte';
  import DeviceEditor from './DeviceEditor.svelte';
  import { optionValue } from '$lib/model/configuration';
  import type { Device } from '$lib/model/types';
  import type { HardwareConfiguration } from '$lib/model/hardware.svelte';
  let { device, hardware, parent }: {device:Device;hardware:HardwareConfiguration;parent?:Device} = $props();
  let expanded = $state(true);
  const schema = $derived(hardware.catalog.find(item=>item.type===device.type));
  const preset = $derived(schema?.presets?.find(item=>Object.entries(item.options).every(([key,value])=>{const actual=optionValue(device.options,schema.options.find(option=>option.name===key)!);return typeof actual==='number'&&Math.abs(actual-Number(value))<1e-6;}))?.id ?? '');
</script>
<article class="editor-card" class:nested={!!parent}>
  <div class="editor-card-header">
    <button class="disclosure" type="button" onclick={()=>expanded=!expanded} aria-expanded={expanded} aria-label={`Configure ${device.name}`}><ChevronDown size={14} class={expanded?'':'-rotate-90'}/><Cpu size={15}/><strong>{device.name || 'Unnamed driver'}</strong><span class="muted">{schema?.label ?? device.type}</span></button>
    <Button variant="ghost" size="icon" title="Remove driver" aria-label={`Remove ${device.name}`} disabled={hardware.busy || hardware.importing} onclick={()=>hardware.remove(device,parent)}><Trash2 size={14}/></Button>
  </div>
  {#if expanded}
    <div class="editor-card-body">
      <div class="form-grid identity-grid">
        <label class="field"><span>Name</span><Input value={device.name} oninput={event=>{device.name=event.currentTarget.value;hardware.save();}} required disabled={hardware.busy}/></label>
        {#if parent}<div class="field"><span>Connection</span><div class="inline-note"><CornerDownRight size={14}/>{parent.name} / {String(device.port).toUpperCase()}</div></div>
        {:else}
          <label class="field"><span>Hub address</span><Input type="number" min="1" max="254" value={device.module} oninput={event=>{device.module=event.currentTarget.value===''?undefined:Number(event.currentTarget.value);hardware.save();}} required disabled={hardware.busy}/></label>
          <label class="field"><span>{schema?.connection==='i2c'?'I²C':schema?.connection} port</span><select class="control" disabled={hardware.busy} value={device.port} onchange={event=>{device.port=Number(event.currentTarget.value);hardware.save();}}>{#each Array.from({length:schema?.ports??4},(_,i)=>i) as port}<option value={port}>{port}</option>{/each}</select></label>
        {/if}
      </div>
      {#if schema}
        {#if schema.presets?.length}
          <label class="field preset-field"><span>Motor preset <small>goBILDA Yellow Jacket · 12 V</small></span><select class="control" value={preset} disabled={hardware.busy} onchange={event=>{const selected=schema.presets?.find(item=>item.id===event.currentTarget.value);if(selected){device.options={...device.options,...selected.options};hardware.save();}}}><option value="">Custom motor</option>{#each schema.presets as item}<option value={item.id}>{item.label}</option>{/each}</select></label>
        {/if}
        <div class="form-grid">
          {#each schema.options as option}
            <OptionField {option} disabled={hardware.busy} onchange={()=>hardware.save()} bind:value={() => optionValue(device.options,option), value => { (device.options??={})[option.name]=value; }} />
          {/each}
        </div>
        {#if schema.child_ports.length}
          <div class="child-heading"><span class="eyebrow">Connected encoders</span><span class="muted">{device.children?.length ?? 0} / {schema.child_ports.length}</span></div>
          {#each device.children ?? [] as child}<DeviceEditor device={child} {hardware} parent={device}/>{/each}
          {#each schema.child_ports.filter(port=>!device.children?.some(child=>child.port===port)) as port}
            <Button variant="outline" size="sm" disabled={hardware.busy} onclick={()=>{const child=hardware.catalog.find(item=>item.connection===schema.child_connections[port]);if(child)hardware.add(child.type,device,port);}}><Plus size={13}/>Add {port.toUpperCase()} encoder</Button>
          {/each}
        {/if}
      {/if}
    </div>
  {/if}
</article>
