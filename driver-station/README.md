# Driver Station

A standalone Svelte 5 / SvelteKit application using shadcn-svelte, Bits UI,
Tailwind 4, local Geist fonts, and Lucide icons. The Python server serves its
static production bundle; end users do not need Node.js.

## Development

Install Node.js 22.12+ and npm. Start the Python simulator in development mode:

```sh
ftcsim --dev
```

This keeps all simulator HTTP/WebSocket APIs running on port 9015 and disables
the Python server's `/ds` routes and root redirect. No frontend bundle is needed.
Use `--port` to change the API port. Plain `ftcsim` still serves the bundled UI.

Start the robot SDK with `./gradlew runSimulator` in your robot project in another
terminal. Then, from this repository in a third terminal:

```sh
cd driver-station
npm ci
npm run dev
```

Open http://127.0.0.1:5173/ds/. Vite hot reloads the app and proxies `/sim` to
`http://127.0.0.1:9015` and `/sdk` to `ws://127.0.0.1:1115/ds`. The SDK connection
still belongs to the browser; only the development server proxies it to satisfy
same-origin checks. Production connects directly to the SDK.

For different ports, copy `.env.example` to `.env.local` and change
`FTCSIM_BACKEND` / `FTCSIM_SDK`. Restart Vite after changing them. In development,
the SDK address in Connection settings must match `FTCSIM_SDK` to use that proxy.
Browser drafts are scoped to their origin and SDK address, so Vite and the
Python-served app have separate browser storage. Robot configuration files include both hardware and mechanisms and are portable.
The editors and apply actions remain separate. Loading validates the entire file,
including mechanism driver references, before changing either draft.

The bottom of the sidebar shows separate simulator-server and SDK connection
indicators. Click either to open Connection settings. The simulator indicator
tracks the physical-state WebSocket, independently of whether an SDK is attached.
Connected dots are pastel blue; offline dots are pastel red. A pulsing blue dot
means the SDK is connecting.

Use the **Gamepad 1 / Gamepad 2** toggle on the Gamepads page or the compact
overview card to choose the keyboard and virtual controller. Switching releases
held keys and clears virtual inputs so the previous controller returns to neutral.
Physical gamepads retain their own assignments and continue to be sampled.

Keyboard controls for the selected gamepad: WASD moves the left stick, IJKL moves the right
stick, Z/X/C/V presses A/B/X/Y, Q/E presses the left/right bumpers, R/T holds the
left/right triggers, and the arrow keys operate the D-pad.

```sh
npm run check       # TypeScript and Svelte diagnostics
npm run build       # standalone static output in build/
npm run preview     # inspect the static build; use Python for live SDK access
```

## 3D Overview

Overview fills the workspace below the breadcrumb bar with a transparent Three.js
scene. OpMode controls, telemetry, the selected gamepad, and drivebase readouts
float over the scene. Smaller screens expose Telemetry and Gamepad dock buttons.
The other sidebar pages and the settings dialog retain their existing workflows.

Drag to orbit, right-drag to pan, and scroll or pinch to zoom. Camera controls
switch between perspective/top views, follow the selected robot, and recenter.
The scene uses the mechanism's physical pose rather than the Pinpoint estimator.
Wheel animation uses measured wheel speed and the configured wheel diameter;
wheelbase and track width determine the model's dimensions. The generic chassis
is generated locally without downloading a model or environment textures.

`src/lib/scene/viewport.ts` owns the renderer, camera, controls, lighting, resize
observer, and render loop. Register a mechanism visual in `mechanismVisuals`;
`mecanum.ts` implements the current robot. FTC forward/left mm coordinates map
to Three.js +X/-Z meters, with +Y up. Three.js loads only for Overview or a mechanism preview. Leaving
the page disposes GPU resources while the root station retains its sockets;
hidden documents pause rendering. No physics or input logic runs in the viewer.

See the [Three.js renderer](https://threejs.org/docs/pages/WebGLRenderer) and
[OrbitControls](https://threejs.org/docs/pages/OrbitControls) documentation.

## Python distribution

From the repository root:

```sh
python3 scripts/build_driver_station.py
```

This runs `npm ci`, builds the app with `adapter-static`, and replaces
`src/ftcsim/web/` with the complete bundle. `ftcsim` serves it under `/ds`, including
client-side routes and content-hashed JS, CSS, and local font assets. HTML is
never cached; immutable assets can be cached safely. The Python wheel build
(including editable installations) runs this script and the SDK build. Source
distributions contain frontend sources and the lockfile, excluding generated
output and node_modules. Wheels contain the static bundle, without build tools.

## Structure

- `src/lib/model/station.svelte.ts`: controller lifecycle, telemetry, WebSocket
  ownership, heartbeat, pending requests, physical-state reconnects, and cleanup.
- `hardware.svelte.ts` / `mechanisms.svelte.ts`: metadata-driven configuration,
  validation, browser drafts, import/export, confirmation, and idle restoration.
- `configuration.ts`: shared topology, origin graph, and option validation.
- `robot-configuration.svelte.ts`: portable `.fs` ZIP archives containing `robot.json` and GLB files.
- `robot-archive.ts`: archive creation, bounded extraction, and path validation.
- `model-assets.ts`: IndexedDB storage and binary glTF validation.
- `src/lib/scene/models.ts`: uploaded models and nested mechanism transforms.
- `widgets.ts`: driver presenters. Register new driver kinds here; composite
  device cards recurse through existing children.
- `mechanism-widgets.ts`: mechanism kind → Svelte component registry. Mechanisms
  never enter SDK messages or TeamCode APIs.
- `src/lib/components/ui`: actual shadcn-svelte components generated with the CLI;
  theme overrides live in `src/app.css`.

The persistent root layout owns one station instance. Sidebar navigation never
recreates the SDK connection. The settings dialog pauses gamepad input and uses
Bits UI focus trapping, Escape dismissal, and keyboard-accessible tabs. Runtime sidebar views retain controller input. Blur, hidden pages, the settings
dialog, and STOP neutralize virtual/keyboard controls. The input enable switch
retains its value when settings open and close.
Reduced-motion preferences disable cosmetic transitions.

Performance diagnostics live in **Settings → Performance**. See [MECHANISMS.md](../MECHANISMS.md#updating-simulation-and-performance-diagnostics) for RTT measurement details and rendering behavior.
