# BioBuzz desktop example

This is an isolated copy of BioBuzz revision
`797d3603999e7a039510278b049f039deab43ba3`. The original BioBuzz checkout is never
read or written by the build. `UPSTREAM.txt` and `upstream-source.sha256.json`
record the original revision and original source hashes.

Start `sim/server.py` independently, then from `sdk/desktop` run:

```sh
./gradlew :biobuzz:run
```

Open `http://localhost:9015/ds`, select **Red TeleOp**, INIT and START. Gamepad A
runs/releases the intake, bumpers lower/raise it, right trigger runs transfer, and
the sticks drive. The copied TeleOp, actual SolversLib and Pedro drivetrain code,
and SDK motor controllers execute on the JVM. Python handles only hub state.

`robot.json` maps the assumed two hubs, eight motors and four servos; real robot
XML was not supplied, so review names and ports before using other programs.

Copy-only adaptations carried forward from the previous implementation:

- Removed unused Panels/Marrow imports/settings access; safe shooter feedforward
  defaults are zero.
- Corrected the transfer setter's duplicate `if (value)` stop condition to
  `if (!value)` and shooter RPM conversion to ticks/second.
- Replaced the physical Pinpoint localizer with `StationaryLocalizer`, wholly
  inside this example. It never contacts Python or produces motion feedback.

Only the TeleOp, its subsystem/util code and Constants compile here; autonomous
and tuning sources are preserved but excluded. The upstream `robot.reset()` and
SolversLib scheduling behavior remain, including its limitation on automatic
shooter/turret periodic registration. No diagnostic motor overrides are injected
by the DS. Field-relative localization, automatic aiming and autonomous accuracy
are not simulated. The physical panel shows motor status/speed/encoder only.
