package org.firstinspires.ftc.teamcode.pedro;
import com.pedropathing.localization.*;
import com.pedropathing.math.*;
/** Example-only adapter: no simulated position feedback or network traffic. */
public final class StationaryLocalizer implements Localizer {
    private MotionState state = MotionState.zero();
    public void setPose(Pose pose) { state = MotionState.ofVelocity(pose, Velocity.zero()); }
    public MotionState state() { return state; }
    public void update() { }
    public void reset() { state = MotionState.zero(); }
}
