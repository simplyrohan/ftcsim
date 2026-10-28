package org.firstinspires.ftc.teamcode.subsystems

import com.qualcomm.robotcore.hardware.DcMotorEx
import com.qualcomm.robotcore.hardware.HardwareMap
import com.qualcomm.robotcore.hardware.ServoImplEx
import com.bylazar.configurables.annotations.Configurable;
import com.seattlesolvers.solverslib.command.SubsystemBase
import org.firstinspires.ftc.teamcode.Robot

@Configurable
class Intake(hardwareMap: HardwareMap) : SubsystemBase() {
    companion object {
        @JvmField
        var servoPosRaised = 1.0;
        @JvmField
        var servoPosLowered = 0.0;
    }
    val motorFront: DcMotorEx = hardwareMap.get(DcMotorEx::class.java, "intakeMotorFront");
    val motorBack: DcMotorEx = hardwareMap.get(DcMotorEx::class.java, "intakeMotorBack");

    val servoFront: ServoImplEx = hardwareMap.get(ServoImplEx::class.java, "intakeServoFront");
    val servoBack: ServoImplEx = hardwareMap.get(ServoImplEx::class.java, "intakeServoBack");

    var running: Boolean = false
        private set

    var raised: Boolean = true
        private set

    fun start() {
        // todo bulk write
        running = true;
        motorFront.power = 1.0;
        motorBack.power = 1.0;
    }

    fun stop() {
        running = false;
        motorFront.power = 0.0;
        motorBack.power = 0.0;
    }

    fun raise() {
        raised = true;
        servoFront.position = servoPosRaised;
        servoBack.position = servoPosRaised;
    }

    fun lower() {
        raised = false;
        servoFront.position = servoPosLowered;
        servoBack.position = servoPosLowered;
    }

    fun init(robot: Robot) {}

    override fun periodic() {
    }
}