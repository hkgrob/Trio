# Dosing Modes

In Trio 1.0.2, open **Settings → Dosing Mode**. This is a four-option picker, replacing the Closed Loop on/off control shown in older screenshots. Open Loop is the default. The picker requires a connected pump and an active CGM sensor session.

## What is Closed Loop?

**Closed Loop** allows Trio to enact its automated dosing decisions, including basal reductions, corrections and SMBs when their individual conditions and safety checks permit. A forecast is not a delivery record, and a nominal five-minute loop interval does not guarantee a dose on every cycle.

## What is Open Loop?

**Open Loop** displays forecasts and recommendations without enacting automated dosing. Your pump continues its scheduled basal delivery. Manual bolus commands are separate user actions. Open Loop does not provide Trio-initiated low-glucose suspension or automatic correction of highs.

## Low Glucose Suspend

**Low Glucose Suspend (LGS)** permits predictive basal reductions while treating effective Max IOB as 0. Your saved Max IOB preference is preserved. It is not a fixed glucose-trigger switch. If reduced basal has produced negative IOB, insulin may be replenished until IOB reaches zero; therefore this mode should not be described as forbidding every amount above the scheduled basal rate.

## Basal Testing

**Basal Testing** permits low-glucose suspension rather than normal algorithm adjustments. It derives effective Max IOB 0, Autosens Min/Max 100%, Dynamic ISF off, and sigmoid off. Its threshold preference is at least 72 mg/dL: `max(saved threshold, 72)`. Profile generation also enables the suspend-only behavior. Entering this mode attempts to cancel an existing automatic temporary basal, subject to pump and delivery-state checks.

These are temporary, derived mode constraints. They do not overwrite the saved preferences. Returning to another mode can restore the influence of those saved settings.

## Want to stay in Open Loop?

Choose a mode by its actual automation behavior. Use the descriptions above to distinguish no automated enactment, predictive reductions, low-only suspension and full automation. The earlier recipe that changed saved Max IOB and Autosens values is not the dedicated Basal Testing mode. It should not be presented as equivalent to that mode.

The mode applies to automated enactment; it is not a blanket block on every manually requested or remotely requested bolus. Those paths have their own controls and validation.


## 1.0.2 source references

- **F01 — Dosing Mode replaces the documented Closed Loop switch**
    - [Trio/Sources/Models/DosingMode.swift:16](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Models/DosingMode.swift#L16)
    - [Trio/Sources/Modules/Settings/View/SettingsRootView.swift:218](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Modules/Settings/View/SettingsRootView.swift#L218)
- **F02 — Mode overrides differ from the documented manual basal-testing recipe**
    - [Trio/Sources/Models/Preferences+DosingMode.swift:6](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Models/Preferences+DosingMode.swift#L6)
    - [Trio/Sources/APS/OpenAPS/OpenAPS.swift:559](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/APS/OpenAPS/OpenAPS.swift#L559)
    - [Trio/Sources/APS/APSManager.swift:1511](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/APS/APSManager.swift#L1511)
