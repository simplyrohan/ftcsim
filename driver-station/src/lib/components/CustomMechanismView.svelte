<script lang="ts">
  import type { MechanismState } from '$lib/model/types';
  import { format } from '$lib/utils';
  let { mechanism }: {mechanism:MechanismState}=$props();
</script>
<div class="custom-mechanism-readout"><strong>{format(mechanism.state.displacement,1)}<small>{mechanism.state.motion==='translation'?'mm':'°'}</small></strong><span>{String(mechanism.state.axis??'Z').toUpperCase()} · {mechanism.state.motion}</span><p>{mechanism.state.bound?`${mechanism.drivers.actuator} · input ${format(mechanism.state.input_position,3)}`:'Static model · no actuator bound'}</p></div>
