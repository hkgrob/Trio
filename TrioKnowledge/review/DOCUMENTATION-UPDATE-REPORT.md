# Trio 1.0.2 documentation alignment review

Reviewed against main / v1.0.2 `0b29cd53415e7f0e668677749cad8daf81c68c2f`. Documentation captured 2026-11-27T19:57:28.765936+00:00.

## Scope and evidence

All 101 published sitemap pages were saved without download failures. The complete pinned source has 104 Markdown documents: 101 pages and three include fragments. The app index covers committed first-party Swift (including tests and Watch/extensions), JSON, JavaScript, docs, build scripts and configuration. Device submodule implementations are not exhaustively audited; their exact Git commits are recorded in knowledge/code-manifest.json. The review combines corpus indexing, a settings/model/UI inventory, and targeted manual tracing of the findings below. It is not a claim that every sentence or device workflow has been manually validated.

Published HTML/search text and dev-branch Markdown are separate snapshots. The core mismatch wording was also checked in the published search corpus. Upstream files are preserved unchanged; the proposed corrections below are local review work, not published edits.

## Priority

Correct dosing-mode and basal-testing instructions (F01–F02), remote duplicate checks (F04), and the calculator trend description (F05) first. Confirm maintainer intent where behavior and wording differ. Then correct SMB limits (F03) and Libre branch availability (F07), and add the missing feature guides. No dosing implementation was changed.

| Finding | Classification | Topic |
|---|---|---|
| F01 | verified-mismatch | Dosing Mode replaces the documented Closed Loop switch |
| F02 | verified-mismatch | Mode overrides differ from the documented manual basal-testing recipe |
| F03 | verified-mismatch | SMB and UAM basal-minute picker limits start at 15, not 30 |
| F04 | verified-mismatch | Remote duplicate-bolus guard uses command time and a cumulative inclusive threshold |
| F05 | verified-mismatch | Calculator trend input is newest minus oldest within 20 minutes |
| F06 | verified-gap | Calculator safety gates and backdated-carb handling need explicit documentation |
| F07 | verified-mismatch | Libre 3 documentation still claims dev-only availability |
| F08 | verified-gap | Document the Settings CSV export and effective-mode annotations |
| F09 | verified-gap | Garmin guide omits configuration choices and transmission reset behavior |
| F10 | verified-gap | Shortcut boluses use shared safety checks beyond the permission toggle |
| F11 | verified-behavior | The meal bolus calculator already subtracts automated insulin represented in IOB |
| F12 | verified-behavior | UAM does not independently grant SMB permission; interval is not a delivery schedule |

## F01: Dosing Mode replaces the documented Closed Loop switch

**Verified behavior:** In the pinned 1.0.2 code, Settings uses a Dosing Mode picker with closed, open, lowGlucoseSuspend and basalTesting. Open is the model default. Closed permits full automation; Open enacts no automated dosing; LGS uses reductionsOnly; Basal Testing uses hypoSuspendOnly. LGS can replenish negative IOB up to zero, so describing it as never giving any extra insulin is too absolute. These modes govern automated enactment, not every user-initiated manual bolus.

**Documentation action:** Replace switch-based navigation and screenshots on the closing-the-loop and new-user pages with the four-mode picker. Explain each mode's enactment scope and the requirement for a pump and CGM. Preserve the distinction between forecasts and delivered insulin.

**Evidence:**

- [Trio/Sources/Models/DosingMode.swift:16](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Models/DosingMode.swift#L16) ([local snapshot](../knowledge/code/Trio/Sources/Models/DosingMode.swift))
- [Trio/Sources/Modules/Settings/View/SettingsRootView.swift:218](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Modules/Settings/View/SettingsRootView.swift#L218) ([local snapshot](../knowledge/code/Trio/Sources/Modules/Settings/View/SettingsRootView.swift))
- [upstream/source/docs/configuration/settings/closed-loop.md:2](https://github.com/nightscout/trio-docs/blob/159649de635575ee3f732008dafcff25eb39181c/docs/configuration/settings/closed-loop.md#L2) ([local snapshot](../upstream/source/docs/configuration/settings/closed-loop.md))

## F02: Mode overrides differ from the documented manual basal-testing recipe

**Verified behavior:** LGS derives effective maxIOB=0. Basal Testing additionally derives autosensMin=autosensMax=1, disables useNewFormula and sigmoid, and raises threshold_setting to at least 72 mg/dL. Saved preferences remain unchanged. Profile generation actually calls clamped(for:); entry into Basal Testing also attempts to cancel an existing automatic temp basal. The documentation instead tells readers to change saved Max IOB, Autosens and Dynamic settings manually.

**Documentation action:** Document derived versus stored settings and the dedicated Basal Testing mode. Distinguish Basal Testing's low-only suspension from predictive reductions in LGS. Replace the old saved-setting recipe with a version-specific explanation rather than recommending patient-specific changes.

**Evidence:**

- [Trio/Sources/Models/Preferences+DosingMode.swift:6](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Models/Preferences+DosingMode.swift#L6) ([local snapshot](../knowledge/code/Trio/Sources/Models/Preferences+DosingMode.swift))
- [Trio/Sources/APS/OpenAPS/OpenAPS.swift:559](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/APS/OpenAPS/OpenAPS.swift#L559) ([local snapshot](../knowledge/code/Trio/Sources/APS/OpenAPS/OpenAPS.swift))
- [Trio/Sources/APS/APSManager.swift:1511](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/APS/APSManager.swift#L1511) ([local snapshot](../knowledge/code/Trio/Sources/APS/APSManager.swift))
- [upstream/source/docs/configuration/settings/closed-loop.md:20](https://github.com/nightscout/trio-docs/blob/159649de635575ee3f732008dafcff25eb39181c/docs/configuration/settings/closed-loop.md#L20) ([local snapshot](../upstream/source/docs/configuration/settings/closed-loop.md))

## F03: SMB and UAM basal-minute picker limits start at 15, not 30

**Verified behavior:** Both maxSMBBasalMinutes and maxUAMSMBBasalMinutes have picker bounds 15–180 minutes in steps of 5. Their default is still 30. The documentation lists 30–180 for both. Picker limits describe selectable values, not a clinically appropriate range or all downstream pump constraints.

**Documentation action:** Change both Setting Limits entries to 15–180 minutes; retain the 30-minute default. Keep default and allowable range distinct.

**Evidence:**

- [Trio/Sources/Models/DecimalPickerSettings.swift:88](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Models/DecimalPickerSettings.swift#L88) ([local snapshot](../knowledge/code/Trio/Sources/Models/DecimalPickerSettings.swift))
- [upstream/source/docs/configuration/settings/algorithm/smb-settings.md:111](https://github.com/nightscout/trio-docs/blob/159649de635575ee3f732008dafcff25eb39181c/docs/configuration/settings/algorithm/smb-settings.md#L111) ([local snapshot](../upstream/source/docs/configuration/settings/algorithm/smb-settings.md))

## F04: Remote duplicate-bolus guard uses command time and a cumulative inclusive threshold

**Verified behavior:** The shared evaluator rejects when total recent bolus is greater than or equal to 20% of the requested bolus. Remote bolus passes the original command timestamp as lookbackStart, so its cumulative sum covers boluses since the command was sent. Shortcuts omits that argument and uses the default six-minute lookback. The docs instead describe an individual bolus greater than 20% within a fixed ten-minute window. Command expiry is a separate validation and should not be confused with this lookback.

**Documentation action:** Rewrite duplicate prevention to describe summed boluses, >=20%, and the caller-specific windows. Replace the remote eight-minutes-ago example: a bolus before the command timestamp is outside this caller's lookback. Document command expiry separately.

**Evidence:**

- [Trio/Sources/Services/BolusSafety/BolusSafetyValidator.swift:43](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Services/BolusSafety/BolusSafetyValidator.swift#L43) ([local snapshot](../knowledge/code/Trio/Sources/Services/BolusSafety/BolusSafetyValidator.swift))
- [Trio/Sources/Services/RemoteControl/TrioRemoteControl+Bolus.swift:13](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Services/RemoteControl/TrioRemoteControl+Bolus.swift#L13) ([local snapshot](../knowledge/code/Trio/Sources/Services/RemoteControl/TrioRemoteControl+Bolus.swift))
- [Trio/Sources/Shortcuts/Bolus/BolusIntentRequest.swift:16](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Shortcuts/Bolus/BolusIntentRequest.swift#L16) ([local snapshot](../knowledge/code/Trio/Sources/Shortcuts/Bolus/BolusIntentRequest.swift))
- [upstream/source/docs/configuration/settings/features/remote-control.md:211](https://github.com/nightscout/trio-docs/blob/159649de635575ee3f732008dafcff25eb39181c/docs/configuration/settings/features/remote-control.md#L211) ([local snapshot](../upstream/source/docs/configuration/settings/features/remote-control.md))

## F05: Calculator trend input is newest minus oldest within 20 minutes

**Verified behavior:** updateGlucoseVariables selects readings newer than now minus 20 minutes and calculates newest glucose minus oldest glucose within that window, or zero if fewer than two readings exist. It does not normalize that delta to a fixed 15-minute interval. The later variable is still named fifteenMinutesInsulin. Docs describe the last 15 minutes / three readings; actual span depends on available readings.

**Documentation action:** Describe the actual data-window selection and irregular-reading behavior. Flag the 15-minute documentation versus 20-minute implementation as requiring maintainer intent confirmation before changing algorithm behavior; this review changes no dosing code.

**Evidence:**

- [Trio/Sources/Services/BolusCalculator/BolusCalculationManager.swift:216](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Services/BolusCalculator/BolusCalculationManager.swift#L216) ([local snapshot](../knowledge/code/Trio/Sources/Services/BolusCalculator/BolusCalculationManager.swift))
- [upstream/source/docs/usage/features/bolus-calculator.md:239](https://github.com/nightscout/trio-docs/blob/159649de635575ee3f732008dafcff25eb39181c/docs/usage/features/bolus-calculator.md#L239) ([local snapshot](../upstream/source/docs/usage/features/bolus-calculator.md))

## F06: Calculator safety gates and backdated-carb handling need explicit documentation

**Verified behavior:** Backdated calculation uses zero new carbs and simulated COB. Ordinary calculation uses existing COB plus new carbs capped by maxCOB. Recommendation becomes zero for currentBG<54 mg/dL, minPredBG<54, or loop age>15 minutes. Otherwise the code applies a nonnegative clamp, Max Bolus cap, Max IOB headroom cap and pump bolus rounding in that order. It does not apply a second nonnegative clamp after maxIOB-currentIOB, so negative headroom is an edge case to inspect rather than assume away.

**Documentation action:** Add an explicit backdated-meal example, the three zero-recommendation conditions, and the actual cap/rounding order to the calculator guide. Distinguish a displayed recommendation from a validated delivery command.

**Evidence:**

- [Trio/Sources/Services/BolusCalculator/BolusCalculationManager.swift:344](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Services/BolusCalculator/BolusCalculationManager.swift#L344) ([local snapshot](../knowledge/code/Trio/Sources/Services/BolusCalculator/BolusCalculationManager.swift))
- [Trio/Sources/Services/BolusCalculator/BolusCalculationManager.swift:452](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Services/BolusCalculator/BolusCalculationManager.swift#L452) ([local snapshot](../knowledge/code/Trio/Sources/Services/BolusCalculator/BolusCalculationManager.swift))
- [upstream/source/docs/usage/features/bolus-calculator.md:1](https://github.com/nightscout/trio-docs/blob/159649de635575ee3f732008dafcff25eb39181c/docs/usage/features/bolus-calculator.md#L1) ([local snapshot](../upstream/source/docs/usage/features/bolus-calculator.md))

## F07: Libre 3 documentation still claims dev-only availability

**Verified behavior:** The published CGM guide says Libre 3/3 Plus requires dev. The pinned 1.0.2 main code includes the Libre 3 plugin. The official 1.0.2 release notes also describe the updated Libre driver and mandatory re-pairing after upgrade. The latest dev-source sensor recovery instructions may describe a different driver revision; availability does not establish every driver instruction applies to main.

**Documentation action:** Remove the unconditional dev-only claim for the 1.0.2 guide. Add a clearly versioned upgrade/re-pair note, and verify sensor startup/recovery instructions against the exact LibreLoop submodule revision before copying newer driver procedures into 1.0.2 instructions.

**Evidence:**

- [Trio/Sources/APS/Devices/DeviceCatalog.swift:357](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/APS/Devices/DeviceCatalog.swift#L357) ([local snapshot](../knowledge/code/Trio/Sources/APS/Devices/DeviceCatalog.swift))
- [.gitmodules:44](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/.gitmodules#L44) ([local snapshot](../knowledge/code/.gitmodules))
- [upstream/source/docs/configuration/settings/devices/cgm.md:87](https://github.com/nightscout/trio-docs/blob/159649de635575ee3f732008dafcff25eb39181c/docs/configuration/settings/devices/cgm.md#L87) ([local snapshot](../upstream/source/docs/configuration/settings/devices/cgm.md))

## F08: Document the Settings CSV export and effective-mode annotations

**Verified behavior:** Settings has Export Settings. The implementation exports selected categories to CSV with Setting Category, Subcategory, Setting Name, Value and Unit columns, plus optional version/build/branch metadata. It annotates some values overridden by dosing mode. The docs corpus describes log export but has no settings-export guide. CSV names and values are localized; the export is not a flat preferences JSON backup or an import mechanism.

**Documentation action:** Add an Export Settings guide covering category selection, metadata, units, stored/effective annotations and sharing. Explain that export supports review rather than automatic restoration. Use a fresh export when evaluating a configuration.

**Evidence:**

- [Trio/Sources/Modules/Settings/View/SettingsRootView.swift:394](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Modules/Settings/View/SettingsRootView.swift#L394) ([local snapshot](../knowledge/code/Trio/Sources/Modules/Settings/View/SettingsRootView.swift))
- [Trio/Sources/Modules/SettingsExport/SettingsExportStateModel.swift:1249](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Modules/SettingsExport/SettingsExportStateModel.swift#L1249) ([local snapshot](../knowledge/code/Trio/Sources/Modules/SettingsExport/SettingsExportStateModel.swift))
- [upstream/source/docs/help/share-logs.md:14](https://github.com/nightscout/trio-docs/blob/159649de635575ee3f732008dafcff25eb39181c/docs/help/share-logs.md#L14) ([local snapshot](../upstream/source/docs/help/share-logs.md))

## F09: Garmin guide omits configuration choices and transmission reset behavior

**Verified behavior:** The 1.0.2 Garmin configuration includes watchface selection, independent datafield selection, a transmission control and primary/secondary attribute choices. Its help includes a Complication option. Changing the selected watchface disables transmission and requires resuming it after changing the watch. The brief documentation focuses on sideloading and adding a device. Current Connect IQ publication status was not evaluated.

**Documentation action:** Add screenshots and instructions for each configuration choice and the pause/change/resume sequence. Verify external distribution links separately instead of inferring their present status from app code.

**Evidence:**

- [Trio/Sources/Modules/WatchConfig/View/WatchConfigGarminAppConfigView.swift:18](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Modules/WatchConfig/View/WatchConfigGarminAppConfigView.swift#L18) ([local snapshot](../knowledge/code/Trio/Sources/Modules/WatchConfig/View/WatchConfigGarminAppConfigView.swift))
- [Trio/Sources/Models/GarminWatchSettings.swift:54](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Models/GarminWatchSettings.swift#L54) ([local snapshot](../knowledge/code/Trio/Sources/Models/GarminWatchSettings.swift))
- [upstream/source/docs/configuration/settings/devices/smart-watch.md:23](https://github.com/nightscout/trio-docs/blob/159649de635575ee3f732008dafcff25eb39181c/docs/configuration/settings/devices/smart-watch.md#L23) ([local snapshot](../upstream/source/docs/configuration/settings/devices/smart-watch.md))

## F10: Shortcut boluses use shared safety checks beyond the permission toggle

**Verified behavior:** The UI permission maps to bolusShortcut notAllowed or limitWithSafetyChecks. The bolus intent uses the shared validator before pump rounding/enactment, enforcing Max Bolus, available current IOB, Max IOB headroom and the cumulative >=20% recent-bolus check with the default six-minute window. External insulin logging is a distinct path with a three-times-Max-Bolus bound and does not deliver insulin.

**Documentation action:** Expand the Shortcuts bolus section with rejection conditions, the internal enum/export mapping and the difference between requesting a pump bolus and logging externally delivered insulin.

**Evidence:**

- [Trio/Sources/Shortcuts/Bolus/BolusIntentRequest.swift:14](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Shortcuts/Bolus/BolusIntentRequest.swift#L14) ([local snapshot](../knowledge/code/Trio/Sources/Shortcuts/Bolus/BolusIntentRequest.swift))
- [Trio/Sources/Services/BolusSafety/BolusSafetyValidator.swift:44](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Services/BolusSafety/BolusSafetyValidator.swift#L44) ([local snapshot](../knowledge/code/Trio/Sources/Services/BolusSafety/BolusSafetyValidator.swift))
- [upstream/source/docs/configuration/settings/features/shortcuts.md:29](https://github.com/nightscout/trio-docs/blob/159649de635575ee3f732008dafcff25eb39181c/docs/configuration/settings/features/shortcuts.md#L29) ([local snapshot](../upstream/source/docs/configuration/settings/features/shortcuts.md))

## F11: The meal bolus calculator already subtracts automated insulin represented in IOB

**Verified behavior:** The calculator combines glucose correction, glucose trend and capped COB plus new-carbs coverage, then subtracts current IOB. Automated insulin already included in that IOB is therefore counted. Positive results are multiplied by overrideFactor (Recommended Bolus Percentage), optionally by fattyMealFactor; an optional super-bolus component is added afterward. This is separate from smbDeliveryRatio, which scales automated SMB delivery. Default overrideFactor is 0.8 (80%); smbDeliveryRatio is 0.5 (50%). Neither default establishes the right personal setting.

**Documentation action:** Keep the existing IOB explanation: it agrees with the implementation. Add a cross-link explaining the separate manual-recommendation and automated-SMB percentages, plus the backdated-carb path. Avoid claiming that all documentation is wrong.

**Evidence:**

- [Trio/Sources/Services/BolusCalculator/BolusCalculationManager.swift:400](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Services/BolusCalculator/BolusCalculationManager.swift#L400) ([local snapshot](../knowledge/code/Trio/Sources/Services/BolusCalculator/BolusCalculationManager.swift))
- [upstream/source/docs/usage/features/bolus-calculator.md:129](https://github.com/nightscout/trio-docs/blob/159649de635575ee3f732008dafcff25eb39181c/docs/usage/features/bolus-calculator.md#L129) ([local snapshot](../upstream/source/docs/usage/features/bolus-calculator.md))

## F12: UAM does not independently grant SMB permission; interval is not a delivery schedule

**Verified behavior:** The SMB permission function checks override/schedule blocks, high Temp Target restrictions, then SMB Always, COB, After Carbs, low Temp Target and high-glucose conditions. enableUAM alone is not one of those enabling conditions. Later guard-glucose and maximum-delta checks can still block SMBs. The interval is clamped to 1–10 minutes and delivery requires lastBolusAge strictly greater than the interval when that age exists. It is an eligibility gate, not a timer promising delivery every N minutes. The basal-minute cap switches to the UAM branch when current IOB exceeds mealCOB/carbRatio and is positive; override settings can change the minutes and basal factor.

**Documentation action:** Keep the documented SMB prerequisite flow, but explain that UAM enablement, an SMB permission condition, current safety checks and actual loop timing are separate. Qualify the simplified per-dose basal-minute formula for active overrides and the code's IOB-versus-meal-insulin branch.

**Evidence:**

- [Trio/Sources/APS/OpenAPSSwift/DetermineBasal/DosingEngine.swift:18](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/APS/OpenAPSSwift/DetermineBasal/DosingEngine.swift#L18) ([local snapshot](../knowledge/code/Trio/Sources/APS/OpenAPSSwift/DetermineBasal/DosingEngine.swift))
- [Trio/Sources/APS/OpenAPSSwift/DetermineBasal/DosingEngine.swift:840](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/APS/OpenAPSSwift/DetermineBasal/DosingEngine.swift#L840) ([local snapshot](../knowledge/code/Trio/Sources/APS/OpenAPSSwift/DetermineBasal/DosingEngine.swift))
- [Trio/Sources/APS/OpenAPSSwift/DetermineBasal/DosingEngine.swift:720](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/APS/OpenAPSSwift/DetermineBasal/DosingEngine.swift#L720) ([local snapshot](../knowledge/code/Trio/Sources/APS/OpenAPSSwift/DetermineBasal/DosingEngine.swift))
- [upstream/source/docs/configuration/settings/algorithm/smb-settings.md:109](https://github.com/nightscout/trio-docs/blob/159649de635575ee3f732008dafcff25eb39181c/docs/configuration/settings/algorithm/smb-settings.md#L109) ([local snapshot](../upstream/source/docs/configuration/settings/algorithm/smb-settings.md))

## Remaining review limits

The UI-label coverage CSV reports lexical matches and missing exact-label matches. Neither proves semantic agreement or a defect. Schedule editing, device onboarding, screenshots, alarms, localization, and signed hardware behavior need their own walkthroughs. Settings evaluation checks only supplied supported fields and explicitly lists unassessed rows; it does not determine clinical suitability. External Garmin store status and every Libre driver procedure remain unverified.
