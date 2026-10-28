package org.firstinspires.ftc.teamcode.opmodes

import com.pedropathing.follower.ManualDrive
import com.qualcomm.robotcore.eventloop.opmode.OpMode
import com.qualcomm.robotcore.eventloop.opmode.Utility
import com.skeletonarmy.marrow.settings.Settings
import org.firstinspires.ftc.teamcode.Robot
import org.firstinspires.ftc.teamcode.util.Alliance

@Utility(name = "Shooter Tuner")
class ShooterTuning : OpMode() {
    lateinit var robot: Robot;

    override fun init() {
        robot = Robot(
            hardwareMap,
            Alliance.RED
        );

        // todo: define start pose
    }

    override fun loop() {
        val powers = ManualDrive.fieldCentric(
            -gamepad1.left_stick_y.toDouble(),
            gamepad1.left_stick_x.toDouble(),
            gamepad1.right_stick_x.toDouble(),
            robot.follower.pose().heading()
        )
        robot.follower.manual(powers)
        // or
        // ManualDrive.driveOrHold(follower, powers)
        robot.follower.update()

        robot.update()

        if (gamepad1.aWasPressed()) {
            robot.intake.start()
        }

        if (gamepad1.aWasReleased()) {
            robot.intake.stop()
        }



        // todo: shooter controls/wizard
        // todo: distance telemetry
        // todo: regression model

        val followerPose = robot.follower.pose()
        val hivePose = robot.field.hivePose

        val distance = followerPose.distance(hivePose)

        telemetry.addData("Distance from Hive", distance)


        // Settings.set("regressionModel", "linear");
        // Settings.set("regressionCoeffs", arrayOf(1.0, 2.0));
    }

    override fun stop() {
        robot.stop();
    }
}