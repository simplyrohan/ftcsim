<script lang="ts">
  import { isDrivetrain } from '$lib/model/mechanism-types';
  import { onDestroy } from 'svelte';
  import { Upload, Trash2, LoaderCircle, Box } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import SelectField from './SelectField.svelte';
  import HelpTooltip from './HelpTooltip.svelte';
  import { readBinaryFile, saveModel, MAX_MODEL_BYTES } from '$lib/model/model-assets';
  import type { Confirmation } from '$lib/model/confirmation.svelte';
  import type { Mechanism } from '$lib/model/types';
  let { definition=$bindable(), definitions, confirmation, disabled=false, onchange }: {definition:Mechanism;definitions:Mechanism[];confirmation:Confirmation;disabled?:boolean;onchange:()=>void}=$props();
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
      if(file.size>MAX_MODEL_BYTES)throw Error('Choose a GLB no larger than 200 MB.');
      const data=await readBinaryFile(file);
      const [{parseModel},{disposeObject}]=await Promise.all([import('$lib/scene/models'),import('$lib/scene/drivetrain')]);
      const object=await parseModel(data);disposeObject(object);
      if(disposed)return;
      const previous=definition.visual?.model;
      const allowed=()=>!disposed&&!disabled&&definition.visual?.model===previous;
      if(previous&&!await confirmation.ask({title:'Replace mechanism model?',description:`Replace “${previous.name}” on “${definition.name}” with “${file.name}”.`,action:'Replace model',details:['The model assignment saves immediately. Position, orientation, and motion settings are kept.'],allowed}))return;
      if(!allowed())return;
      const id=crypto.randomUUID();await saveModel(id,data);
      if(disposed)return;
      (definition.visual??={}).model={id,name:file.name};onchange();message='Model ready. Its original pivot and materials are preserved.';
    }catch(error){if(!disposed)message=`Model not loaded: ${error instanceof Error?error.message:error}`;}
    finally{if(!disposed)uploading=false;}
  }
  async function removeModel(){
    const model=definition.visual?.model;
    const allowed=()=>!disposed&&!disabled&&!!model&&definition.visual?.model===model;
    if(!allowed())return;
    if(!await confirmation.ask({title:'Remove mechanism model?',description:`Remove “${model!.name}” from “${definition.name}”.`,action:'Remove model',details:[isDrivetrain(definition.type)?'The built-in drivebase visual will be used.':'The mechanism will show its origin marker.','Position, orientation, and motion settings are kept. The change saves immediately.'],allowed})||!allowed())return;
    delete definition.visual!.model;onchange();message='';
  }
</script>
<section class="mechanism-section">
  <div class="mechanism-section-title"><span class="step-number">01</span><h3>Model <HelpTooltip label="About mechanism models" text="Upload a GLB with its origin at the intended pivot. Models are saved in this browser and included in robot exports; they change the visual only."/></h3></div>
  <div class="model-upload">
    <Box size={24} strokeWidth={1}/><div class="model-file-name"><strong>{definition.visual?.model?.name ?? (isDrivetrain(definition.type)?'Built-in drivebase model':'Origin marker')}</strong></div>
    <label class="file-button">{#if uploading}<LoaderCircle size={13} class="animate-spin"/>{:else}<Upload size={13}/>{/if}<span>{uploading?'Loading…':definition.visual?.model?'Replace':'Upload GLB'}</span><input bind:this={input} type="file" accept=".glb,model/gltf-binary" aria-label={`Upload GLB for ${definition.name}`} disabled={disabled||uploading} onclick={()=>input.value=''} onchange={()=>{const file=input.files?.[0];if(file)void upload(file);}}/></label>
    {#if definition.visual?.model}<Button variant="ghost" type="button" size="icon" aria-label="Remove uploaded model" disabled={disabled||uploading} onclick={removeModel}><Trash2 size={13}/></Button>{/if}
  </div>
  {#if message}<p class="fine-print" role="status">{message}</p>{/if}
  <label class="field"><span>Model scale</span><div class="scale-input"><Input type="number" aria-label="Model scale" min="0.000001" step="any" value={definition.visual?.scale??1} {disabled} oninput={event=>{(definition.visual??={}).scale=event.currentTarget.value===''?NaN:Number(event.currentTarget.value);onchange();}}/><SelectField aria-label="Model unit preset" {disabled} value={[1,.01,.001].includes(definition.visual?.scale??1)?String(definition.visual?.scale??1):'custom'} items={[{value:'1',label:'Meters · 1×'},{value:'0.01',label:'Centimeters · 0.01×'},{value:'0.001',label:'Millimeters · 0.001×'},{value:'custom',label:'Custom scale',disabled:true}]} onValueChange={next=>{(definition.visual??={}).scale=Number(next);onchange();}}/></div></label>
</section>
<section class="mechanism-section">
  <div class="mechanism-section-title"><span class="step-number">02</span><h3>Origin &amp; placement <HelpTooltip label="About model placement" text="Offsets follow the selected mechanism’s moving origin. X is forward, Y is left, Z is up. Motion happens at the uploaded model’s origin after this starting pose. Model scale does not scale movement distance."/></h3></div>
  <label class="field"><span>Attach to origin</span><SelectField aria-label="Attach to origin" value={definition.visual?.parent??''} {disabled} items={[{value:'',label:'World origin · fixed'},...definitions.filter(item=>item!==definition).map(parent=>({value:parent.name,label:`${parent.name} · ${isDrivetrain(parent.type)?'robot origin':'moving origin'}`,disabled:!possibleParent(parent.name)}))]} onValueChange={next=>{(definition.visual??={}).parent=next;onchange();}}/></label>
  <div class="vector-field"><span class="eyebrow">Starting position · mm</span><div class="vector-inputs">{#each ['X · forward','Y · left','Z · up'] as label,index}<label class="field"><span>{label}</span><Input type="number" step="any" value={definition.visual?.position?.[index]??0} {disabled} oninput={event=>update('position',index,event.currentTarget.value)}/></label>{/each}</div></div>
  <div class="vector-field"><span class="eyebrow">Starting orientation · degrees</span><div class="vector-inputs">{#each ['Roll · X','Pitch · Y','Yaw · Z'] as label,index}<label class="field"><span>{label}</span><Input type="number" step="any" value={definition.visual?.rotation?.[index]??0} {disabled} oninput={event=>update('rotation',index,event.currentTarget.value)}/></label>{/each}</div></div>
</section>
