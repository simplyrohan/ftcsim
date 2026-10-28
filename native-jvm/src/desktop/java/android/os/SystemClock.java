package android.os;
public final class SystemClock {
    private static final long START = System.nanoTime();
    public static long elapsedRealtimeNanos() { return System.nanoTime() - START; }
    public static long elapsedRealtime() { return elapsedRealtimeNanos()/1000000; }
    public static long uptimeMillis() { return elapsedRealtime(); }
    public static long currentThreadTimeMillis() { return java.lang.management.ManagementFactory.getThreadMXBean().getCurrentThreadCpuTime()/1000000; }
    public static void sleep(long ms) { try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); } }
}
