package ftcsim.jvm;

import android.app.Application;
import com.google.gson.*;
import com.qualcomm.robotcore.eventloop.opmode.*;
import com.qualcomm.robotcore.hardware.Gamepad;
import java.net.URI;
import org.firstinspires.ftc.robotcore.internal.network.*;
import com.qualcomm.robotcore.robocol.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** Reusable desktop Robot Controller host. Start before connecting a Driver Station. */
public final class DesktopSdk implements AutoCloseable {
    private final Application context;
    private final SimulatorTransport simulator;
    private final DriverStationServer ds;
    private final Map<String, Class<? extends OpMode>> modes = new LinkedHashMap<>();
    private final AtomicBoolean requestedStop = new AtomicBoolean();
    private HardwareFactory hardware;
    private JsonArray devices;
    private Gamepad one = new Gamepad(), two = new Gamepad();
    private OpMode active;
    private String selected = "", state = "idle", error = "";
    private volatile boolean closing;
    private boolean poisoned;
    private boolean hardwareConfigured;
    private long lastGamepad;

    public DesktopSdk(URI endpoint, int dsPort, JsonArray configuration, List<String> opmodes) throws Exception {
        context = DesktopRuntime.initialize();
        // This completes the upgrade before any OpMode is constructed or initialized.
        simulator = new SimulatorTransport(endpoint);
        ds = new DriverStationServer(dsPort, endpoint.getPort() == -1 ? 80 : endpoint.getPort());
        try {
            for (String name : opmodes) register(Class.forName(name).asSubclass(OpMode.class));
            if (!modes.isEmpty()) selected = new ArrayList<>(modes.keySet()).get(modes.size() - 1);
            devices = new JsonParser().parse(configuration.toString()).getAsJsonArray();
            hardware = new HardwareFactory(context, simulator, devices);
            hardwareConfigured = devices.size() > 0;
            NetworkConnectionHandler.setDriverStationTransport(new DriverStationTransport() {
                public void sendCommand(Command command) {
                    JsonObject message = new JsonObject(); message.addProperty("type", "command");
                    message.addProperty("name", command.getName()); message.addProperty("extra", command.getExtra()); ds.event(message);
                }
                public void sendData(RobocolParsable data) throws com.qualcomm.robotcore.exception.RobotCoreException {
                    if (data instanceof TelemetryMessage) { telemetry((TelemetryMessage)data); return; }
                    JsonObject message = new JsonObject(); message.addProperty("type", "robocol");
                    message.addProperty("kind", data.getRobocolMsgType().toString());
                    message.addProperty("payload", Base64.getEncoder().encodeToString(data.toByteArray())); ds.event(message);
                }
            });
            publishHello(); publishState();
            // Timeout 0 keeps idle desktop connections open; heartbeat is managed by the host.
            ds.start(0, true);
        } catch (Throwable failure) { close(); throw failure; }
    }
    private void register(Class<? extends OpMode> type) throws Exception {
        if (type.isAnnotationPresent(Disabled.class)) return;
        type.getConstructor();
        TeleOp tele = type.getAnnotation(TeleOp.class);
        Autonomous auto = type.getAnnotation(Autonomous.class);
        String name = tele != null ? tele.name() : auto != null ? auto.name() : type.getSimpleName();
        if (name.isEmpty()) name = type.getSimpleName();
        if (modes.putIfAbsent(name, type) != null) throw new IllegalArgumentException("Duplicate OpMode name: " + name);
        if (selected.isEmpty()) selected = name;
    }
    private void publishHello() {
        JsonObject message = new JsonObject(); message.addProperty("type", "hello"); message.addProperty("version", 1);
        JsonArray list = new JsonArray();
        modes.forEach((name, type) -> {
            JsonObject item = new JsonObject(); item.addProperty("name", name); item.addProperty("class", type.getName());
            item.addProperty("flavor", type.isAnnotationPresent(Autonomous.class) ? "autonomous" : "teleop"); list.add(item);
        });
        message.add("opmodes", list); message.add("devices", devices); message.addProperty("hardwareConfigured", hardwareConfigured); ds.hello(message);
    }
    private void publishState() {
        JsonObject message = new JsonObject(); message.addProperty("type", "status"); message.addProperty("state", state);
        message.addProperty("selected", selected); message.addProperty("error", error);
        message.addProperty("simulatorConnected", simulator.isConnected());
        message.addProperty("elapsed", active == null ? 0 : active.getRuntime()); ds.state(message);
    }
    private void telemetry(TelemetryMessage source) {
        JsonObject message = new JsonObject(); message.addProperty("type", "telemetry"); message.addProperty("tag", source.getTag());
        JsonObject data = new JsonObject();
        synchronized (source) {
            source.getDataStrings().forEach(data::addProperty);
            source.getDataNumbers().forEach(data::addProperty);
        }
        message.add("data", data); ds.telemetry(message);
    }
    public void run() throws InterruptedException {
        while (!closing) {
            long before = System.nanoTime();
            if (ds.disconnected.getAndSet(false)) stop("Driver Station disconnected");
            if (active != null && (!ds.hasController() || before - ds.lastInput > 1_500_000_000L)) stop("Driver Station heartbeat expired");
            if (!simulator.isConnected() && !poisoned) {
                poisoned = true; stop("Simulator disconnected; restart the SDK"); state = "error"; error = "Simulator disconnected; restart the SDK";
            }
            DriverStationServer.Command command;
            for (int count = 0; count < 64 && (command = ds.commands.poll()) != null; count++) {
                if (!ds.isController(command.peer)) continue;
                try { handle(command.data); ds.reply(command, true, "ok"); }
                catch (Throwable failure) { ds.reply(command, false, failure.toString()); }
            }
            if (requestedStop.getAndSet(false)) stop("");
            if (active != null) {
                try {
                    // Neutralize stale controls even if a client keeps sending heartbeat frames.
                    if (before - lastGamepad > 500_000_000L) { one = new Gamepad(); two = new Gamepad(); }
                    DesktopLifecycle.tick(active, one, two);
                } catch (Throwable failure) {
                    failure.printStackTrace(); stop(""); state = "error"; error = failure.toString();
                }
            }
            publishState();
            long wait = 20_000_000 - (System.nanoTime() - before);
            if (wait > 0) Thread.sleep(wait / 1_000_000, (int)(wait % 1_000_000));
        }
    }
    private void handle(JsonObject data) throws Exception {
        String type = data.get("type").getAsString();
        switch (type) {
            case "gamepads": {
                Gamepad nextOne = gamepad(data.getAsJsonObject("gamepad1")), nextTwo = gamepad(data.getAsJsonObject("gamepad2"));
                one = nextOne; two = nextTwo; lastGamepad = System.nanoTime(); break;
            }
            case "select":
                requireInactive();
                String name = data.get("name").getAsString();
                if (!modes.containsKey(name)) throw new IllegalArgumentException("Unknown OpMode: " + name);
                selected = name; error = ""; break;
            case "configure": {
                requireInactive();
                JsonArray proposed = data.getAsJsonArray("devices");
                HardwareFactory.validate(proposed);
                // Preflight the complete physical tree before retiring the current SDK objects.
                simulator.validateConfiguration(proposed);
                // Close against the old topology; old hubs must not address the new one.
                hardware.close();
                try { hardware = new HardwareFactory(context, simulator, proposed); }
                catch (Exception failure) {
                    try { hardware = new HardwareFactory(context, simulator, devices); }
                    catch (Exception restoreFailure) {
                        failure.addSuppressed(restoreFailure); poisoned = true; simulator.close();
                        state = "error"; error = "Hardware reconfiguration failed; restart the SDK";
                    }
                    throw failure;
                }
                devices = new JsonParser().parse(proposed.toString()).getAsJsonArray(); hardwareConfigured = true; publishHello(); break;
            }
            case "init":
                requireInactive();
                if (!hardwareConfigured) throw new IllegalStateException("Apply a hardware map from the Driver Station before INIT"); hardware.failsafe(); error = ""; requestedStop.set(false);
                one = new Gamepad(); two = new Gamepad();
                active = modes.get(selected).getDeclaredConstructor().newInstance();
                try { DesktopLifecycle.init(active, hardware.map, this::telemetry, () -> requestedStop.set(true)); state = "initialized"; }
                catch (Throwable failure) { stop(""); state = "error"; error = failure.toString(); throw failure; }
                break;
            case "start":
                if (!state.equals("initialized") || active == null) throw new IllegalStateException("INIT an OpMode first");
                DesktopLifecycle.start(active); state = "running"; break;
            case "stop": stop(""); break;
            default: throw new IllegalArgumentException("Unknown Driver Station message: " + type);
        }
    }
    private void requireInactive() {
        if (poisoned) throw new IllegalStateException("Restart SDK after transport loss or an unresponsive OpMode");
        if (active != null) throw new IllegalStateException("STOP before selecting/configuring/initializing");
    }
    private void stop(String reason) {
        OpMode previous = active; active = null;
        one = new Gamepad(); two = new Gamepad();
        try { if (previous != null) DesktopLifecycle.stop(previous); }
        catch (Exception failure) {
            poisoned = true; error = failure.toString(); simulator.close();
        } finally {
            if (hardware != null) hardware.failsafe();
            state = poisoned ? "error" : "stopped";
            if (!reason.isEmpty()) error = reason;
        }
    }
    private static final String[] AXES = {"left_stick_x", "left_stick_y", "right_stick_x", "right_stick_y", "left_trigger", "right_trigger"};
    private static final String[] BUTTONS = {"a", "b", "x", "y", "dpad_up", "dpad_down", "dpad_left", "dpad_right", "left_bumper", "right_bumper", "left_stick_button", "right_stick_button", "guide", "start", "back", "touchpad"};
    private static Gamepad gamepad(JsonObject data) throws Exception {
        Gamepad pad = new Gamepad();
        if (data == null) return pad;
        pad.setGamepadId(Gamepad.ID_SYNTHETIC); pad.timestamp = android.os.SystemClock.uptimeMillis();
        for (String axis : AXES) if (data.has(axis)) {
            float value = data.get(axis).getAsFloat();
            if (!Float.isFinite(value) || value < (axis.endsWith("trigger") ? 0 : -1) || value > 1) throw new IllegalArgumentException("Invalid axis: " + axis);
            Gamepad.class.getField(axis).setFloat(pad, value);
        }
        for (String button : BUTTONS) if (data.has(button)) {
            JsonPrimitive value = data.getAsJsonPrimitive(button);
            if (!value.isBoolean()) throw new IllegalArgumentException("Expected boolean: " + button);
            Gamepad.class.getField(button).setBoolean(pad, value.getAsBoolean());
        }
        return pad;
    }
    @Override public synchronized void close() {
        if (closing) return;
        closing = true; stop("");
        if (hardware != null) hardware.close();
        ds.stop(); simulator.close();
        NetworkConnectionHandler.setDriverStationTransport(null);
    }
    public static void main(String[] args) throws Exception {
        URI endpoint = URI.create("ws://localhost:9015/sim"); int port = 1115;
        List<String> opmodes = new ArrayList<>();
        JsonArray devices = new JsonArray();
        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--sim": endpoint = URI.create(args[++i]); break;
                case "--ds-port": port = Integer.parseInt(args[++i]); break;
                case "--opmode": opmodes.add(args[++i]); break;
                default: throw new IllegalArgumentException("Unknown argument: " + args[i]);
            }
        }
        try (DesktopSdk sdk = new DesktopSdk(endpoint, port, devices, opmodes)) {
            Runtime.getRuntime().addShutdownHook(new Thread(sdk::close, "DesktopSdkShutdown"));
            System.out.println("SDK ready: ws://localhost:" + port + "/ds; simulator " + endpoint);
            sdk.run();
        }
    }
}
