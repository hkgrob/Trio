# Activity monitoring and automatic presets

Open **Settings → Services → Apple Health → Activity observations**.

## Passive observation

Collection is off by default and independent of the existing Apple Health write integration. Enabling it requests heart-rate read permission and starts iPhone motion/step collection, subject to Motion & Fitness permission and hardware availability. No workout needs to be started.

Heart rate comes from authorized samples in the iPhone Health store, including Apple Watch samples after synchronization. This implementation does not start a Watch workout or directly stream the Watch sensor. It records the source, measurement timestamps, and the time Trio receives each sample, so end-to-end availability delays can be measured. This includes both synchronization and app execution delays; it does not isolate them. HealthKit does not disclose whether read permission was denied; no readings must not be interpreted as proof that permission was granted or that activity is absent.

iPhone activity classifications include motion confidence. Live step readings are cumulative from the current pedometer session's start, not additive deltas. Queried step intervals record actual counts over the preceding minute, including zero; automatic detection prefers these intervals once available. The phone must be carried to represent the wearer's movement. Motion callbacks and the collection timer pause when iOS suspends Trio. Collection resumes using existing app execution opportunities and HealthKit background delivery; neither guarantees immediate updates or continuous execution. Force-quitting Trio can interrupt collection.

The history retains at most 20,000 observations from the preceding seven days. It is saved locally with file protection; it may be included in device backups. CSV export includes timestamps and sources. Turning collection off retains history; clearing history also stops collection. No raw activity observations are uploaded to Nightscout.

## Automatic activity detection

Select an existing activity preset at the top of the screen. Enable collection, enter the Watch heart-rate threshold, iPhone fallback step-rate threshold, required activity duration, and recovery duration. No exercise thresholds or durations are preselected. The maximum reading age/gap defaults to two minutes and can be changed; it must be at least one minute to accommodate the phone's queried intervals. Then explicitly enable **Automatically activate activity preset**. This is independent of the workout shortcut toggle.

Fresh, non-manual Apple Watch heart rate takes precedence, identified using HealthKit's device/product metadata. If Watch heart rate is at or above the configured threshold for the configured duration, it can trigger on its own. Fresh Watch heart rate below the threshold vetoes elevated phone movement. Only when Watch heart rate is missing or stale does the phone's step rate become the fallback. A change of source resets the qualification window; evidence from the two sources is not combined into one run. Motion activity labels alone never trigger activation.

Qualification must advance on new measurement timestamps. A held reading, a timer, a delayed batch, observations from before arming, or an app execution gap cannot backdate a sustained activity window. Activation is decided only after the complete incoming batch is processed: a batch ending with a below-threshold Watch reading cannot activate from an earlier high reading. Fresh Watch readings collected before arming are retained as source-precedence context, without contributing time toward qualification. Phone intervals are converted to steps per minute; cumulative readings are never summed. Actual queried zero-step readings can demonstrate phone recovery, while silence cannot.

Each detected episode gets at most one activation attempt, including when an existing adjustment causes that attempt to be skipped or a preset has been deleted. The episode latch is persisted before requesting activation and survives restarts. It is released only after fresh measurements from the currently preferred source remain below its threshold for the recovery duration. Switching sources or losing both sources resets recovery progress; missing data does not count as recovery. Recovery only re-arms future detection; it does not cancel or change a running preset. The preset's saved duration still applies, and an expired preset is not automatically restarted during the same episode.

Manual adjustment requests suppress the current episode synchronously on the main actor, before changing stored adjustments or waiting for Nightscout uploads. Upload completion and automatic expiry do not count as a second manual interruption. Changing thresholds or the selected preset, or stopping collection, disables passive automation until explicitly re-enabled. A queued request is also revoked if its preferred source changes or its current activity evidence is no longer eligible. Each request has a deadline derived from the qualifying reading; the serialized adjustment transaction rejects expired requests even without a new sensor callback. Disabling automation does not undo a preset that has already started.

Successful detection requests the same saved preset as the workout shortcut, through the existing adjustment manager. Existing adjustments are preserved, a local result notification is requested, and standard Nightscout uploads allow LoopFollow start alarms. No new insulin calculation, glucose prediction, basal-rate formula, or pump command is introduced. Configure an appropriate user-created preset; the detector does not decide whether insulin should increase or decrease.

## Explicit Apple Watch workout starts

Workout activation is a separate opt-in, off by default. Select one existing user-created override **or** temporary-target preset, then enable **Allow workout preset activation**. Changing the selection disables activation until explicitly re-enabled.

In the iPhone **Shortcuts** app:

1. Create a personal automation with the **Apple Watch Workout** trigger.
2. Select **Starts**, the desired workout types, and **Run Immediately**.
3. Add Trio's **Activate workout preset** action.

The action is intentionally parameterless: it uses Trio's configured activity preset. Configure the trigger carefully: manually running this action also requests activation. Trio does not claim to independently verify the source of an invocation. There is no generic live HealthKit observer for the start of another app's workout; observing a saved workout would be too late for this purpose.

Activation uses the existing adjustment manager and its serialized transaction. If an override or temporary target is still running, it skips activation without restarting, replacing, or cancelling it. Finite adjustments whose saved duration has expired do not block later episodes, even before UI cleanup. Indefinite adjustments and rows with unknown expiry remain protected. UI expiry tasks recheck current state in the same serializer, so an old cleanup task cannot cancel a restarted preset or a different running preset. Only saved presets are eligible. The selected preset's current settings and saved duration apply, including indefinite duration. Workout end does not cancel the preset. Multiple simultaneous workout invocations cannot enable both adjustment types.

Trio records the last result and requests a normal local notification for successful, skipped, or failed activation attempts while this option is enabled. Notification presentation depends on permission and system settings. The action never sends pump commands directly or changes the dosing algorithm. As with manual preset activation, the preset affects subsequent dosing through the existing pipeline.

Successful starts use Trio's existing Nightscout upload settings. Configure **Override Start** or **Temp Target Start** alarms in a compatible LoopFollow version for parent alerts. Those alerts depend on connectivity and follower updates, and do not specifically distinguish workout automation from manual starts.

## Validation

History tests cover arrival-time preservation, late arrival ordering, deletion, retention/count limits, invalid samples, CSV escaping, persistence, and default-disabled configuration. Detector tests also cover complete-batch decisions, fresh Watch context at arming, pending-request revocation and deadlines. Adjustment tests cover active-adjustment preservation, expired finite rows, indefinite/unknown expiry protection, manual intent before mutation/upload, duplicate/concurrent starts, rejecting non-presets, cancelled/expired requests, and serialized expiry after a preset restart. The isolated harness and iOS-hosted tests exercise these paths; they do not establish end-to-end physical sensor behavior.

Before relying on the feature, verify on a physical phone/Watch pair:

1. Deny and grant Health/Motion permissions; verify that missing data is not shown as inactivity.
2. Collect with the phone carried and left stationary, screen off, and Trio backgrounded. Compare measurement and arrival timestamps.
3. Turn collection off and clear history; verify that in-flight callbacks do not resume collection.
4. With explicitly configured thresholds, confirm that fresh Watch data takes precedence over conflicting phone movement. Check phone fallback only when Watch data is missing/stale, and source-change qualification reset.
5. Confirm one activation attempt per episode, fresh recovery before re-arming, and no restart after manually cancelling or letting a preset expire while activity remains elevated. Restart Trio and verify the latch remains in force.
6. Start an Apple Workout with the personal automation enabled, including with the iPhone locked. Check the selected preset, saved duration, local result, and notification.
7. Repeat automatic and workout starts with an existing override and an existing temporary target. Both must remain unchanged.
8. Check Nightscout and LoopFollow with uploads enabled, and verify local activation still works offline.

These checks have not been performed on a physical device by the coding agent. This feature adds no Watch-specific APIs or Watch deployment-target changes; passive sampling behavior remains dependent on the paired hardware and OS.
