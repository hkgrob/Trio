# Smart Watch

## Apple Watch

On an Apple Watch, you can add carbs and boluses, set a temporary target, and display BG, IOB, COB, etc.

Trio has a companion app for the Apple Watch.  
The companion app shows the loop status and current insulin and carbs onboard. 
It also lets you add carbs, do a manual bolus, and set a temporary target.
However, the companion app only serves as a remote control for the iPhone app; connection to the CGM and pump is still done through your iPhone, and you will have to bring it with you.

Apple Watch Series 3 and newer are supported.  
Newer versions of the Apple Watch have better battery life and support an always-on display.

### Confirm Bolus Faster
<!-- TODO: Add description of confirm bolus faster -->

### Contacts Configuration
<!-- TODO: Add contacts configuration instructions -->

- - -

## Garmin

Garmin watches only display data and do not allow interaction for adding carbs or insulin. Two components can be installed on Garmin watches: a watch face that continuously displays information, and a data field that shows glucose information during activities.
Both components are independent of each other and need to be sideloaded onto the watch as described below. 
No need for Garmin Connect in the background — the watch just needs to be connected to the phone that runs Trio.
The watch face updates with Trio loop cycles.

### Releases
The sideloading instructions below are retained from the upstream guide. Current Connect IQ distribution and model support were not verified in this code-alignment review; check the relevant project release before choosing an installation method.

### How to do it
1. Choose a folder on your Mac and get the latest release from [this GitHub repo](https://github.com/mountrcg/garminWatch).
2. You need `*.prg` files for your watch model from the release and OpenMTP from [OpenMTP](https://openmtp.ganeshrvel.com) to transfer them to the watch.
3. Install and start OpenMTP.
4. Connect your Garmin watch via a data USB cable to the MacBook and allow the USB connection. The Garmin watch USB mode should be set to MTP.
5. Transfer `*.prg` files for your watch model to the `/GARMIN/APPS` folder.
6. Wait for the transfer to finish and disconnect the watch.
7. Add the Garmin watch in Trio settings: `Settings -> Watch -> Garmin Watch -> Add Devices`.
8. Choose the Trio watch face on the watch and enjoy.

### Hints
The watch face will not display information after another has been used. In that case, you have to uninstall the Trio watch face and reinstall it. No similar side effects occur with the data field.

If your watch is not listed in the Release section, please ask about it in the Garmin channel on Discord.

- - -


## Garmin configuration in Trio 1.0.2

After adding the device, configure the supported **watchface** and **datafield** independently in Trio. The available watchface choices include a Complication mode for compatible faces with Connect IQ complication slots. Configure primary/secondary attribute choices as appropriate for the selected integration.

Changing the selected watchface in Trio automatically disables watchface data transmission. Follow the displayed sequence: choose the configuration in Trio, change the face on the watch, then resume transmission when prompted. The **Disable watchface data transmission** control is inverted relative to the internal `isWatchfaceDataEnabled` value: turning Disable on makes the internal enabled flag false.

This describes the verified configuration controls and transition behavior. It does not confirm every watch model, current app-store listing or connection state. Existing screenshots may predate these controls.


## 1.0.2 source references

- **F09 — Garmin guide omits configuration choices and transmission reset behavior**
    - [Trio/Sources/Modules/WatchConfig/View/WatchConfigGarminAppConfigView.swift:18](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Modules/WatchConfig/View/WatchConfigGarminAppConfigView.swift#L18)
    - [Trio/Sources/Models/GarminWatchSettings.swift:54](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Models/GarminWatchSettings.swift#L54)
