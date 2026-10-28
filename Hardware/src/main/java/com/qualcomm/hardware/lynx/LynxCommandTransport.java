package com.qualcomm.hardware.lynx;

import com.qualcomm.hardware.lynx.commands.LynxMessage;

/** Optional synchronous command transport. Complete each respondable with an ACK, response or NACK. */
public interface LynxCommandTransport {
    void transmit(LynxMessage message) throws InterruptedException;
}
