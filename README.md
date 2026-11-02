# ftcsim

A desktop FTC simulator: the modified Java SDK runs TeamCode, Python models
hardware and mechanisms, and a SvelteKit Driver Station configures and displays
the robot. Mechanisms connect simulated drivers without appearing in the SDK.

The desktop host runs standalone FTC `@OnCreate`/`@OnDestroy` hooks from TeamCode
and its dependencies. Libraries requiring Android event-loop or web-server hooks
are reported and skipped. FTC Dashboard and Panels need desktop adapters before
their full dashboards can run; Sloth's Android hot reload is not supported.

## Run

```sh
pipx install ftcsim
cd /path/to/your/FTC-project
ftcsim --wizard
ftcsim
```

Run `./gradlew runSimulator` in the robot project to launch its SDK and TeamCode.
`ftcsim --help` lists CLI options. Wheel installations include the compiled SDK
and Driver Station; robot projects need JDK 17+.

## Develop and build

Source builds require Python 3.10+, JDK 17+, Node.js 22.12+, and npm.

```sh
python3 -m pip install -e .
ftcsim --dev
```

Run `npm ci` and `npm run dev` in `driver-station/` for frontend development;
`npm run check` checks its TypeScript and Svelte code. Development proxy overrides
are listed in `driver-station/.env.example`.

```sh
python3 -m pip install build
python3 -m build
```

The Python build invokes `scripts/build_driver_station.py` and
`scripts/build_sdk.py`. They compile and stage frontend assets, dependency
licenses, and JVM libraries into the package. Either script can also be run
independently. The SDK resource generator remains part of its Gradle build.

## Protocols and formats

[PROTOCOL.md](PROTOCOL.md) defines the custom SDK/Driver Station messages,
simulator API, and `.fs` robot archive format. SDK sources retain their upstream
namespaces and license notices. The Android SDK workspace remains independent
of the desktop build.
