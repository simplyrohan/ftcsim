import org.gradle.kotlin.dsl.apply
import org.gradle.kotlin.dsl.dependencies
import org.gradle.kotlin.dsl.maven
import org.gradle.kotlin.dsl.repositories

repositories {
    mavenCentral()
    google()
    maven("https://repo.dairy.foundation/releases/")
    maven("https://mymaven.bylazar.com/releases")
}

dependencies {
    // FTC SDK
    add("implementation", "org.firstinspires.ftc:Inspection:12.0.0")
    add("implementation", "org.firstinspires.ftc:Blocks:12.0.0")
    add("implementation", "org.firstinspires.ftc:RobotCore:12.0.0")
    add("implementation", "org.firstinspires.ftc:RobotServer:12.0.0")
    add("implementation", "org.firstinspires.ftc:OnBotJava:12.0.0")
    add("implementation", "org.firstinspires.ftc:Hardware:12.0.0")
    add("implementation", "org.firstinspires.ftc:FtcCommon:12.0.0")
    add("implementation", "org.firstinspires.ftc:Vision:12.0.0")

    add("implementation", "androidx.appcompat:appcompat:1.2.0")

    // Pedro Pathing
    add("implementation", "com.pedropathing:revhub:3.0.2")
    add("implementation", "com.pedropathing:tuning:1.0.0")

    // SolversLib
    add("implementation", "org.solverslib:core:0.3.6")
    add("implementation", "org.solverslib:pedroPathing:0.3.6")


    // Marrow
    add("implementation", "com.skeletonarmyftc.marrow:core:1.2.2")

    // Panels
    add("implementation", "com.bylazar.sloth:fullpanels:0.3.2+1.0.13")

    // Dairy
    add("implementation", "dev.frozenmilk.dairy:Core:2.2.4")
}