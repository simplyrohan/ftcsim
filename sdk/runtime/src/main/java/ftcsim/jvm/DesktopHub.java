package ftcsim.jvm;

import com.qualcomm.hardware.lynx.*;
import com.qualcomm.hardware.lynx.commands.*;
import com.qualcomm.hardware.lynx.commands.core.*;
import com.qualcomm.robotcore.hardware.usb.RobotUsbModule;
import com.qualcomm.robotcore.util.SerialNumber;
import java.lang.reflect.Proxy;
import java.util.concurrent.locks.ReentrantLock;


/** A real SDK LynxModule with a desktop endpoint instead of USB/FTDI discovery. */
public final class DesktopHub extends LynxModule implements AutoCloseable {
    private final SimulatorTransport transport;
    public DesktopHub(SimulatorTransport transport, int address) {
        super(endpoint(), validate(address), true, true);
        this.transport = transport;
        setCommandTransport(transport);
    }
    private static int validate(int address) {
        if (address < 1 || address > 254) throw new IllegalArgumentException("Module address must be 1..254");
        return address;
    }
    private static LynxUsbDevice endpoint() {
        ReentrantLock lock = new ReentrantLock(true);
        SerialNumber serial = SerialNumber.fromString("FTCSIM-WS");
        return (LynxUsbDevice) Proxy.newProxyInstance(DesktopHub.class.getClassLoader(), new Class<?>[]{LynxUsbDevice.class}, (proxy, method, args) -> {
            switch (method.getName()) {
                case "getSerialNumber": return serial;
                case "getArmingState": return RobotUsbModule.ARMINGSTATE.ARMED;
                case "isArmed": case "isEngaged": return true;
                case "isPretending": case "isSystemSynthetic": return false;
                case "acquireNetworkTransmissionLock": lock.lockInterruptibly(); return null;
                case "releaseNetworkTransmissionLock": lock.unlock(); return null;
                case "registerCallback": case "unregisterCallback": case "removeConfiguredModule": case "close": return null;
                case "getConnectionInfo": return "Shared simulator WebSocket";
                case "toString": return "FTCSIM-WS";
                case "hashCode": return System.identityHashCode(proxy);
                case "equals": return proxy == args[0];
                default: throw new UnsupportedOperationException("Desktop Lynx endpoint: " + method.getName());
            }
        });
    }
    @Override protected void startExecutor() { /* WebSocket exchanges complete command latches; no Android background services. */ }
    @Override protected void stopExecutor() { }
    @Override public void resetPingTimer(LynxMessage message) { }
    @Override public boolean isCommandSupported(Class<? extends LynxCommand> command) {
        // DEKA classes are routed by class name, so interface-number negotiation is unnecessary.
        return LynxDekaInterfaceCommand.class.isAssignableFrom(command) || super.isCommandSupported(command);
    }
    public boolean isTransportConnected() { return transport.isConnected(); }
    // The SDK owns the shared socket; closing one hub must not close other hubs.
    @Override public void close() { if (transport.isConnected()) super.close(); }
}
