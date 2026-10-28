package ftcsim.jvm;
import com.google.gson.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;

public final class SimulatorLink {
    public static String base;
    public static JsonObject control = new JsonObject();
    public static JsonObject exchange(String path, JsonObject body) throws IOException {
        HttpURLConnection connection = (HttpURLConnection)new URL(base+path).openConnection();
        connection.setConnectTimeout(1500); connection.setReadTimeout(1500);
        try {
            if (body != null) {
                connection.setRequestMethod("POST"); connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json");
                try(OutputStream out=connection.getOutputStream()) { out.write(body.toString().getBytes(StandardCharsets.UTF_8)); }
            }
            try(Reader reader=new InputStreamReader(connection.getInputStream(),StandardCharsets.UTF_8)) {
                return new JsonParser().parse(reader).getAsJsonObject();
            }
        } finally { connection.disconnect(); }
    }
}
