package ftcsim.jvm;

import com.google.gson.*;
import fi.iki.elonen.NanoWSD;
import java.io.IOException;
import java.util.Set;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** HTTP/WS listener owned by the SDK, never proxied through the Python server. */
final class DriverStationServer extends NanoWSD {
    static final class Command {
        final Peer peer; final JsonObject data;
        Command(Peer peer, JsonObject data) { this.peer = peer; this.data = data; }
    }
    final BlockingQueue<Command> commands = new ArrayBlockingQueue<>(256);
    final AtomicBoolean disconnected = new AtomicBoolean();
    private final Set<Peer> peers = ConcurrentHashMap.newKeySet();
    private volatile Peer owner;
    private volatile String hello = "{}", state = "{}", telemetry = "{}";
    volatile long lastInput;
    private final int pagePort;
    DriverStationServer(int port, int pagePort) { super("127.0.0.1", port); this.pagePort = pagePort; }
    @Override public Response serve(IHTTPSession session) {
        if (isWebsocketRequested(session)) {
            if (!(session.getUri().equals("/ds") || session.getUri().equals("/")))
                return newFixedLengthResponse(Response.Status.NOT_FOUND, "text/plain", "Use /ds");
            String origin = session.getHeaders().get("origin");
            if (origin != null && !(origin.equals("http://localhost:" + pagePort) || origin.equals("http://127.0.0.1:" + pagePort)))
                return newFixedLengthResponse(Response.Status.FORBIDDEN, "text/plain", "Open the DS from the simulator origin");
        }
        return super.serve(session);
    }
    @Override protected Response serveHttp(IHTTPSession session) {
        return newFixedLengthResponse(Response.Status.OK, "application/json", "{\"service\":\"ftc-desktop-sdk\",\"version\":1,\"websocket\":\"/ds\"}");
    }
    @Override protected WebSocket openWebSocket(IHTTPSession session) { return new Peer(session); }
    void hello(JsonObject data) { hello = data.toString(); for (Peer p : peers) p.sendJson(hello); }
    void state(JsonObject data) { state = data.toString(); for (Peer p : peers) p.sendJson(state); }
    void telemetry(JsonObject data) { telemetry = data.toString(); for (Peer p : peers) p.sendJson(telemetry); }
    void event(JsonObject data) { for (Peer p : peers) p.sendJson(data.toString()); }
    boolean hasController() { return owner != null; }
    boolean isController(Peer peer) { return owner == peer; }
    void reply(Command c, boolean ok, String message) {
        JsonObject reply = new JsonObject(); reply.addProperty("type", ok ? "ack" : "error");
        if (c.data.has("id")) reply.add("id", c.data.get("id"));
        reply.addProperty("message", message); c.peer.sendJson(reply.toString());
    }
    final class Peer extends WebSocket {
        Peer(IHTTPSession session) { super(session); }
        @Override protected void onOpen() {
            peers.add(this);
            boolean controller;
            synchronized (DriverStationServer.this) {
                controller = owner == null;
                if (controller) { owner = this; lastInput = System.nanoTime(); }
            }
            sendJson("{\"type\":\"role\",\"controller\":" + controller + "}");
            sendJson(hello); sendJson(state); sendJson(telemetry);
        }
        @Override protected void onClose(WebSocketFrame.CloseCode code, String reason, boolean remote) {
            peers.remove(this);
            synchronized (DriverStationServer.this) {
                if (owner == this) { owner = null; disconnected.set(true); }
            }
        }
        @Override protected void onMessage(WebSocketFrame frame) {
            try {
                String text = frame.getTextPayload();
                if (text.length() > 65536) throw new IllegalArgumentException("Message exceeds 64 KiB");
                JsonObject data = new JsonParser().parse(text).getAsJsonObject();
                if (owner != this) throw new IllegalArgumentException("Observer connection; reconnect after controller disconnects");
                String type = data.get("type").getAsString();
                // Refresh on receipt so queued commands cannot inherit stale liveness.
                lastInput = System.nanoTime();
                if (type.equals("heartbeat")) return;
                if (!commands.offer(new Command(this, data))) throw new IllegalArgumentException("Control queue full");
            } catch (RuntimeException e) {
                JsonObject error = new JsonObject(); error.addProperty("type", "error"); error.addProperty("message", e.getMessage()); sendJson(error.toString());
            }
        }
        @Override protected void onPong(WebSocketFrame frame) { }
        @Override protected void onException(IOException error) { }
        synchronized void sendJson(String data) {
            try { if (isOpen()) send(data); } catch (IOException e) { onClose(WebSocketFrame.CloseCode.AbnormalClosure, e.toString(), false); }
        }
    }
}
