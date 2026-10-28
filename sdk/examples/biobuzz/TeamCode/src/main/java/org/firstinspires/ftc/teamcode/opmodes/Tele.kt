package org.firstinspires.ftc.teamcode.opmodes


import com.pedropathing.follower.ManualDrive
import com.qualcomm.robotcore.eventloop.opmode.OpMode
import com.qualcomm.robotcore.eventloop.opmode.TeleOp
import com.seattlesolvers.solverslib.command.InstantCommand
import com.seattlesolvers.solverslib.command.button.GamepadButton
import com.seattlesolvers.solverslib.gamepad.GamepadEx
import com.seattlesolvers.solverslib.gamepad.GamepadKeys
import org.firstinspires.ftc.teamcode.Robot
import org.firstinspires.ftc.teamcode.util.Alliance


@TeleOp(name = "Red TeleOp")
class Tele : OpMode() {
    lateinit var robot: Robot
    lateinit var driverOp: GamepadEx

    override fun init() {
        robot = Robot(
            hardwareMap,
            Alliance.RED
        );
        robot.reset(); // seems to fix pid

        driverOp = GamepadEx(gamepad1)

        driverOp.getGamepadButton(GamepadKeys.Button.A)
            .whenPressed(InstantCommand(robot.intake::start))
            .whenReleased(InstantCommand(robot.intake::stop))

        driverOp.getGamepadButton(GamepadKeys.Button.RIGHT_BUMPER)
            .whenPressed(InstantCommand(robot.intake::lower))
        driverOp.getGamepadButton(GamepadKeys.Button.LEFT_BUMPER)
            .whenPressed(InstantCommand(robot.intake::raise))

        // todo: read from persistent storage class

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


        if (driverOp.getTrigger(GamepadKeys.Trigger.RIGHT_TRIGGER) > 0.3) {
            robot.transfer.transferring = true;
        }
        else {
            robot.transfer.transferring = false;
        }

        robot.update()
    }

    override fun stop() {
        robot.stop();
    }
}