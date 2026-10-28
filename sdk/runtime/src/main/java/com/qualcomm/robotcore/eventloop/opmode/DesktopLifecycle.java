package com.qualcomm.robotcore.eventloop.opmode;

import com.qualcomm.robotcore.hardware.*;
import com.qualcomm.robotcore.robocol.TelemetryMessage;
import org.firstinspires.ftc.robotcore.internal.opmode.OpModeServices;
import java.util.function.Consumer;

/** Package-local access adapter; the original SDK owns the OpMode execution thread. */
public final class DesktopLifecycle {
    private DesktopLifecycle() { }
    public static void init(OpMode mode, HardwareMap map, Consumer<TelemetryMessage> telemetry, Runnable stop) {
        mode.hardwareMap = map; mode.gamepad1 = new Gamepad(); mode.gamepad2 = new Gamepad();
        mode.internalOpModeServices = new OpModeServices() {
            public void refreshUserTelemetry(TelemetryMessage message, double interval) { telemetry.accept(message); }
            public void requestOpModeStop(OpMode requested) { if (requested == mode) stop.run(); }
        };
        mode.resetRuntime();
        mode.internalInit();
    }
    public static void start(OpMode mode) { mode.resetRuntime(); mode.internalStart(); }
    public static void tick(OpMode mode, Gamepad one, Gamepad two) {
        mode.newGamepadDataAvailable(one, two);
        mode.internalOnEventLoopIteration();
        mode.internalThrowOpModeExceptionIfPresent();
    }
    public static void stop(OpMode mode) throws InterruptedException {
        // Preserve upstream stop semantics, but never leave the control loop blocked indefinitely.
        Thread stop = new Thread(mode::internalStop, "DesktopOpModeStop");
        stop.setDaemon(true); stop.start(); stop.join(1500);
        if (stop.isAlive()) throw new IllegalStateException("OpMode did not stop; restart the desktop SDK");
    }
}
