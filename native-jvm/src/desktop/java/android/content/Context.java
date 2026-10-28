package android.content;
public class Context {
    public static final int MODE_PRIVATE=0;
    public static final String USB_SERVICE="usb";
    private final android.content.res.Resources resources=new android.content.res.Resources();
    public android.content.res.Resources getResources() { return resources; }
    public String getString(int id) { return resources.getString(id); }
    public String getString(int id,Object...args) { return resources.getString(id,args); }
    public CharSequence getText(int id) { return resources.getText(id); }
    public Context getApplicationContext() { return this; }
    public String getPackageName() { return "org.firstinspires.ftcsim.jvm"; }
    public Object getSystemService(String name) { if(name.equals("uimode"))return new android.app.UiModeManager(); throw new UnsupportedOperationException("Android service: " + name); }
}
