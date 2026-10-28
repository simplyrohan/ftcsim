package ftcsim.jvm;

import com.qualcomm.hardware.lynx.*;
import com.qualcomm.robotcore.hardware.*;

/** Exercise ordinary team-facing SDK devices through the same TCP boundary. */
public final class ControllerSmokeTest {
    public static void main(String[] args) throws Exception {
        android.app.Application context = DesktopRuntime.initialize();
        try (DesktopHub hub = new DesktopHub(Integer.parseInt(args[0]), 2)) {
            DcMotorEx motor = new DcMotorImplEx(new LynxDcMotorController(context, hub), 0);
            motor.setPower(0.5);
            // Clear the controller cache, so the following read must cross TCP.
            ((LynxDcMotorController)motor.getController()).forgetLastKnown();
            double power = motor.getPower();
            if (Math.abs(power - 0.5) > 0.001) throw new AssertionError("Motor power: " + power);
            int encoder = motor.getCurrentPosition();
            Servo servo = new ServoImpl(new LynxServoController(context, hub), 0);
            servo.setPosition(0.75);
            ((LynxServoController)servo.getController()).forgetLastKnown();
            double position = servo.getPosition();
            if (Math.abs(position - 0.75) > 0.01) throw new AssertionError("Servo position: " + position);
            hub.setBulkCachingMode(LynxModule.BulkCachingMode.MANUAL);
            hub.clearBulkCache();
            motor.getCurrentPosition();
            motor.setPower(0);
            System.out.println("SDK devices -> Python OK; power=" + power + ", encoder=" + encoder + ", servo=" + position);
        }
    }
}
