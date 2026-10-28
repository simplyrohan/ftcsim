package org.firstinspires.ftc.robotcore.internal.network;

import com.qualcomm.robotcore.exception.RobotCoreException;
import com.qualcomm.robotcore.robocol.Command;
import com.qualcomm.robotcore.robocol.RobocolParsable;

/** Optional desktop transport. A null transport retains upstream Android networking. */
public interface DriverStationTransport {
    void sendCommand(Command command);
    void sendData(RobocolParsable data) throws RobotCoreException;
}
