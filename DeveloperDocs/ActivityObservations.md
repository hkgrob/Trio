# Activity observations and workout presets

Open **Settings → Services → Apple Health → Activity observations**.

## Passive observation

Collection is off by default and independent of the existing Apple Health write integration. Enabling it requests heart-rate read permission and starts iPhone motion/step collection, subject to Motion & Fitness permission and hardware availability. No workout needs to be started.

Heart rate comes from authorized samples in the iPhone Health store, including Apple Watch samples after synchronization. This implementation does not start a Watch workout or directly stream the Watch sensor. It records the source, measurement timestamps, and the time Trio receives each sample, so end-to-end availability delays can be measured. This includes both synchronization and app execution delays; it does not isolate them. HealthKit does not disclose whether read permission was denied; no readings must not be interpreted as proof that permission was granted or that activity is absent.

iPhone activity classifications include motion confidence. Step readings are cumulative from the current pedometer session's start, not additive deltas. The phone must be carried to represent the wearer's movement. Motion callbacks pause when iOS suspends Trio. Collection resumes using existing app execution opportunities and HealthKit background delivery; neither guarantees immediate updates or continuous execution. Force-quitting Trio can interrupt collection.

The history retains at most 20,000 observations from the preceding seven days. It is saved locally with file protection; it may be included in device backups. CSV export includes timestamps and sources. Turning collection off retains history; clearing history also stops collection. No activity observations are uploaded to Nightscout. There are no passive activity thresholds, exercise/glucose predictions, preset changes, or activity-detection alerts in this version.

## Explicit Apple Watch workout starts

Workout activation is a separate opt-in, off by default. Select one existing user-created override **or** temporary-target preset, then enable **Allow workout preset activation**. Changing the selection disables activation until explicitly re-enabled.

In the iPhone **Shortcuts** app:

1. Create a personal automation with the **Apple Watch Workout** trigger.
2. Select **Starts**, the desired workout types, and **Run Immediately**.
3. Add Trio's **Activate workout preset** action.

The action is intentionally parameterless: it uses Trio's configured activity preset. Configure the trigger carefully: manually running this action also requests activation. Trio does not claim to independently verify the source of an invocation. There is no generic live HealthKit observer for the start of another app's workout; observing a saved workout would be too late for this purpose.

Activation uses the existing adjustment manager and its serialized transaction. If **any** override or temporary-target row is enabled, it skips activation, without restarting, replacing, or cancelling the existing adjustment. This check conservatively includes enabled rows awaiting expiry cleanup. Only saved presets are eligible. The selected preset's current settings and saved duration apply, including indefinite duration. Workout end does not cancel the preset. Multiple simultaneous workout invocations cannot enable both adjustment types.

Trio records the last result and requests a normal local notification for successful, skipped, or failed activation attempts while this option is enabled. Notification presentation depends on permission and system settings. The action never sends pump commands directly or changes the dosing algorithm. As with manual preset activation, the preset affects subsequent dosing through the existing pipeline.

Successful starts use Trio's existing Nightscout upload settings. Configure **Override Start** or **Temp Target Start** alarms in a compatible LoopFollow version for parent alerts. Those alerts depend on connectivity and follower updates, and do not specifically distinguish workout automation from manual starts.

## Validation

History tests cover arrival-time preservation, late arrival ordering, deletion, retention/count limits, invalid samples, CSV escaping, persistence, and default-disabled configuration. Adjustment tests cover both directions of active-adjustment preservation, normal starts, duplicate/concurrent starts, and rejecting non-presets.

Before relying on the feature, verify on a physical phone/Watch pair:

1. Deny and grant Health/Motion permissions; verify that missing data is not shown as inactivity.
2. Collect with the phone carried and left stationary, screen off, and Trio backgrounded. Compare measurement and arrival timestamps.
3. Turn collection off and clear history; verify that in-flight callbacks do not resume collection.
4. Start an Apple Workout with the personal automation enabled, including with the iPhone locked. Check the selected preset, saved duration, local result, and notification.
5. Repeat with an existing override and an existing temporary target. Both must remain unchanged.
6. Check Nightscout and LoopFollow with uploads enabled, and verify local activation still works offline.

These checks have not been performed on a physical device by the coding agent. This feature adds no Watch-specific APIs or Watch deployment-target changes; passive sampling behavior remains dependent on the paired hardware and OS.
