<h1 align="center">ftcsim</h1>
<p align="center">A desktop runtime and simulator for FTC robot code.</p>

<img align="center" src="/assets/page.png" style="border-radius: 15px;">

<br>

**ftcsim is not another FTC gameplay simulator.** It is a tool for software teams to directly test their robot's code without access to the physical robot. It works by swapping out the FtcRobotController for a custom version that communicates with a Python server. This server keeps track of motor states, sensor readings, and every other peripheral you could connect to a Lynx module. You can then configure your robot in the web driver station, which allows you to upload custom CAD models, change your hardware map, and configure mechanisms. Your code, ideally, never realizes it's not running on the real robot, giving you an accurate test platform for your robot's software.

## Installation and Setup

Make sure you have Python 3.10+ and Android Studio (which I would hope you do) installed
```sh
pip install ftcsim
```

**Setup**
```sh
cd /path/to/your/FTC-project
ftcsim --wizard
```
This will install the TeamCodeSim package and desktop version of the SDK into your project. It'll also add Gradle tasks to run the simulator. Don't worry, the normal robot target will still work normally.

<details>
  <summary>Windows troubleshooting</summary>

  You may have errors related to finding the `ftcsim` executable on Windows, which is due to a missing PATH variable you need to configure.

  First, try using the normal Command Prompt app instead of the Android Studio terminal.

  You may also need to add Python's Scripts folder to your path. For this run
  ```
  where python
  ```
  
  This will output a path like: `C:\Users\YourUsername\AppData\Local\Programs\Python\Python313\python.exe`
  - Your Scripts path will be in that exact same folder, inside a subfolder named `Scripts`
  - e.g. `C:\Users\YourUsername\AppData\Local\Programs\Python\Python313\Scripts`

  [Then add that Scripts path to your enviroment PATH variable.](https://realpython.com/add-python-to-path/#how-to-add-python-to-path-on-windows)
</details>

## Usage

Either in the Android Studio terminal or in another window run the robot simulator and driver station server.
```sh
ftcsim
```

You can use the Driver Station at [localhost:9015/ds/](http://localhost:9015/ds/).

Run `./gradlew runSimulator` in the robot project to launch its SDK and TeamCode. You can also change the Gradle target in Android Studio to run it from your IDE.

<img src="/assets/gradle.png" style="border-radius: 15px;">

## The Driver Station

This is where you will be spending most of your time with ftcsim. The main overview tab shows a 3D field with the configured robot, OpMode controls, and a gamepad preview.

The bottom-left of the screen shows the connection status of the server and TeamCode. If you're having trouble connecting, try restarting the servers. You can also click on the labels and troubleshoot the connection manually.

Once connected, you can try running your OpMode. More than likely though, you'll first need to configure your robot. In settings, the hardware map functions the same as a normal hardware map on the Driver Station. Add all your motors, servos, and other peripherals with the correct name.

<img src="/assets/hardware.png" height="300px">

After configuring the hardware map, you may want to configure "mechanisms" to get sensor feedback on subsystems like the drivetrain, or to add visualizations of simpler subsystems like a turret.

For all mechanisms, you need to first configure the ports the mechanism interacts with. For drivebases, these are the drive motors and optional odometry encoders and coprocessors. For custom mechanisms, it's the servo or motor that changes the position or orientation of this mechanism. 

In the "Model & origin" tab you can optionally add a 3D model as a GLB of your robot's subsystem. Configure the starting/zero position and orientation of the mechanism. For drivetrains, make sure the wheels are touching the ground. For custom mechanisms, the "Motion" tab sets how the motor's movement changes the 3D model.

> [!WARNING]
> Adding 3D models can make the app very laggy, very quickly. Definitely optimize your GLB files with a tool like [OptimizeGLB](https://optimizeglb.com/) before adding them. Generally, try to keep them under or around 20MB. If your computer still can't handle the models, ftcsim is still usable and useful without custom models.

## Progress and Shortcomings

ftcsim is still missing some features. Most importantly, it doesn't have some drivers/peripherals for the Lynx module yet. For multi-motor or velocity-based feedback software to work, we also need to define mechanisms that link motor/servo output to sensor readings. Right now, I have a simple mecanum drive mechanism and a tank drive mechanism implemented, but they also need more odometry options. I also need to implement more drivebases and other miscellaneous mechanisms like flywheels.

## Development

Source builds require Python 3.10+, JDK 17+, Node.js 22.12+, and npm

```sh
python3 -m pip install -e .
ftcsim --dev
```

Run `npm ci` and `npm run dev` in `driver-station/` for frontend development

```sh
python3 -m pip install build
python3 -m build
```

The Python build runs `scripts/build_driver_station.py` and
`scripts/build_sdk.py`. They compile the frontend and JVM libraries into the package. Either script can also be run
independently.

## License
This project is made by [@simplyrohan](https://github.com/simplyrohan) at 29619 Axiom Robotics. ftcsim is licensed under [GNU GPL v3](LICENSE). The bundled FTC SDK keeps its [license](sdk/LICENSE).

> [!IMPORTANT]
> I personally do not support using AI vibecoding in or out of FTC because it generally leads to lower-quality software, goes against FIRST's educational goals, and stops software innovation. That said, this project was built heavily with AI because it will be completely obsolete by the next FTC season, and the effort and time it would take to build it without AI wouldn't be worth the results.
