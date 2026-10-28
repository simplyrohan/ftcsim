package ftcsim.jvm;
import com.google.gson.*;
import com.qualcomm.robotcore.hardware.*;
import com.qualcomm.robotcore.eventloop.opmode.*;
import com.qualcomm.hardware.lynx.*;
import com.qualcomm.hardware.lynx.commands.standard.LynxFailSafeCommand;
import com.qualcomm.robotcore.hardware.configuration.ConfigurationTypeManager;
import java.util.*;
import java.lang.reflect.*;

/** Run the copied BioBuzz Red TeleOp; every motor/servo write uses actual SDK Lynx controllers. */
public final class BioBuzzRunner {
    private static final Map<Integer,DesktopHub> hubs=new LinkedHashMap<>();
    private static OpMode mode;
    private static String status="idle", error="";
    private static long lastAction;
    public static void main(String[] args) throws Exception {
        SimulatorLink.base="http://127.0.0.1:"+args[0];
        int lynxPort=Integer.parseInt(args[1]);
        android.app.Application context=DesktopRuntime.initialize();
        try {
            SimulatorLink.control=SimulatorLink.exchange("/api/control",null);
            JsonArray devices=SimulatorLink.control.getAsJsonArray("devices");
            HardwareMap map=new HardwareMap(context,null);
            Map<Integer,LynxDcMotorController> motors=new HashMap<>();
            Map<Integer,LynxServoController> servos=new HashMap<>();
            for(JsonElement entry:devices) {
                JsonObject d=entry.getAsJsonObject();int address=d.get("module").getAsInt(),port=d.get("port").getAsInt();
                if(!hubs.containsKey(address)) {
                    DesktopHub hub=new DesktopHub(lynxPort,address);hubs.put(address,hub);map.put("hub"+address,hub);
                    motors.put(address,new LynxDcMotorController(context,hub));servos.put(address,new LynxServoController(context,hub));
                }
                HardwareDevice device;
                if(d.get("type").getAsString().equals("motor")) device=new DcMotorImplEx(motors.get(address),port);
                else device=new ServoImplEx(servos.get(address),port,ConfigurationTypeManager.getInstance().getStandardServoType());
                map.put(d.get("name").getAsString(),device);
            }
            failSafe();
            publish();
            Runtime.getRuntime().addShutdownHook(new Thread(BioBuzzRunner::failSafe));
            while(true) {
                long began=System.nanoTime();
                SimulatorLink.control=SimulatorLink.exchange("/api/control",null);
                String desired=SimulatorLink.control.get("desired").getAsString();
                if(desired.equals("init") && (mode==null || status.equals("stopped") || status.equals("error"))) {
                    failSafe(); error="";
                    // A failsafe changes hub state outside the SDK controller caches.
                    for(LynxDcMotorController controller:motors.values()) controller.forgetLastKnown();
                    for(LynxServoController controller:servos.values()) controller.forgetLastKnown();
                    try {
                        mode=(OpMode)Class.forName("org.firstinspires.ftc.teamcode.opmodes.Tele").getDeclaredConstructor().newInstance();
                        DesktopLifecycle.prepare(mode,map);mode.init();status="initialized";
                    } catch(Throwable e) { onError(e); }
                }
                if(desired.equals("start") && status.equals("initialized")) { DesktopLifecycle.start(mode);status="running"; }
                if((desired.equals("stop") && !status.equals("stopped")) || (mode!=null && DesktopLifecycle.stopped(mode) && status.equals("running"))) {
                    stop();status="stopped";
                }
                if(status.equals("running")) {
                    try {
                        Gamepad input=new Gamepad();JsonObject g=SimulatorLink.control.getAsJsonObject("gamepad");
                        input.left_stick_x=(float)number(g,"left_stick_x");input.left_stick_y=(float)number(g,"left_stick_y");
                        input.right_stick_x=(float)number(g,"right_stick_x");input.right_trigger=(float)number(g,"right_trigger");
                        input.a=bool(g,"a");input.left_bumper=bool(g,"left_bumper");input.right_bumper=bool(g,"right_bumper");
                        DesktopLifecycle.loop(mode,input);
                        for(DesktopHub hub:hubs.values()) if(!hub.isTransportConnected())
                            throw new IllegalStateException("Lynx connection lost; restart the simulator");
                        JsonObject action=SimulatorLink.control.getAsJsonObject("action");
                        if(action!=null && action.get("id").getAsLong()>lastAction) { lastAction=action.get("id").getAsLong();action(action); }
                    } catch(Throwable e) { onError(e); }
                }
                publish();
                long remaining=20_000_000-(System.nanoTime()-began);
                if(remaining>0) Thread.sleep(remaining/1_000_000,(int)(remaining%1_000_000));
            }
        } catch(Throwable e) { onError(e);publish();throw e; }
        finally { failSafe();for(DesktopHub hub:hubs.values()) hub.close(); }
    }
    private static void action(JsonObject action) throws Exception {
        Object robot=mode.getClass().getMethod("getRobot").invoke(mode);
        String name=action.get("name").getAsString();
        if(name.equals("turret")) {
            double position=action.get("position").getAsDouble();
            mode.hardwareMap.get(ServoImplEx.class,"turretServoBack").setPosition(position);
            mode.hardwareMap.get(ServoImplEx.class,"turretServoFront").setPosition(position);
        }
        if(name.equals("shooter")) {
            Object shooter=robot.getClass().getMethod("getShooter").invoke(robot);
            shooter.getClass().getMethod("setTargetShooterRPM",double.class).invoke(shooter,action.get("rpm").getAsDouble());
        }
    }
    private static double number(JsonObject o,String k) { return o.has(k)?o.get(k).getAsDouble():0; }
    private static boolean bool(JsonObject o,String k) { return o.has(k)&&o.get(k).getAsBoolean(); }
    private static void publish() throws java.io.IOException {
        JsonObject data=new JsonObject();data.addProperty("status",status);data.addProperty("error",error);data.addProperty("opmode","Red TeleOp");
        if(mode!=null)data.addProperty("elapsed",mode.getRuntime());
        SimulatorLink.exchange("/api/runtime",data);
    }
    private static void stop() {
        try { if(mode!=null && !status.equals("stopped")) DesktopLifecycle.stop(mode); }
        finally { failSafe(); }
    }
    private static void onError(Throwable failure) {
        while(failure instanceof InvocationTargetException && failure.getCause()!=null)failure=failure.getCause();
        failure.printStackTrace();error=failure.toString();status="error";failSafe();
    }
    private static synchronized void failSafe() {
        for(DesktopHub hub:hubs.values())try {new LynxFailSafeCommand(hub).send();}catch(Exception ignored) { }
    }
}
