package ftcsim.jvm;

import android.app.Application;
import com.google.gson.*;
import com.qualcomm.hardware.lynx.*;
import com.qualcomm.hardware.lynx.commands.standard.LynxFailSafeCommand;
import com.qualcomm.robotcore.hardware.*;
import com.qualcomm.robotcore.hardware.configuration.ConfigurationTypeManager;
import java.util.*;

/** Configured names become genuine SDK controllers/devices backed by remote Lynx modules. */
final class HardwareFactory implements AutoCloseable {
    final HardwareMap map;
    final Map<Integer, DesktopHub> hubs = new LinkedHashMap<>();
    final List<LynxController> controllers = new ArrayList<>();
    HardwareFactory(Application context, SimulatorTransport transport, JsonArray devices) throws Exception {
        validate(devices);
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
                HardwareDevice device = d.get("type").getAsString().equals("motor")
                        ? new DcMotorImplEx(motors.get(module), port)
                        : new ServoImplEx(servos.get(module), port, ConfigurationTypeManager.getInstance().getStandardServoType());
                map.put(d.get("name").getAsString(), device);
            }
            failsafe();
        } catch (Exception failure) { close(); throw failure; }
    }
    static void validate(JsonArray devices) {
        if (devices.size() > 256) throw new IllegalArgumentException("Too many devices");
        Set<String> names = new HashSet<>(), ports = new HashSet<>();
        for (JsonElement item : devices) {
            JsonObject d = item.getAsJsonObject();
            String name = d.get("name").getAsString(), type = d.get("type").getAsString();
            int module = integer(d, "module"), port = integer(d, "port");
            if (!(type.equals("motor") || type.equals("servo"))) throw new IllegalArgumentException("Supported device types: motor, servo");
            if (module < 1 || module > 254 || port < 0 || port >= (type.equals("motor") ? 4 : 6)) throw new IllegalArgumentException("Invalid hub address or port");
            if (name.trim().isEmpty() || name.matches("hub[0-9]+") || !names.add(name) || !ports.add(module + ":" + type + ":" + port))
                throw new IllegalArgumentException("Duplicate/reserved name or duplicate port: " + name);
        }
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
    @Override public void close() { failsafe(); for (DesktopHub hub : hubs.values()) hub.close(); }
}
