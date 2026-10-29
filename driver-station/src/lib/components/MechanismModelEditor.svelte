<script lang="ts">
  import { onDestroy } from 'svelte';
  import { Upload, Trash2, LoaderCircle, Box } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { readBinaryFile, saveModel, MAX_MODEL_BYTES } from '$lib/model/model-assets';
  import type { Mechanism } from '$lib/model/types';
  let { definition, definitions, disabled=false, onchange }: {definition:Mechanism;definitions:Mechanism[];disabled?:boolean;onchange:()=>void}=$props();
  let uploading=$state(false),message=$state(''),input:HTMLInputElement,disposed=false;
  onDestroy(()=>disposed=true);
  function update(key:'position'|'rotation',index:number,value:string) {
    const visual=definition.visual??={};const values=[...(visual[key]??[0,0,0])];values[index]=value===''?NaN:Number(value);visual[key]=values;onchange();
  }
  function possibleParent(candidate:string) {
    const seen=new Set([definition.name]);let name:string|undefined=candidate;
    while(name){if(seen.has(name))return false;seen.add(name);name=definitions.find(item=>item.name===name)?.visual?.parent;}
    return true;
  }
  async function upload(file:File) {
    if(uploading || disabled)return;uploading=true;message='';
    try {
      if(file.size>MAX_MODEL_BYTES)throw Error('Choose a GLB smaller than 20 MB.');
      const data=await readBinaryFile(file);
      const [{parseModel},{disposeObject}]=await Promise.all([import('$lib/scene/models'),import('$lib/scene/mecanum')]);
      const object=await parseModel(data);disposeObject(object);
      if(disposed)return;
      const id=crypto.randomUUID();await saveModel(id,data);
      if(disposed)return;
      (definition.visual??={}).model={id,name:file.name};onchange();message='Model ready. Its original pivot and materials are preserved.';
    }catch(error){if(!disposed)message=`Model not loaded: ${error instanceof Error?error.message:error}`;}
    finally{if(!disposed)uploading=false;}
  }
</script>
<section class="mechanism-section">
  <div class="mechanism-section-title"><span class="step-number">01</span><div><h3>Model</h3><p>Upload a GLB with its origin at the intended pivot.</p></div></div>
  <div class="model-upload">
    <Box size={24} strokeWidth={1}/><div class="model-file-name"><strong>{definition.visual?.model?.name ?? (definition.type==='mecanum'?'Built-in mecanum model':'Origin marker')}</strong><span>{definition.visual?.model?'Saved in this browser · included in robot exports':'Your GLB replaces this visual only.'}</span></div>
    <label class="file-button">{#if uploading}<LoaderCircle size={13} class="animate-spin"/>{:else}<Upload size={13}/>{/if}<span>{uploading?'Loading…':definition.visual?.model?'Replace':'Upload GLB'}</span><input bind:this={input} type="file" accept=".glb,model/gltf-binary" aria-label={`Upload GLB for ${definition.name}`} disabled={disabled||uploading} onclick={()=>input.value=''} onchange={()=>{const file=input.files?.[0];if(file)void upload(file);}}/></label>
    {#if definition.visual?.model}<Button variant="ghost" type="button" size="icon" aria-label="Remove uploaded model" disabled={disabled||uploading} onclick={()=>{delete definition.visual!.model;onchange();message='';}}><Trash2 size={13}/></Button>{/if}
  </div>
  {#if message}<p class="fine-print" role="status">{message}</p>{/if}
  <label class="field"><span>Model scale</span><div class="scale-input"><Input type="number" min="0.000001" step="any" value={definition.visual?.scale??1} {disabled} oninput={event=>{(definition.visual??={}).scale=event.currentTarget.value===''?NaN:Number(event.currentTarget.value);onchange();}}/><select class="control" aria-label="Model unit preset" {disabled} value={[1,.01,.001].includes(definition.visual?.scale??1)?String(definition.visual?.scale??1):'custom'} onchange={event=>{(definition.visual??={}).scale=Number(event.currentTarget.value);onchange();}}><option value="1">Meters · 1×</option><option value="0.01">Centimeters · 0.01×</option><option value="0.001">Millimeters · 0.001×</option><option value="custom" disabled>Custom scale</option></select></div></label>
</section>
<section class="mechanism-section">
  <div class="mechanism-section-title"><span class="step-number">02</span><div><h3>Origin &amp; placement</h3><p>Offsets are relative to the selected mechanism’s moving origin.</p></div></div>
  <label class="field"><span>Attach to origin</span><select class="control" value={definition.visual?.parent??''} {disabled} onchange={event=>{(definition.visual??={}).parent=event.currentTarget.value;onchange();}}><option value="">World origin · fixed</option>{#each definitions.filter(item=>item!==definition) as parent}<option value={parent.name} disabled={!possibleParent(parent.name)}>{parent.name} · {parent.type==='mecanum'?'robot origin':'moving origin'}</option>{/each}</select></label>
  <div class="vector-field"><span class="eyebrow">Starting position · mm</span><div class="vector-inputs">{#each ['X · forward','Y · left','Z · up'] as label,index}<label class="field"><span>{label}</span><Input type="number" step="any" value={definition.visual?.position?.[index]??0} {disabled} oninput={event=>update('position',index,event.currentTarget.value)}/></label>{/each}</div></div>
  <div class="vector-field"><span class="eyebrow">Starting orientation · degrees</span><div class="vector-inputs">{#each ['Roll · X','Pitch · Y','Yaw · Z'] as label,index}<label class="field"><span>{label}</span><Input type="number" step="any" value={definition.visual?.rotation?.[index]??0} {disabled} oninput={event=>update('rotation',index,event.currentTarget.value)}/></label>{/each}</div></div>
  <p class="fine-print">X is forward, Y is left, Z is up. Rotation and translation happen at the uploaded model’s origin, after this starting pose. Model scale does not scale the movement distance.</p>
</section>
