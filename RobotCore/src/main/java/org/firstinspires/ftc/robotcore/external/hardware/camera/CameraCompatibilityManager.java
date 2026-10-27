/*
Copyright (c) 2026 FIRST

All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted (subject to the limitations in the disclaimer below) provided that
the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list
of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this
list of conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.

Neither the name of Robert Atkinson nor the names of his contributors may be used to
endorse or promote products derived from this software without specific prior
written permission.

NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE GRANTED BY THIS
LICENSE. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

package org.firstinspires.ftc.robotcore.external.hardware.camera;

import org.firstinspires.ftc.robotcore.internal.camera.CameraCompatibilityManagerImpl;

import java.util.List;

public abstract class CameraCompatibilityManager
{
    public enum Quirk
    {
        /* To quote saki:
         *      "libusb_release_interface *should* reset the alternate setting to the first available,
         *       but sometimes (e.g. on Darwin) it doesn't. Thus, we do it explicitly here.
         *       This is needed to de-initialize certain cameras.
         *
         *       XXX but resetting the alt setting here many times leads trouble
         *       on GT-N7100(international Galaxy Note2 at lease with Android4.4.2)
         *       so we add flag to avoid the issue
         */
        RESET_ALT_SETTING_ON_RELEASE(1 << 0),

        /** Some cameras just take too very long to have a USB reset thrown their way (like, seconds) */
        AVOID_LIB_USB_RESET_DEVICE  (1 << 1);

        public final int bitmask;

        Quirk(int bitmask)
        {
            this.bitmask = bitmask;
        }
    }

    /**
     * Notes a quirk for a particular camera model
     * @param vid the USB vendor ID of the camera
     * @param pid the USB product ID of the camera
     * @param quirk the quirk to add
     */
    public abstract void addQuirk(int vid, int pid, Quirk quirk);

    /**
     * Forgets about a previously added quirk for a particular camera model
     * @param vid the USB vendor ID of the camera
     * @param pid the USB product ID of the camera
     * @param quirk the quirk to forget about
     */
    public abstract void removeQuirk(int vid, int pid, Quirk quirk);

    /**
     * Gets the list of quirks for a given camera
     * @param vid the USB vendor ID of the camera
     * @param pid the USB product ID of the camera
     * @return list of quirks
     */
    public abstract List<Quirk> getQuirks(int vid, int pid);

    private static final CameraCompatibilityManager INSTANCE = new CameraCompatibilityManagerImpl();

    public static CameraCompatibilityManager getInstance()
    {
        return INSTANCE;
    }
}
