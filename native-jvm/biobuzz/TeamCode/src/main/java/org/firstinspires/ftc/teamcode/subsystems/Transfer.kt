package org.firstinspires.ftc.teamcode.subsystems

import com.qualcomm.robotcore.hardware.DcMotorEx
import com.qualcomm.robotcore.hardware.HardwareMap
import com.seattlesolvers.solverslib.command.SubsystemBase
import org.firstinspires.ftc.teamcode.Robot

class Transfer(hardwareMap: HardwareMap) : SubsystemBase() {
    val transferMotor: DcMotorEx = hardwareMap.get(DcMotorEx::class.java, "transferMotor");

    var transferring = false
        set(value) {
            if (value == field) return

            if (value) transferMotor.power = 1.0
            if (!value) transferMotor.power = 0.0
            field = value
        }

    fun init(robot: Robot) {}
}