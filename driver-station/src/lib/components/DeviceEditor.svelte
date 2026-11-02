<script lang="ts">
  import { Trash2, Plus, CornerDownRight, Pencil, Check, Cpu, RotateCw, Gauge, Compass } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import * as Collapsible from '$lib/components/ui/collapsible';
  import OptionField from './OptionField.svelte';
  import SelectField from './SelectField.svelte';
  import DeviceEditor from './DeviceEditor.svelte';
  import { optionValue } from '$lib/model/configuration';
  import type { Device } from '$lib/model/types';
  import type { HardwareConfiguration } from '$lib/model/hardware.svelte';
  let { device=$bindable(), hardware, parent, expanded=$bindable(false) }: {device:Device;hardware:HardwareConfiguration;parent?:Device;expanded?:boolean} = $props();
  const Icon = $derived(device.type==='motor'||device.type==='servo'?RotateCw:device.type==='odometry'?Gauge:device.type==='pinpoint'?Compass:Cpu);
  const schema = $derived(hardware.catalog.find(item=>item.type===device.type));
  const preset = $derived(schema?.presets?.find(item=>Object.entries(item.options).every(([key,value])=>{const actual=optionValue(device.options,schema.options.find(option=>option.name===key)!);return typeof actual==='number'&&Math.abs(actual-Number(value))<1e-6;}))?.id ?? '');
</script>
<Collapsible.Root bind:open={expanded} class={`editor-card${parent?' nested':''}`}>
  <div class="configuration-row">
    <span class="configuration-icon"><Icon size={17} strokeWidth={1.5}/></span>
    <div class="configuration-identity"><h3>{device.name||'Unnamed driver'}</h3><p>{schema?.label??device.type}{#if device.children?.length}<span class="summary-divider">·</span>{device.children.length} encoders{/if}</p></div>
    <span class="configuration-meta">{parent?`${parent.name} / ${String(device.port).toUpperCase()}`:`Hub ${device.module??1} · ${schema?.connection==='i2c'?'I²C':schema?.connection??'port'} ${device.port}`}</span>
    <div class="configuration-actions">
      <Collapsible.Trigger>{#snippet child({props})}<Button {...props} variant="ghost" size="sm" aria-label={`${expanded?'Finish editing':'Edit'} driver ${device.name}`}>{#if expanded}<Check size={13}/>Done{:else}<Pencil size={13}/>Edit{/if}</Button>{/snippet}</Collapsible.Trigger>
      <Button variant="ghost" size="icon-sm" title="Remove driver" aria-label={`Remove ${device.name}`} disabled={hardware.busy} onclick={()=>hardware.remove(device,parent)}><Trash2 size={14}/></Button>
    </div>
  </div>
  <Collapsible.Content>
    <div class="editor-card-body">
      <div class="form-grid identity-grid">
        <label class="field"><span>Name</span><Input value={device.name} oninput={event=>{device.name=event.currentTarget.value;hardware.save();}} required disabled={hardware.busy}/></label>
        {#if parent}<div class="field"><span>Connection</span><div class="inline-note"><CornerDownRight size={14}/>{parent.name} / {String(device.port).toUpperCase()}</div></div>
        {:else}
          <label class="field"><span>Hub address</span><Input type="number" min="1" max="254" value={device.module} oninput={event=>{device.module=event.currentTarget.value===''?undefined:Number(event.currentTarget.value);hardware.save();}} required disabled={hardware.busy}/></label>
          <label class="field"><span>{schema?.connection==='i2c'?'I²C':schema?.connection} port</span><SelectField aria-label={`${device.name} port`} items={Array.from({length:schema?.ports??4},(_,i)=>({value:String(i),label:String(i)}))} disabled={hardware.busy} value={String(device.port)} onValueChange={next=>{device.port=Number(next);hardware.save();}}/></label>
        {/if}
      </div>
      {#if schema}
        {#if schema.presets?.length}
          <label class="field preset-field"><span>Motor preset</span><SelectField aria-label={`${device.name} motor preset`} items={[{value:'',label:'Custom motor'},...schema.presets.map(item=>({value:item.id,label:item.label}))]} value={preset} disabled={hardware.busy} onValueChange={next=>{const selected=schema.presets?.find(item=>item.id===next);if(selected){device.options={...device.options,...selected.options};hardware.save();}}}/></label>
        {/if}
        <div class="form-grid">
          {#each schema.options as option}
            <OptionField {option} disabled={hardware.busy} onchange={()=>hardware.save()} bind:value={() => optionValue(device.options,option), value => { (device.options??={})[option.name]=value; }} />
          {/each}
        </div>
        {#if schema.child_ports.length}
          <div class="child-heading"><span class="eyebrow">Connected encoders</span><span class="muted">{device.children?.length ?? 0} / {schema.child_ports.length}</span></div>
          {#each device.children ?? [] as child (child)}<DeviceEditor bind:device={device.children![device.children!.indexOf(child)]} {hardware} parent={device}/>{/each}
          {#each schema.child_ports.filter(port=>!device.children?.some(child=>child.port===port)) as port}
            <Button variant="outline" size="sm" disabled={hardware.busy} onclick={()=>{const child=hardware.catalog.find(item=>item.connection===schema.child_connections[port]);if(child)hardware.add(child.type,device,port);}}><Plus size={13}/>Add {port.toUpperCase()} encoder</Button>
          {/each}
        {/if}
      {/if}
    </div>
  </Collapsible.Content>
</Collapsible.Root>
