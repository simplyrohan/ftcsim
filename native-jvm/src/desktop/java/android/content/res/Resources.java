package android.content.res;
/** Headless string resources only. Android layouts/drawables are not desktop UI. */
public class Resources {
    public static class NotFoundException extends RuntimeException { public NotFoundException(String message) { super(message); } }
    public String getString(int id) { return ftcsim.jvm.ResourceStrings.get(id); }
    public String getString(int id,Object... args) { return String.format(java.util.Locale.ROOT,getString(id),args); }
    public CharSequence getText(int id) { return getString(id); }
    public int getIdentifier(String name, String type, String packageName) {
        try { return Class.forName("com.qualcomm.robotcore.R$" + type).getField(name).getInt(null); }
        catch (ReflectiveOperationException e) { return 0; }
    }
    public String[] getStringArray(int id) { throw new UnsupportedOperationException("Array resource " + id); }
}
