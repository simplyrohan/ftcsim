package ftcsim.jvm;

import com.qualcomm.hardware.lynx.LynxNackException;
import com.qualcomm.hardware.lynx.commands.core.LynxGetMotorConstantPowerCommand;

/** Negative-path integration checks driven by the Python test server. */
public final class ProtocolSmokeTest {
    public static void main(String[] args) throws Exception {
        DesktopRuntime.initialize();
        try (DesktopHub hub = new DesktopHub(Integer.parseInt(args[0]), 1)) {
            try {
                new LynxGetMotorConstantPowerCommand(hub, 0).sendReceive();
                throw new AssertionError("Expected a transport failure");
            } catch (LynxNackException e) {
                if (!args[1].equals("nack") || e.getNack().getNackReasonCode().getValue() != 255) throw e;
            } catch (IllegalStateException e) {
                if (!args[1].equals("malformed")) throw e;
            }
        }
        System.out.println("Expected " + args[1] + " handled");
    }
}
