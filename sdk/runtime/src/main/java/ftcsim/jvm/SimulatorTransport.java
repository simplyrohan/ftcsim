package ftcsim.jvm;

import com.google.gson.*;
import com.qualcomm.hardware.lynx.*;
import com.qualcomm.hardware.lynx.commands.*;
import com.qualcomm.hardware.lynx.commands.standard.*;
import java.net.URI;
import java.net.http.*;
import java.nio.ByteBuffer;
import java.time.Duration;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

/** One persistent WebSocket for all hubs, opened during desktop SDK bootstrap. */
public final class SimulatorTransport implements LynxCommandTransport, AutoCloseable, WebSocket.Listener {
    private static final int MAX_MESSAGE = 1024 * 1024;
    private final ConcurrentMap<Long, CompletableFuture<JsonObject>> pending = new ConcurrentHashMap<>();
    private final AtomicLong sequence = new AtomicLong();
    private final StringBuilder fragments = new StringBuilder();
    private final WebSocket socket;
    private volatile boolean connected;

    public SimulatorTransport(URI uri) throws Exception {
        if (!"ws".equals(uri.getScheme()) || !("localhost".equals(uri.getHost()) || "127.0.0.1".equals(uri.getHost())))
            throw new IllegalArgumentException("Simulator must be a loopback ws:// endpoint");
        socket = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build()
                .newWebSocketBuilder().connectTimeout(Duration.ofSeconds(3)).buildAsync(uri, this).get(4, TimeUnit.SECONDS);
    }
    @Override public void onOpen(WebSocket ws) { connected = true; ws.request(1); }
    @Override public CompletionStage<?> onText(WebSocket ws, CharSequence data, boolean last) {
        try {
            if (fragments.length() + data.length() > MAX_MESSAGE) throw new IllegalArgumentException("Oversized simulator message");
            fragments.append(data);
            if (last) {
                JsonObject reply = new JsonParser().parse(fragments.toString()).getAsJsonObject();
                fragments.setLength(0);
                CompletableFuture<JsonObject> waiting = pending.remove(reply.get("id").getAsLong());
                if (waiting != null) waiting.complete(reply);
            }
        } catch (RuntimeException failure) { fail(failure); ws.abort(); }
        ws.request(1);
        return null;
    }
    @Override public CompletionStage<?> onPing(WebSocket ws, ByteBuffer data) {
        ws.request(1); return ws.sendPong(data);
    }
    @Override public CompletionStage<?> onPong(WebSocket ws, ByteBuffer data) { ws.request(1); return null; }
    @Override public CompletionStage<?> onClose(WebSocket ws, int status, String reason) {
        fail(new IllegalStateException("Simulator disconnected: " + reason)); return null;
    }
    @Override public void onError(WebSocket ws, Throwable error) { fail(error); }
    private void fail(Throwable error) {
        connected = false;
        pending.forEach((id, future) -> future.completeExceptionally(error));
        pending.clear();
    }
    @Override public void transmit(LynxMessage message) throws InterruptedException {
        if (!(message instanceof LynxRespondable)) throw new IllegalArgumentException("Expected a respondable Lynx command");
        LynxRespondable<?> command = (LynxRespondable<?>) message;
        if (!connected) throw new IllegalStateException("Simulator WebSocket is disconnected");
        long id = sequence.incrementAndGet();
        CompletableFuture<JsonObject> waiting = new CompletableFuture<>();
        pending.put(id, waiting);
        try {
            JsonObject request = new JsonObject();
            request.addProperty("version", 1); request.addProperty("type", "lynx"); request.addProperty("id", id);
            request.addProperty("module", command.getModuleAddress()); request.addProperty("command", command.getClass().getName());
            request.addProperty("payload", hex(command.toPayloadByteArray())); request.addProperty("response", command.getExpectedResponseClassName());
            // JDK WebSocket permits one outstanding text send. Responses remain correlated by id.
            synchronized (socket) { socket.sendText(request.toString(), true).get(3, TimeUnit.SECONDS); }
            JsonObject reply = waiting.get(3, TimeUnit.SECONDS);
            String status = reply.get("status").getAsString();
            if (status.equals("nack")) command.onNackReceived(new LynxNack(command.getModule(), reply.get("reason").getAsInt()));
            else if (status.equals("response") && command.isResponseExpected()) command.onRemotePayloadReceived(unhex(reply.get("payload").getAsString()));
            else if (status.equals("ack") && !command.isResponseExpected()) command.onAckReceived(new LynxAck(command.getModule()));
            else throw new IllegalStateException("Unexpected Lynx reply: " + reply);
        } catch (ExecutionException | TimeoutException | RuntimeException failure) {
            close();
            throw new IllegalStateException("Lynx WebSocket exchange failed for " + command.getClass().getSimpleName(), failure);
        } finally { pending.remove(id); }
    }
    public boolean isConnected() { return connected; }
    @Override public void close() {
        fail(new IllegalStateException("Simulator transport closed"));
        socket.abort();
    }
    private static String hex(byte[] bytes) {
        StringBuilder out = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) out.append(String.format("%02x", b & 255));
        return out.toString();
    }
    private static byte[] unhex(String text) {
        if ((text.length() & 1) != 0) throw new IllegalArgumentException("Odd payload length");
        byte[] out = new byte[text.length() / 2];
        for (int i = 0; i < out.length; i++) {
            int high = Character.digit(text.charAt(2*i), 16), low = Character.digit(text.charAt(2*i+1), 16);
            if (high < 0 || low < 0) throw new IllegalArgumentException("Invalid hex payload");
            out[i] = (byte)((high << 4) | low);
        }
        return out;
    }
}
