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
package org.firstinspires.ftc.robotcore.internal.camera;

import org.firstinspires.ftc.robotcore.external.hardware.camera.CameraCompatibilityManager;
import org.firstinspires.ftc.robotcore.internal.ftdi.VendorAndProductIds;
import org.firstinspires.ftc.robotcore.internal.usb.UsbConstants;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

public class CameraCompatibilityManagerImpl extends CameraCompatibilityManager
{
    protected HashMap<VendorAndProductIds, ArrayList<Quirk>> map = new HashMap<>();

    public CameraCompatibilityManagerImpl()
    {
        // unclear if this helps
        addQuirk(UsbConstants.VENDOR_ID_LOGITECH, UsbConstants.PRODUCT_ID_LOGITECH_C270, Quirk.RESET_ALT_SETTING_ON_RELEASE);

        addQuirk(UsbConstants.VENDOR_ID_ARDUCAM, UsbConstants.PRODUCT_ID_ARDUCAM_OV9281, Quirk.AVOID_LIB_USB_RESET_DEVICE);
        addQuirk(UsbConstants.VENDOR_ID_MICROSOFT, UsbConstants.PRODUCT_ID_MICROSOFT_LIFECAM_HD_3000, Quirk.AVOID_LIB_USB_RESET_DEVICE); // takes six seconds
        addQuirk(UsbConstants.VENDOR_ID_MICROSOFT, UsbConstants.PRODUCT_ID_MICROSOFT_LIFECAM_HD_5000, Quirk.AVOID_LIB_USB_RESET_DEVICE); // takes many seconds
        addQuirk(UsbConstants.VENDOR_ID_MICROSOFT, UsbConstants.PRODUCT_ID_MICROSOFT_LIFECAM_STUDIO, Quirk.AVOID_LIB_USB_RESET_DEVICE); // takes many seconds
        addQuirk(UsbConstants.VENDOR_ID_AUSDOM, UsbConstants.PRODUCT_ID_AUSDOM_AW615, Quirk.AVOID_LIB_USB_RESET_DEVICE); // takes many seconds
    }

    public void addQuirk(int vid, int pid, Quirk quirk)
    {
        VendorAndProductIds key = new VendorAndProductIds(vid, pid);
        ArrayList<Quirk> quirks = map.computeIfAbsent(key, k -> new ArrayList<>());

        if (!quirks.contains(quirk))
        {
            quirks.add(quirk);
        }
    }

    public void removeQuirk(int vid, int pid, Quirk quirk)
    {
        ArrayList<Quirk> quirks = map.get(new VendorAndProductIds(vid, pid));
        if (quirks != null)
        {
            quirks.remove(quirk);
        }
    }

    public List<Quirk> getQuirks(int vid, int pid)
    {
        return map.getOrDefault(new VendorAndProductIds(vid, pid), new ArrayList<Quirk>());
    }
}
