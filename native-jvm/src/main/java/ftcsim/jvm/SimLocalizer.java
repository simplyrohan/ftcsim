package ftcsim.jvm;
import com.pedropathing.localization.*;
import com.pedropathing.math.*;
import com.qualcomm.robotcore.hardware.HardwareMap;
import com.google.gson.*;

/** Desktop replacement for the physical Pinpoint localizer, only used by the BioBuzz copy. */
public final class SimLocalizer implements Localizer {
    private MotionState state = MotionState.zero();
    public SimLocalizer(HardwareMap ignored) { update(); }
    public void setPose(Pose pose) {
        state = MotionState.ofVelocity(pose,Velocity.zero());
        JsonObject data=new JsonObject(); data.addProperty("x",pose.x());data.addProperty("y",pose.y());data.addProperty("heading",pose.heading());
        try { SimulatorLink.exchange("/api/pose",data); } catch(java.io.IOException e) { throw new IllegalStateException(e); }
    }
    public MotionState state() { return state; }
    public void update() {
        JsonObject pose=SimulatorLink.control.has("pose")?SimulatorLink.control.getAsJsonObject("pose"):new JsonObject();
        state=MotionState.ofVelocity(new Pose(value(pose,"x"),value(pose,"y"),value(pose,"heading")),new Velocity(value(pose,"vx"),value(pose,"vy"),value(pose,"omega")));
    }
    private static double value(JsonObject o,String name) { return o.has(name)?o.get(name).getAsDouble():0; }
    public void reset() { setPose(Pose.zero()); }
}
