package android.os;
public final class Process {
    public static int myTid() { return (int)Thread.currentThread().getId(); }
    public static int myPid() { return 0; }
    public static void setThreadPriority(int priority) { }
}
