package org.firstinspires.ftc.teamcode.subsystems

import com.pedropathing.follower.Follower
import com.qualcomm.robotcore.hardware.DcMotor
import com.qualcomm.robotcore.hardware.DcMotorEx
import com.qualcomm.robotcore.hardware.HardwareMap
import com.seattlesolvers.solverslib.command.SubsystemBase

import org.firstinspires.ftc.teamcode.Robot
import org.firstinspires.ftc.teamcode.util.Field
import kotlin.math.abs

class Shooter(hardwareMap: HardwareMap) : SubsystemBase() {
    companion object {
        @JvmField
        var shooterRPMToTicks = 28.0 // from GoBilda


        @JvmField
        var idleRPM = 2500.0

        @JvmField
        var kP = 1.0

        @JvmField
        var kF = 0.0
    }


    lateinit var follower: Follower
    lateinit var field: Field

    lateinit var regressionMode: String
    var regressionCoeffs = emptyArray<Double>()

    val shooterMotor: DcMotorEx = hardwareMap.get(DcMotorEx::class.java, "shooterMotor")

    var targetShooterRPM: Double = 0.0
        set(rpm) {
            shooterMotor.velocity = rpm * shooterRPMToTicks / 60.0
            field = rpm
        }

    fun init(robot: Robot) {
        follower = robot.follower
        field = robot.field

        shooterMotor.mode = DcMotor.RunMode.RUN_USING_ENCODER
        shooterMotor.setVelocityPIDFCoefficients(kP, 0.0, 0.0, kF)

        // load lut
        // if we have issues we'll use custom PID impl
        regressionMode = "linear"
        regressionCoeffs = arrayOf(0.0, 0.0) // Simulator default; no robot LUT was supplied.

    }

    override fun periodic() {
        val followerPose = follower.pose()
        val hivePose = field.hivePose

        val distance = followerPose.distance(hivePose)

        if (distance < 0) { // maybe also if it falls below a threshold?
            targetShooterRPM = idleRPM
            return
        }

        // todo: more lut modes
        var targetRPM = 0.0
        if (regressionMode == "linear") {
            targetRPM = regressionCoeffs[0] * distance + regressionCoeffs[1]
        }
        targetShooterRPM = targetRPM
    }
}