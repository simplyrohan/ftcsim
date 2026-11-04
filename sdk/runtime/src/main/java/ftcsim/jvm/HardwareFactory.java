package ftcsim.jvm;

import android.app.Application;
import com.google.gson.*;
import com.qualcomm.hardware.lynx.*;
import com.qualcomm.hardware.lynx.commands.standard.LynxFailSafeCommand;
import com.qualcomm.robotcore.hardware.*;
import java.util.*;

/** Configured names become genuine SDK controllers/devices backed by remote Lynx modules. */
final class HardwareFactory implements AutoCloseable {
    final HardwareMap map;
    final Map<Integer, DesktopHub> hubs = new LinkedHashMap<>();
    final List<LynxController> controllers = new ArrayList<>();
    final List<HardwareDevice> devicesToClose = new ArrayList<>();
    HardwareFactory(Application context, SimulatorTransport transport, JsonArray devices) throws Exception {
        validate(devices);
        transport.configure(devices);
        map = new HardwareMap(context, null);
        Map<Integer, LynxDcMotorController> motors = new HashMap<>();
        Map<Integer, LynxServoController> servos = new HashMap<>();
        try {
            for (JsonElement item : devices) {
                JsonObject d = item.getAsJsonObject();
                int module = d.get("module").getAsInt(), port = d.get("port").getAsInt();
                if (!hubs.containsKey(module)) {
                    DesktopHub hub = new DesktopHub(transport, module); hubs.put(module, hub); map.put("hub" + module, hub);
                    LynxDcMotorController mc = new LynxDcMotorController(context, hub);
                    LynxServoController sc = new LynxServoController(context, hub);
                    motors.put(module, mc); servos.put(module, sc); controllers.add(mc); controllers.add(sc);
                }
                DesktopDeviceDrivers.Binding binding = DesktopDeviceDrivers.TYPES.get(d.get("type").getAsString());
                HardwareDevice device = binding.factory.create(context, hubs.get(module), port, motors.get(module), servos.get(module));
                devicesToClose.add(device);
                map.put(d.get("name").getAsString(), device);
            }
            failsafe();
        } catch (Exception failure) { close(); throw failure; }
    }
    static void validate(JsonArray devices) {
        if (devices.size() > 256) throw new IllegalArgumentException("Too many devices");
        Set<String> names = new HashSet<>();
        Map<String, String> ports = new HashMap<>();
        for (JsonElement item : devices) {
            JsonObject d = item.getAsJsonObject();
            String name = d.get("name").getAsString(), type = d.get("type").getAsString();
            int module = integer(d, "module"), port = integer(d, "port");
            DesktopDeviceDrivers.Binding binding = DesktopDeviceDrivers.TYPES.get(type);
            if (binding == null) throw new IllegalArgumentException("Supported device types: " + DesktopDeviceDrivers.TYPES.keySet());
            if (module < 1 || module > 254 || port < 0 || port >= binding.ports) throw new IllegalArgumentException("Invalid hub address or port");
            if (name.trim().isEmpty() || name.matches("hub[0-9]+") || !names.add(name))
                throw new IllegalArgumentException("Duplicate, empty, or reserved device name: " + name);
            claimPort(ports, module, binding.connection, port, name);
            if (type.equals("motor")) claimPort(ports, module, "encoder", port, name);
        }
    }
    private static void claimPort(Map<String, String> ports, int module, String connection, int port, String name) {
        String previous = ports.putIfAbsent(module + ":" + connection + ":" + port, name);
        if (previous != null)
            throw new IllegalArgumentException("Port conflict: \"" + previous + "\" and \"" + name + "\" both use Hub " + module + " " + connection + " port " + port + ".");
    }
    private static int integer(JsonObject d, String key) {
        double value = d.get(key).getAsDouble();
        if (!Double.isFinite(value) || value != Math.rint(value)) throw new IllegalArgumentException("Expected integer " + key);
        return d.get(key).getAsInt();
    }
    void failsafe() {
        for (DesktopHub hub : hubs.values()) try { new LynxFailSafeCommand(hub).send(); } catch (Exception ignored) { }
        for (LynxController c : controllers) c.forgetLastKnown();
    }
    @Override public void close() {
        failsafe();
        for (HardwareDevice device : devicesToClose) try { device.close(); } catch (RuntimeException ignored) { }
        for (DesktopHub hub : hubs.values()) hub.close();
    }
}
