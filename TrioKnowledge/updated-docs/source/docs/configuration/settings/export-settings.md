# Export Settings

Open **Settings → Export Settings**. Select the categories you want to include and use the export/share action to save a CSV. Include **Metadata, Therapy, Algorithm and Features** for a useful settings review; add other categories when they are relevant.

## What the CSV contains

The English header is `Setting Category,Subcategory,Setting Name,Value,Unit`. Rows may include app version, build and branch, units/limits, schedules, algorithm and feature settings, devices/services, and presets, depending on the selected categories. Names, some values and units are localized.

Percentages are exported in displayed percent units, while stored JSON factors use fractions: a displayed 80% corresponds to `0.8`. Glucose rows use the selected display unit; stored algorithm glucose values use mg/dL. Keep each row's Unit column when sharing a file.

## Stored versus effective settings

Some values are annotated as `stored value (mode is using effective value)` when the dosing mode overrides them. For example, Basal Testing derives effective Autosens Min/Max 100% without changing the saved values. Metadata includes Dosing Mode when that category is selected. Missing categories or fields must not be assumed to be at factory defaults.

## Evaluate the file locally

The companion knowledge graph accepts an English CSV export or stored-settings JSON. Choose the file in **Evaluate your settings export**. It reports supported type/range checks, dependencies and known effective values, and lists every row it does not evaluate. Schedules and device/preset/service fields are not all mechanically assessed.

The file is read in browser memory and is not sent to a server or saved automatically. **Clear settings** removes the working report from the tab; **Download evaluation** saves a report only when you choose it. Questions in that tab can use supplied values, while missing glucose history, active overrides and other runtime state remain unknown.

The CSV is a review/share export, not an automatic import, backup restoration or verification that settings suit a particular person.


## 1.0.2 source references

- **F02 — Mode overrides differ from the documented manual basal-testing recipe**
    - [Trio/Sources/Models/Preferences+DosingMode.swift:6](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Models/Preferences+DosingMode.swift#L6)
    - [Trio/Sources/APS/OpenAPS/OpenAPS.swift:559](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/APS/OpenAPS/OpenAPS.swift#L559)
    - [Trio/Sources/APS/APSManager.swift:1511](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/APS/APSManager.swift#L1511)
- **F08 — Document the Settings CSV export and effective-mode annotations**
    - [Trio/Sources/Modules/Settings/View/SettingsRootView.swift:394](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Modules/Settings/View/SettingsRootView.swift#L394)
    - [Trio/Sources/Modules/SettingsExport/SettingsExportStateModel.swift:1249](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Modules/SettingsExport/SettingsExportStateModel.swift#L1249)
