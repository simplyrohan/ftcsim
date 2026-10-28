package ftcsim.jvm;
import com.qualcomm.robotcore.eventloop.opmode.*;
import com.qualcomm.robotcore.hardware.*;

@Autonomous(name = "Linear motor demo", group = "Desktop")
public final class LinearMotorDemo extends LinearOpMode {
    public void runOpMode() throws InterruptedException {
        DcMotorEx motor = hardwareMap.get(DcMotorEx.class, "motor");
        telemetry.addData("ready", "linear"); telemetry.update();
        waitForStart();
        try {
            while (opModeIsActive()) {
                motor.setPower(gamepad1.a ? .5 : 0);
                telemetry.addData("encoder", motor.getCurrentPosition()); telemetry.update();
                sleep(20);
            }
        } finally { motor.setPower(0); }
    }
}
