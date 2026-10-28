package android.os;
public final class Environment {
    public static java.io.File getExternalStorageDirectory() { return new java.io.File(System.getProperty("ftcsim.data", "build/ftcsim-data")); }
}
