package org.firstinspires.ftc.teamcode

import com.pedropathing.follower.Follower
import com.qualcomm.robotcore.hardware.HardwareMap
import com.seattlesolvers.solverslib.command.Robot
import org.firstinspires.ftc.teamcode.pedro.Constants
import org.firstinspires.ftc.teamcode.subsystems.Intake
import org.firstinspires.ftc.teamcode.subsystems.Shooter
import org.firstinspires.ftc.teamcode.subsystems.Transfer
import org.firstinspires.ftc.teamcode.subsystems.Turret
import org.firstinspires.ftc.teamcode.util.Alliance
import org.firstinspires.ftc.teamcode.util.Field


class Robot(hardwareMap: HardwareMap, alliance: Alliance) : Robot() {
    val field = Field(alliance);

    val follower: Follower = Constants.create(hardwareMap)

    val intake = Intake(hardwareMap)
    val transfer = Transfer(hardwareMap)
    val shooter = Shooter(hardwareMap)
    val turret = Turret(hardwareMap)

    init {
        // must be called AFTER subsystem declarations so they can access each other (e.g. shooter can access follower)
        intake.init(this)
        transfer.init(this)
        shooter.init(this)
        turret.init(this)
    }

    fun update() {
        follower.update()

        this.run() // solverslib
    }

    fun stop() {
        this.reset()
    }
}