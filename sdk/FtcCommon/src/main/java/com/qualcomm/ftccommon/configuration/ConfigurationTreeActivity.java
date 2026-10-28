/*
Copyright (c) 2026 Miriam Sinton-Remes

All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted (subject to the limitations in the disclaimer below) provided that
the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list
of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this
list of conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.

Neither the name of Miriam Sinton-Remes nor the names of her contributors may be
used to endorse or promote products derived from this software without specific
prior written permission.

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

package com.qualcomm.ftccommon.configuration;

import android.os.Bundle;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.annotation.NonNull;

import com.qualcomm.ftccommon.R;
import com.qualcomm.robotcore.exception.RobotCoreException;
import com.qualcomm.robotcore.hardware.configuration.ControllerConfiguration;
import com.qualcomm.robotcore.hardware.configuration.DeviceConfiguration;
import com.qualcomm.robotcore.hardware.configuration.LynxI2cDeviceConfiguration;
import com.qualcomm.robotcore.hardware.configuration.LynxModuleConfiguration;
import com.qualcomm.robotcore.hardware.configuration.ServoHubConfiguration;
import com.qualcomm.robotcore.hardware.configuration.ReadXMLFileHandler;
import com.qualcomm.robotcore.robocol.Command;
import com.qualcomm.robotcore.util.RobotLog;
import com.qualcomm.robotcore.util.ThreadPool;

import org.firstinspires.ftc.robotcore.internal.network.CallbackResult;
import org.firstinspires.ftc.robotcore.internal.network.NetworkConnectionHandler;
import org.firstinspires.ftc.robotcore.internal.network.RecvLoopRunnable;
import org.firstinspires.ftc.robotcore.internal.network.RobotCoreCommandList;
import org.firstinspires.ftc.robotcore.internal.system.AppUtil;
import org.xmlpull.v1.XmlPullParser;
import org.xmlpull.v1.XmlPullParserException;

import java.io.FileNotFoundException;
import java.io.StringReader;
import java.text.Collator;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class ConfigurationTreeActivity extends EditActivity {
    public static final RequestCode requestCode = RequestCode.VIEW_CONFIG_TREE;

    public static final String TAG = "ConfigurationTree";
    @Override public String getTag() {
        return TAG;
    }
    @Override protected FrameLayout getBackBar() {
        return findViewById(R.id.backbar);
    }

    protected final NetworkConnectionHandler networkConnectionHandler = NetworkConnectionHandler.getInstance();
    protected final RecvLoopRunnable.RecvLoopCallback commandCallback = new CommandCallback();
    protected LinearLayout treeContainer;
    protected TextView caption;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.config_tree);

        EditParameters<DeviceConfiguration> parameters = EditParameters.fromIntent(this, getIntent());
        deserialize(parameters);

        treeContainer = findViewById(R.id.config_tree_layout);
        caption = findViewById(R.id.config_tree_caption);
        updateCaption();
    }

    @Override
    protected void onStart() {
        super.onStart();

        if (remoteConfigure) {
            networkConnectionHandler.pushReceiveLoopCallback(commandCallback);
        }

        loadTree();
    }

    @Override
    protected void onStop() {
        super.onStop();
        if (remoteConfigure) {
            networkConnectionHandler.removeReceiveLoopCallback(commandCallback);
        }
    }

    @Override
    public void onBackPressed() {
        finishOk();
    }

    protected void loadTree() {
        treeContainer.removeAllViews();

        if (haveRobotConfigMapParameter) {
            populateTree(getRobotConfigMap());
            return;
        }

        if (currentCfgFile.isNoConfig()) {
            addTreeRow(0, "No configuration data available.");
            return;
        }

        if (remoteConfigure) {
            networkConnectionHandler.sendCommand(new Command(RobotCoreCommandList.CMD_REQUEST_PARTICULAR_CONFIGURATION, currentCfgFile.toString()));
            return;
        }

        ThreadPool.getDefault().execute(() -> {
            try {
                final RobotConfigMap robotConfigMap = buildRobotConfigMap(currentCfgFile.getXml());
                AppUtil.getInstance().runOnUiThread(() -> {
                    ConfigurationTreeActivity.this.robotConfigMap = robotConfigMap;
                    populateTree(robotConfigMap);
                });
            } catch (final FileNotFoundException | RobotCoreException | XmlPullParserException e) {
                RobotLog.ee(TAG, e, "unable to load configuration tree");
                AppUtil.getInstance().runOnUiThread(() -> addTreeRow(0, "No configuration data available."));
            }
        });
    }

    protected void populateTree(RobotConfigMap robotConfigMap) {
        treeContainer.removeAllViews();

        if (robotConfigMap == null || robotConfigMap.size() == 0) {
            addTreeRow(0, "No configuration data available.");
            return;
        }

        List<ControllerConfiguration> controllers = new ArrayList<>(robotConfigMap.controllerConfigurations());
        sortControllers(controllers);
        for (ControllerConfiguration<?> controller : controllers) {
            renderController(controller, 0);
        }
    }

    protected void updateCaption() {
        caption.setText(getString(R.string.config_tree_caption) + " " + currentCfgFile.getName());
    }

    protected RobotConfigMap buildRobotConfigMap(XmlPullParser xmlPullParser) throws RobotCoreException, XmlPullParserException {
        ReadXMLFileHandler readXMLFileHandler = new ReadXMLFileHandler();
        List<ControllerConfiguration> controllerList = readXMLFileHandler.parse(xmlPullParser);
        return new RobotConfigMap(controllerList);
    }

    protected void renderController(@NonNull ControllerConfiguration<?> controller, int depth) {
        addTreeRow(depth, controller.getName());

        if (controller instanceof LynxModuleConfiguration) {
            renderLynxModule((LynxModuleConfiguration)controller, depth + 1);
        } else if (controller instanceof ServoHubConfiguration) {
            renderDeviceCategory(depth + 1, "Servos", ((ServoHubConfiguration)controller).getServos());
        } else {
            List<DeviceConfiguration> children = new ArrayList<>(controller.getDevices());
            Collections.sort(children);
            for (DeviceConfiguration child : children) {
                if (child instanceof ControllerConfiguration<?>) {
                    renderController((ControllerConfiguration<?>)child, depth + 1);
                } else {
                    addTreeRow(depth + 1, formatPortDevice(child));
                }
            }
        }
    }

    protected void renderLynxModule(@NonNull LynxModuleConfiguration module, int depth) {
        renderDeviceCategory(depth, "Motors", module.getMotors());
        renderDeviceCategory(depth, "Servos", module.getServos());
        renderDeviceCategory(depth, "Digital Devices", module.getDigitalDevices());
        renderDeviceCategory(depth, "Analog Input Devices", module.getAnalogInputs());
        for (int bus = 0; bus < 4; bus++) {
            List<LynxI2cDeviceConfiguration> devices = module.getI2cDevices(bus);
            if (!devices.isEmpty()) {
                renderDeviceCategory(depth, "I2C Bus " + bus, new ArrayList<DeviceConfiguration>(devices));
            }
        }
    }

    protected void renderDeviceCategory(int depth, String title, List<? extends DeviceConfiguration> devices) {
        List<DeviceConfiguration> enabledDevices = new ArrayList<>();
        for (DeviceConfiguration device : devices) {
            if (device != null && device.isEnabled()) {
                enabledDevices.add(device);
            }
        }

        if (enabledDevices.isEmpty()) {
            return;
        }

        Collections.sort(enabledDevices);
        addTreeRow(depth, title);
        for (DeviceConfiguration device : enabledDevices) {
            addTreeRow(depth + 1, formatPortDevice(device));
        }
    }

    protected void sortControllers(List<ControllerConfiguration> controllers) {
        final Collator collator = Collator.getInstance();
        collator.setStrength(Collator.PRIMARY);
        controllers.sort((lhs, rhs) -> collator.compare(lhs.getName(), rhs.getName()));
    }

    protected String formatPortDevice(@NonNull DeviceConfiguration device) {
        String name = device.getName();
        StringBuilder builder = new StringBuilder();
        builder.append("port ");
        builder.append(device.getPort());
        if (name != null && !name.isEmpty()) {
            builder.append(": ");
            builder.append(name);
        }
        builder.append(" (");
        builder.append(device.getConfigurationType().getName());
        builder.append(")");
        return builder.toString();
    }

    protected void addTreeRow(int depth, String text) {
        TextView row = new TextView(this);
        row.setText(text);
        row.setTextSize(14);
        row.setPadding(dp(depth * 18), dp(2), dp(2), dp(2));
        treeContainer.addView(row);
    }

    protected int dp(int value) {
        float density = getResources().getDisplayMetrics().density;
        return Math.round(value * density);
    }

    protected CallbackResult handleCommandRequestParticularConfigurationResp(String extra) throws RobotCoreException {
        ReadXMLFileHandler readXMLFileHandler = new ReadXMLFileHandler();
        final RobotConfigMap robotConfigMap = new RobotConfigMap(readXMLFileHandler.parse(new StringReader(extra)));
        AppUtil.getInstance().runOnUiThread(() -> {
            ConfigurationTreeActivity.this.robotConfigMap = robotConfigMap;
            populateTree(robotConfigMap);
        });
        return CallbackResult.HANDLED;
    }

    protected class CommandCallback extends RecvLoopRunnable.DegenerateCallback {
        @Override public CallbackResult commandEvent(Command command) throws RobotCoreException {
            CallbackResult result = CallbackResult.NOT_HANDLED;
            try {
                if (command.getName().equals(RobotCoreCommandList.CMD_REQUEST_PARTICULAR_CONFIGURATION_RESP)) {
                    result = handleCommandRequestParticularConfigurationResp(command.getExtra());
                }
            } catch (RobotCoreException e) {
                RobotLog.ee(TAG, e, "unable to render configuration tree");
            }
            return result;
        }
    }
}
