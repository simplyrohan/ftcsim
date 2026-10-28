package ftcsim.jvm;

import com.google.gson.*;
import com.qualcomm.hardware.lynx.*;
import com.qualcomm.hardware.lynx.commands.*;
import com.qualcomm.hardware.lynx.commands.standard.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;

/** Length-prefixed UTF-8 JSON over loopback. No Android or hub native libraries are used. */
public final class TcpLynxTransport implements LynxCommandTransport, AutoCloseable {
    private static final int MAX_FRAME = 1024 * 1024;
    private final Socket socket;
    private final DataInputStream input;
    private final DataOutputStream output;
    private long sequence;
    public TcpLynxTransport(int port) throws IOException { this(port, 3000); }
    public TcpLynxTransport(int port, int timeoutMs) throws IOException {
        socket = new Socket();
        try {
            socket.connect(new InetSocketAddress("127.0.0.1", port), timeoutMs);
            socket.setSoTimeout(timeoutMs);
            socket.setTcpNoDelay(true);
            input = new DataInputStream(socket.getInputStream());
            output = new DataOutputStream(socket.getOutputStream());
        } catch (IOException e) { socket.close(); throw e; }
    }
    @Override public synchronized void transmit(LynxMessage message) throws InterruptedException {
        if (Thread.currentThread().isInterrupted()) throw new InterruptedException();
        if (!(message instanceof LynxRespondable)) throw new IllegalArgumentException("Expected a respondable command");
        LynxRespondable<?> command = (LynxRespondable<?>) message;
        try {
            long id = ++sequence;
            JsonObject request = new JsonObject();
            request.addProperty("version", 1);
            request.addProperty("id", id);
            request.addProperty("module", command.getModuleAddress());
            request.addProperty("command", command.getClass().getName());
            request.addProperty("payload", hex(command.toPayloadByteArray()));
            request.addProperty("response", command.getExpectedResponseClassName());
            byte[] bytes = request.toString().getBytes(StandardCharsets.UTF_8);
            if (bytes.length > MAX_FRAME) throw new IOException("Request too large");
            output.writeInt(bytes.length); output.write(bytes); output.flush();
            int count = input.readInt();
            if (count < 1 || count > MAX_FRAME) throw new IOException("Invalid response frame length: " + count);
            bytes = new byte[count]; input.readFully(bytes);
            JsonObject reply = new JsonParser().parse(new String(bytes, StandardCharsets.UTF_8)).getAsJsonObject();
            if (reply.get("id").getAsLong() != id) throw new IOException("Response ID mismatch");
            String status = reply.get("status").getAsString();
            if (status.equals("nack")) {
                command.onNackReceived(new LynxNack(command.getModule(), reply.get("reason").getAsInt()));
            } else if (status.equals("response") && command.isResponseExpected()) {
                command.onRemotePayloadReceived(unhex(reply.get("payload").getAsString()));
            } else if (status.equals("ack") && !command.isResponseExpected()) {
                command.onAckReceived(new LynxAck(command.getModule()));
            } else { throw new IOException("Unexpected response status: " + status); }
        } catch (IOException | RuntimeException e) {
            try { close(); } catch (IOException ignored) { }
            throw new IllegalStateException("Lynx TCP exchange failed for " + command.getClass().getSimpleName(), e);
        }
    }
    private static String hex(byte[] bytes) {
        StringBuilder text = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) text.append(String.format("%02x", b & 255));
        return text.toString();
    }
    private static byte[] unhex(String text) throws IOException {
        if ((text.length() & 1) != 0) throw new IOException("Odd hex payload length");
        byte[] bytes = new byte[text.length() / 2];
        for (int i = 0; i < bytes.length; i++) {
            int hi = Character.digit(text.charAt(i*2), 16), lo = Character.digit(text.charAt(i*2+1),16);
            if (hi < 0 || lo < 0) throw new IOException("Invalid hex payload");
            bytes[i] = (byte) ((hi << 4) | lo);
        }
        return bytes;
    }
    @Override public synchronized void close() throws IOException { socket.close(); }
}
