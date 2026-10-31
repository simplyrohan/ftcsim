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
The mechanism overlay uses a narrow column with stacked pose and sensor readouts.
On desktop it shares the telemetry/gamepad column width and bottom gutter; narrower
viewports lift it above the camera and overlay controls. Expanded feedback scrolls
inside the column. The other sidebar pages retain their existing workflows.
Settings is a full workspace page.

Drag to orbit, right-drag to pan, and scroll or pinch to zoom. Camera controls
switch between perspective/top views, follow the selected robot, and recenter.
The **Field** camera-toolbar toggle shows the bundled field GLB; its preference
is saved locally. The field is in meters with its mat surface at FTC Z = 0.
Its Draco decoder is bundled locally, so neither the model nor decoder needs a
CDN. Static geometry is batched by material to reduce draw calls.

Expand **Start position** beneath the OpMode controls to enter field X/Y (mm)
and counterclockwise heading (degrees). Enable **Place before INIT** to restore
that pose every time this OpMode initializes, or use **Place now** while stopped.
Named presets can be saved, loaded across OpModes, and deleted. Poses are saved
per OpMode and SDK endpoint in browser storage; presets are shared across that
endpoint's OpModes. These preferences are separate from the robot `.fs` file.
Placement changes the drivetrain's physical field pose only. It never writes
Pinpoint position/heading or resets encoders: TeamCode defines sensor origins.
The server rejects placement while drivetrain motors are moving. A placement
failure prevents INIT and is shown beside the controls.

The viewer uses a camera-mounted directional key and a weak ambient fill, with
ACES filmic tone mapping to keep highlights controlled and dark faces distinct.
A low-intensity, locally generated studio environment supplies subtle reflections
so metallic models retain surface detail without raising the ambient light.
This lighting is shared by Overview and mechanism previews.
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
  the CSS design tokens live in `src/theme.css`, shared animated navigation in
  `src/navigation.css`, and layout styles in `src/app.css`.

The persistent root layout owns one station instance. Sidebar navigation never
recreates the SDK connection. Settings lives at `/ds/settings/hardware`, with separate mechanism, connection,
and performance sections under `/ds/settings/`. The sidebar entry and ⌘/Ctrl+,
open the page; section URLs support refresh and browser history. Shadcn Tabs
provide keyboard navigation, and Collapsible rows reveal fields only after Edit.
Hardware and mechanisms each have search, compact summaries, and independent
apply actions. Mechanism previews mount only for the expanded editor.
The preview stretches to the form height on desktop, allowing portrait canvases,
and scrolls with the page. On narrow screens it stacks below the form with a
viewport-sized canvas. Manual controls stay beneath the canvas.
Runtime sidebar views retain controller input. Blur, hidden pages, Settings, and
STOP neutralize virtual/keyboard controls. The input enable switch retains its
value when navigating into and out of Settings.
Reduced-motion preferences disable cosmetic transitions.

Performance diagnostics live in **Settings → Performance**. See [MECHANISMS.md](../MECHANISMS.md#updating-simulation-and-performance-diagnostics) for RTT measurement details and rendering behavior.

The theme bundles Instrument Sans, Instrument Serif, and Geist Mono locally.
Instrument Serif is limited to page titles and the top-level Settings section
headings; card titles, form labels, and controls remain sans or mono. Shared
spacing tokens use a fixed 4 px scale, including shadcn utility spacing. Cards,
editors, and dialogs share 12 px padding; dense rows and floating toolbars use
8 px insets. Page gutters step from 24 to 16 to 12 px across breakpoints, and
controls retain 36 px standard / 28 px compact heights. Label gaps use 4 px,
card gaps use 8 px, and larger sections use 16 px separation. Nested pill
selectors retain a uniform 4 px inset and the padding/radius rule. Cards, fields, and OpMode lifecycle
buttons have square corners. Other buttons,
navigation, and sliding tab indicators use full pill rounding across interaction
states. Switches, status dots, and stick instruments also use full pill/circle
rounding. The solid background, transparent cards, hairline borders,
and accent colors come from shared tokens. Hover and focus feedback is immediate;
selected tab highlights retain the supplied 300 ms bounce curve. Sidebar links,
shadcn tabs, camera views, and controller selectors share
`sliding-indicator.ts`; the blue highlight follows the selected element’s measured
geometry, updates after fonts or layout change, and respects reduced motion.

Gamepad selectors have equal-width segments and a uniform 4 px inset. Their
outer radius is the inner pill radius plus the inset and border width. Compact
segments are 24 × 24 px. The highlight preserves fractional CSS-pixel bounds
and accounts for the container border and scroll position, including after a
resize or when a previously hidden widget becomes visible.

## Confirming critical changes

A shared shadcn dialog confirms driver/mechanism deletion, removing or replacing
a mechanism GLB, deleting or overwriting a start-position preset, and replacing
an existing robot configuration through a file, drop, or pasted JSON. Imports
are validated before confirmation. Driver deletion lists connected encoders and
affected mechanisms; mechanism deletion identifies attached origins that need
rebinding. Cancelling keeps the current draft and model assignments intact.

Explicitly replacing configured SDK hardware and updating existing simulation
mechanisms also confirm the state they reset. Automatic restoration of saved
configuration remains automatic. STOP and regular controls remain immediate.

Cancel receives initial focus, Escape dismisses, keyboard focus stays inside
the modal, and focus returns to the trigger (or settings navigation after a
deleted trigger). Actions recheck their configuration and connection before
committing. Pending confirmation blocks gamepad input and is cancelled on
navigation or station teardown.
