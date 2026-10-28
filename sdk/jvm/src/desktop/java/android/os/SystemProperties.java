package android.os;
public final class SystemProperties {
    public static void set(String key,String value) { System.setProperty(key,value); }
    public static String get(String key) { return System.getProperty(key, ""); }
    public static String get(String key,String fallback) { return System.getProperty(key,fallback); }
    public static boolean getBoolean(String key,boolean fallback) { String value=System.getProperty(key);return value==null?fallback:Boolean.parseBoolean(value); }
    public static int getInt(String key,int fallback) { try{return Integer.parseInt(get(key));}catch(NumberFormatException e){return fallback;} }
    public static long getLong(String key,long fallback) { try{return Long.parseLong(get(key));}catch(NumberFormatException e){return fallback;} }
}
