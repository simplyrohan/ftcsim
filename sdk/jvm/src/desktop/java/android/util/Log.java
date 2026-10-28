package android.util;
public final class Log {
    public static final int VERBOSE=2, DEBUG=3, INFO=4, WARN=5, ERROR=6, ASSERT=7;
    public static int println(int level,String tag,String text) { if(level >= INFO || Boolean.getBoolean("ftcsim.verbose")) System.err.println(tag+": "+text); return text==null?0:text.length(); }
    public static boolean isLoggable(String tag,int level) { return level>=INFO; }
    public static String getStackTraceString(Throwable e) { java.io.StringWriter w=new java.io.StringWriter(); e.printStackTrace(new java.io.PrintWriter(w)); return w.toString(); }
    public static int v(String t,String m) { return println(VERBOSE,t,m); }
    public static int d(String t,String m) { return println(DEBUG,t,m); }
    public static int i(String t,String m) { return println(INFO,t,m); }
    public static int w(String t,String m) { return println(WARN,t,m); }
    public static int e(String t,String m) { return println(ERROR,t,m); }
    public static int v(String t,String m,Throwable e) { return v(t,m+"\n"+getStackTraceString(e)); }
    public static int d(String t,String m,Throwable e) { return d(t,m+"\n"+getStackTraceString(e)); }
    public static int i(String t,String m,Throwable e) { return i(t,m+"\n"+getStackTraceString(e)); }
    public static int w(String t,String m,Throwable e) { return w(t,m+"\n"+getStackTraceString(e)); }
    public static int e(String t,String m,Throwable e) { return e(t,m+"\n"+getStackTraceString(e)); }
}
