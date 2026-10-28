/*
 * Copyright (c) 2018 David Sargent
 *
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without modification,
 * are permitted (subject to the limitations in the disclaimer below) provided that
 * the following conditions are met:
 *
 * Redistributions of source code must retain the above copyright notice, this list
 * of conditions and the following disclaimer.
 *
 * Redistributions in binary form must reproduce the above copyright notice, this
 * list of conditions and the following disclaimer in the documentation and/or
 * other materials provided with the distribution.
 *
 * Neither the name of David Sargent nor the names of its contributors may be used to
 * endorse or promote products derived from this software without specific prior
 * written permission.
 *
 * NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE GRANTED BY THIS
 * LICENSE. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
 * THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
 * TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
 * THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

package org.firstinspires.ftc.onbotjava.handlers.file;

import com.android.tools.r8.I;
import com.qualcomm.robotcore.util.ReadWriteFile;
import com.qualcomm.robotcore.util.RobotLog;

import org.firstinspires.ftc.onbotjava.JavaSourceFile;
import org.firstinspires.ftc.onbotjava.OnBotJavaFileSystemUtils;
import org.firstinspires.ftc.onbotjava.OnBotJavaManager;
import org.firstinspires.ftc.onbotjava.OnBotJavaProgrammingMode;
import org.firstinspires.ftc.onbotjava.OnBotJavaSecurityManager;
import org.firstinspires.ftc.onbotjava.RegisterWebHandler;
import org.firstinspires.ftc.onbotjava.RequestConditions;
import org.firstinspires.ftc.onbotjava.StandardResponses;
import org.firstinspires.ftc.robotcore.internal.webserver.WebHandler;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

import fi.iki.elonen.NanoHTTPD;

@RegisterWebHandler(uri = OnBotJavaProgrammingMode.URI_FILE_RENAME)
public class RenameFile implements WebHandler {
    private final String TAG = RenameFile.class.getSimpleName();
    @Override
    public NanoHTTPD.Response getResponse(NanoHTTPD.IHTTPSession session) {
        if (!RequestConditions.containsParameters(session, RequestConditions.REQUEST_KEY_COPY_TO, RequestConditions.REQUEST_KEY_COPY_FROM)) {
            return StandardResponses.badRequest();
        }

        final String fromFileName = RequestConditions.dataForParameter(session, RequestConditions.REQUEST_KEY_COPY_FROM);
        final String destFileName = RequestConditions.dataForParameter(session, RequestConditions.REQUEST_KEY_COPY_TO);
        if (!OnBotJavaSecurityManager.isValidSourceFileOrFolder(fromFileName) ||
                !OnBotJavaSecurityManager.isValidSourceFileOrFolder(destFileName)) {
            return StandardResponses.badRequest();
        }

        File origin = new File(OnBotJavaManager.javaRoot, fromFileName);
        File dest = new File(OnBotJavaManager.javaRoot, destFileName);

        if (!Objects.equals(origin.getParent(), dest.getParent())) {
            return StandardResponses.badRequest("cannot rename file: parent directory must be the same");
        }

        try {
            renameFile(origin, dest);
        } catch (IOException ex) {
            RobotLog.ee(TAG, "cannot rename file", ex);
            return StandardResponses.serverError("cannot rename file");
        }

        return StandardResponses.successfulRequest();
    }

    /**
     * Copies the given source File to the given dest File.
     */
    private void renameFile(File source, File dest) throws IOException {
        // Checks if there's an existing file with the same name
        // Since Android uses a case-insensitive filesystem, we need to ignore the case
        // we rename with a different capitalization
        if (!dest.getName().equalsIgnoreCase(source.getName())) {
            dest = checkForSameNameConflicts(dest);
        }
        String tmpFileName = dest.getName() + ".tmp";
        File tmpFile = new File(dest.getParent(), tmpFileName);

        if (source.getPath().endsWith(OnBotJavaFileSystemUtils.EXT_JAVA_FILE)) {
            JavaSourceFile.forFile(source).copyTo(tmpFile);
            source.delete();
            // We need to delete the source file so we can rename the file without
            // weird collisions if the name is different in the case-alone
            if (!tmpFile.renameTo(dest)) {
                throw new IOException("failed to rename file");
            }
        } else {
            if (!source.renameTo(tmpFile)) {
                throw new IOException("failed to rename file");
            }
            if (!tmpFile.renameTo(dest)) {
                throw new IOException("failed to rename file");
            }
            // Force Android to access the length of the new file
            dest.length();
        }
    }

    private File checkForSameNameConflicts(File dest) {
        if (dest.exists()) {
            String originalName = dest.getName();
            String ext = "";
            if (originalName.contains(".")) {
                ext = originalName.substring(originalName.lastIndexOf('.'));
                originalName = originalName.substring(0, originalName.lastIndexOf('.'));
            }
            String suffix = "_Copy";
            if (originalName.endsWith(suffix)) {
                suffix = "";
            }
            dest = new File(dest.getParentFile(), originalName + suffix + ext);
            for (int i = 2; i < 1000 && dest.exists(); i++) {
                dest = new File(dest.getParentFile(), originalName + suffix + i + ext);
            }
        }
        return dest;
    }
}
