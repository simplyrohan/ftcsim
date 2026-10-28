package org.firstinspires.ftc.teamcode.util

import com.pedropathing.api.PoseFactory
import com.pedropathing.math.Pose

enum class Alliance {
    RED,
    BLUE
}

enum class HiveTip {
    GARDEN,
    FLOWER,
//    TIPPING_TO_GARDEN,
//    TIPPING_TO_FLOWER,
}

class Field(val alliance: Alliance) {
    var hiveSide = HiveTip.GARDEN
    var hiveProgress = 0.0; // normalized (0.0-1.0) progress towards X when TIPPING_TO_X

    val poseFactory: PoseFactory = PoseFactory.degrees().apply {
        if (alliance == Alliance.BLUE) {
            mirrorX(70.75)
        }
    }
    val flowerPoseFactory: PoseFactory = poseFactory.mirrorY(70.75)

    val hivePose: Pose
        get() = (if (hiveSide == HiveTip.FLOWER) flowerPoseFactory else poseFactory).of(
            60.0,
            60.0,
            0.0
        ) // TODO: measure; uses flowerPoseFactory if needed

}