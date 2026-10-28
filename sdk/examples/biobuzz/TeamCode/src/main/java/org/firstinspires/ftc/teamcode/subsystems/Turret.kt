package org.firstinspires.ftc.teamcode.subsystems

import com.pedropathing.follower.Follower

import com.qualcomm.robotcore.hardware.HardwareMap
import com.qualcomm.robotcore.hardware.ServoImplEx
import com.seattlesolvers.solverslib.command.SubsystemBase
import org.firstinspires.ftc.teamcode.Robot
import org.firstinspires.ftc.teamcode.util.Field
import kotlin.math.atan2

class Turret(hardwareMap: HardwareMap) : SubsystemBase() {
    companion object {
        @JvmField
        var turretDegreesToServo = 1.0
    }

    lateinit var follower: Follower
    lateinit var field: Field
    val turretServoBack: ServoImplEx = hardwareMap.get(ServoImplEx::class.java, "turretServoBack")
    val turretServoFront: ServoImplEx = hardwareMap.get(ServoImplEx::class.java, "turretServoFront")

    var targetTurretPosition: Double = 0.0
        set(degrees) {
            if (field == degrees) return // lazy writes

            turretServoBack.position = degrees * turretDegreesToServo
            turretServoFront.position = degrees * turretDegreesToServo
            field = degrees
        }


    fun init(robot: Robot) {
        follower = robot.follower
        field = robot.field
    }

    override fun periodic() {
        val followerPose = follower.pose()
        val hivePose = field.hivePose

        val dx: Double = followerPose.x() - hivePose.x()
        val dy: Double = followerPose.y() - hivePose.y()
        val fieldCentricAngleRad = atan2(dy, dx); // 0deg=X+1 Y+1

        var robotCentricAngleRad =
            fieldCentricAngleRad - followerPose.heading() // 0deg = robot front
        robotCentricAngleRad = ((robotCentricAngleRad % 360) + 360) % 360 // wrap angle [0, 360]

        // todo: turret wrapping

        targetTurretPosition = Math.toDegrees(robotCentricAngleRad)
    }
}