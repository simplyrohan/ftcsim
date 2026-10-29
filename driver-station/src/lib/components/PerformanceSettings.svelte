<script lang="ts">
  import { milliseconds } from '$lib/model/diagnostics.svelte';
  import type { Station } from '$lib/model/station.svelte';
  let {station}:{station:Station}=$props();
  const debug=$derived(station.diagnostics);
</script>
<div class="settings-heading"><div><h2>Performance</h2><p>Round-trip latency and browser rendering diagnostics. Rendering updates once per second; ping probes run every two seconds.</p></div></div>
<div class="performance-grid">
  {#each [{name:'SDK ping',probe:debug.sdk},{name:'Simulator ping',probe:debug.simulator}] as {name,probe}}<section class="performance-card"><h3>{name}</h3><strong>{milliseconds(probe.ms)}</strong><p>{probe.transport}</p><dl class="data-rows"><div><dt>Smoothed average</dt><dd>{milliseconds(probe.average)}</dd></div><div><dt>Timeouts</dt><dd>{probe.timeouts}</dd></div></dl></section>{/each}
  <section class="performance-card"><h3>UI scheduling delay</h3><strong>{milliseconds(debug.uiLag)}</strong><p>Timer delay above its expected interval</p><dl class="data-rows"><div><dt>Session maximum</dt><dd>{milliseconds(debug.maxUiLag)}</dd></div></dl></section>
  <section class="performance-card"><h3>Last simulation update</h3><strong>{milliseconds(station.mechanisms.applyMs)}</strong><p>Request, server response, and browser confirmation</p><dl class="data-rows"><div><dt>Python configuration time</dt><dd>{milliseconds(station.mechanisms.serverMs)}</dd></div></dl></section>
</div>
<p class="fine-print">SDK WebSocket timing uses an acknowledgment on an existing gamepad frame, including the SDK command queue. Observer tabs use its existing HTTP endpoint. Simulator timing uses a small WebSocket echo. Neither requires SDK changes.</p>
<div class="section-rule"><span class="eyebrow">3D viewports</span></div>
{#each Object.values(debug.views) as view}<section class="performance-card viewport-metrics"><div class="panel-heading"><h3>{view.label}</h3><span class="pill">{view.active?'Rendering':'Paused'}</span></div><dl class="data-rows"><div><dt>Frames per second</dt><dd>{view.fps.toFixed(1)}</dd></div><div><dt>CPU render work / frame</dt><dd>{milliseconds(view.renderMs)}</dd></div><div><dt>Draw calls / triangles</dt><dd>{view.drawCalls} / {view.triangles.toLocaleString()}</dd></div><div><dt>Geometry / textures</dt><dd>{view.geometries} / {view.textures}</dd></div><div><dt>Model builds</dt><dd>{view.modelBuilds}</dd></div></dl></section>{:else}<p class="fine-print">Open Overview or the mechanism preview to collect rendering metrics.</p>{/each}
<p class="fine-print">CPU render time excludes GPU execution. Covered, hidden, and offscreen viewports pause rendering. Preview rendering is capped at 30 FPS and uses one display pixel per CSS pixel.</p>
