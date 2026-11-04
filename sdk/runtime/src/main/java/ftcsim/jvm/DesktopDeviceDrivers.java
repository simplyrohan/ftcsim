package ftcsim.jvm;

import android.app.Application;
import com.qualcomm.hardware.gobilda.GoBildaPinpointDriver;
import com.qualcomm.hardware.digitalchickenlabs.OctoQuadImpl;
import com.qualcomm.hardware.lynx.*;
import com.qualcomm.robotcore.hardware.*;
import com.qualcomm.robotcore.hardware.configuration.ConfigurationTypeManager;
import java.util.*;

/** SDK counterparts of Python drivers. Add one binding per new hub device type. */
final class DesktopDeviceDrivers {
    interface Factory { HardwareDevice create(Application context, DesktopHub hub, int port,
                                              LynxDcMotorController motors, LynxServoController servos); }
    static final class Binding {
        final String connection;
        final int ports;
        final Factory factory;
        Binding(String connection, int ports, Factory factory) {
            this.connection = connection; this.ports = ports; this.factory = factory;
        }
    }
    static final Map<String, Binding> TYPES = new LinkedHashMap<>();
    static {
        TYPES.put("motor", new Binding("motor", 4, (context, hub, port, motors, servos) -> new DcMotorImplEx(motors, port)));
        // Passive pods connected directly to a hub expose encoder reads through DcMotorEx.
        TYPES.put("odometry", new Binding("encoder", 4, (context, hub, port, motors, servos) -> new DcMotorImplEx(motors, port)));
        TYPES.put("octoquad_encoder", TYPES.get("odometry"));
        TYPES.put("servo", new Binding("servo", 6, (context, hub, port, motors, servos) ->
                new ServoImplEx(servos, port, ConfigurationTypeManager.getInstance().getStandardServoType())));
        TYPES.put("cr_servo", new Binding("servo", 6, (context, hub, port, motors, servos) ->
                new CRServoImplEx(servos, port, ConfigurationTypeManager.getInstance().getStandardServoType())));
        TYPES.put("pinpoint", new Binding("i2c", 4, (context, hub, port, motors, servos) -> {
            LynxI2cDeviceSynch client = new LynxI2cDeviceSynchV2(context, hub, port);
            GoBildaPinpointDriver device = new GoBildaPinpointDriver(client, true);
            device.initialize();
            return device;
        }));
        Binding octoquad = new Binding("i2c", 4, (context, hub, port, motors, servos) -> {
            LynxI2cDeviceSynch client = new LynxI2cDeviceSynchV2(context, hub, port);
            OctoQuadImpl device = new OctoQuadImpl(client, true) {
                @Override protected boolean doInitialize() {
                    // The desktop host has no Android manager for optional diagnostic listeners.
                    client.setBusSpeed(LynxI2cDeviceSynch.BusSpeed.FAST_400K);
                    refreshCache();
                    return true;
                }
            };
            device.initialize();
            return device;
        });
        TYPES.put("octoquad_mk1", octoquad);
        TYPES.put("octoquad_mk2", octoquad);
    }
    private DesktopDeviceDrivers() { }
}
