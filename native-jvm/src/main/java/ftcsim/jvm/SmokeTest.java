package ftcsim.jvm;

import com.qualcomm.hardware.lynx.commands.core.*;

/** Real SDK serialization -> TCP -> Python state -> real SDK response decoding. */
public final class SmokeTest {
    public static void main(String[] args) throws Exception {
        DesktopRuntime.initialize();
        int port = args.length > 0 ? Integer.parseInt(args[0]) : 9010;
        try (DesktopHub hub = new DesktopHub(port, 1)) {
            new LynxSetMotorConstantPowerCommand(hub, 0, 16384).send();
            int power = new LynxGetMotorConstantPowerCommand(hub, 0).sendReceive().getPower();
            if (power != 16384) throw new AssertionError("Motor power: " + power);
            int encoder = new LynxGetMotorEncoderPositionCommand(hub, 0).sendReceive().getPosition();
            new LynxSetMotorConstantPowerCommand(hub, 0, 0).send();
            System.out.println("JVM -> Python -> SDK OK; power=" + power + ", encoder=" + encoder);
        }
    }
}
