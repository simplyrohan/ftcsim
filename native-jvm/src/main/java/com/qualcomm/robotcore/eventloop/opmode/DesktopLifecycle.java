package com.qualcomm.robotcore.eventloop.opmode;
import com.qualcomm.robotcore.hardware.*;
import org.firstinspires.ftc.robotcore.internal.opmode.OpModeServices;
import com.qualcomm.robotcore.robocol.TelemetryMessage;
/** Runs iterative SDK OpModes with explicit desktop inputs, without the Android event loop. */
public final class DesktopLifecycle {
    public static void prepare(OpMode mode, HardwareMap map) {
        if (mode instanceof LinearOpMode) throw new UnsupportedOperationException("This runner currently supports iterative OpModes only");
        mode.hardwareMap=map;mode.gamepad1=new Gamepad();mode.gamepad2=new Gamepad();
        mode.internalOpModeServices=new OpModeServices() {
            public void refreshUserTelemetry(TelemetryMessage telemetry,double interval) { }
            public void requestOpModeStop(OpMode requested) { mode.stopRequested=true; }
        };
    }
    public static void start(OpMode mode) { mode.isStarted=true; mode.resetRuntime(); mode.start(); }
    public static boolean stopped(OpMode mode) { return mode.stopRequested; }
    public static void loop(OpMode mode,Gamepad input) {
        mode.gamepad1.copy(input); mode.time=mode.getRuntime(); mode.loop(); mode.telemetry.update();
    }
    public static void stop(OpMode mode) { mode.stopRequested=true;mode.stop(); }
}
