# ftcsim

A desktop runtime and simulator for FTC robot code.

## Installation and Setup

Make sure you have Python 3.10+ and Android Studio (which I would hope you do) installed.
```sh
pip install ftcsim
```
or
```sh
pipx install ftcsim
```

**Setup**
```sh
cd /path/to/your/FTC-project
ftcsim --wizard
```
This will install the TeamCodeSim package and desktop version of the SDK into your project. It'll also add gradle tasks to start the simulator.

## Usage

Either in the Android Studio terminal or in another window run the robot simulator and driver station server.
```sh
ftcsim
```

You can use the Driver Station at [localhost:9015/ds/](http://localhost:9015/ds/).

Run `./gradlew runSimulator` in the robot project to launch its SDK and TeamCode. You can also change the Gradle target in Android Studio to run it from your IDE.

TODO: Add screenshot

## Development

Source builds require Python 3.10+, JDK 17+, Node.js 22.12+, and npm.

```sh
python3 -m pip install -e .
ftcsim --dev
```

Run `npm ci` and `npm run dev` in `driver-station/` for frontend development;

```sh
python3 -m pip install build
python3 -m build
```

The Python build runs `scripts/build_driver_station.py` and
`scripts/build_sdk.py`. They compile the frontend and JVM libraries into the package. Either script can also be run
independently.

## License
ftcsim is licensed under [GNU GPL v3](LICENSE). The bundled FTC SDK retains its own [license](sdk/LICENSE).
