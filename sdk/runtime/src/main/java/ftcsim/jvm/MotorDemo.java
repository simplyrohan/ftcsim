package ftcsim.jvm;
import com.qualcomm.robotcore.eventloop.opmode.*;
import com.qualcomm.robotcore.hardware.*;

@TeleOp(name = "Motor demo", group = "Desktop")
public final class MotorDemo extends OpMode {
    private DcMotorEx motor;
    public void init() { motor = hardwareMap.get(DcMotorEx.class, "motor"); telemetry.setDisplayFormat(org.firstinspires.ftc.robotcore.external.Telemetry.DisplayFormat.MONOSPACE); telemetry.addData("ready", "motor"); }
    public void loop() {
        motor.setPower(gamepad1.a ? 1 : -gamepad1.left_stick_y);
        telemetry.addData("encoder", motor.getCurrentPosition());
        telemetry.addData("power", motor.getPower());
        telemetry.addData("gamepad2_a", gamepad2.a);
    }
    public void stop() { motor.setPower(0); }
}
