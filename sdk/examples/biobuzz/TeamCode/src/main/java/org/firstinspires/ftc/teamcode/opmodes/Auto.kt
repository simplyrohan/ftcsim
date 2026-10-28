package org.firstinspires.ftc.teamcode.opmodes

import com.qualcomm.robotcore.eventloop.opmode.Autonomous
import com.qualcomm.robotcore.eventloop.opmode.OpMode
import com.skeletonarmy.marrow.settings.Settings
import org.firstinspires.ftc.teamcode.Robot
import org.firstinspires.ftc.teamcode.util.Alliance

@Autonomous(name = "Auton")
class Auto : OpMode() {
    lateinit var robot: Robot;

    override fun init() {
        robot = Robot(
            hardwareMap,
            Alliance.RED
        );
    }

    override fun loop() {
        robot.update()
    }

    override fun stop() {
        // TODO: persistent storage class
    }
}