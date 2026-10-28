package ftcsim.jvm;

import android.app.Application;
import org.firstinspires.ftc.robotcore.internal.system.AppUtil;

public final class DesktopRuntime {
    private DesktopRuntime() { }
    /** Install a headless context without starting Android USB, camera or UI services. */
    public static synchronized Application initialize() {
        System.setProperty("ftcsim.jvm", "true");
        try {
            java.lang.reflect.Field field = AppUtil.class.getDeclaredField("application");
            field.setAccessible(true);
            if (field.get(AppUtil.getInstance()) == null) field.set(AppUtil.getInstance(), new Application());
            com.qualcomm.robotcore.hardware.configuration.ConfigurationTypeManager types =
                com.qualcomm.robotcore.hardware.configuration.ConfigurationTypeManager.getInstance();
            if (!(types.configurationTypeFromTag("Motor") instanceof com.qualcomm.robotcore.hardware.configuration.typecontainers.MotorConfigurationType)) {
                types.filterClass(com.qualcomm.robotcore.hardware.configuration.UnspecifiedMotor.class);
                types.filterClass(com.qualcomm.robotcore.hardware.Servo.class);
            }
            return AppUtil.getDefContext();
        } catch (ReflectiveOperationException e) { throw new IllegalStateException("Cannot initialize desktop SDK context", e); }
    }
}
