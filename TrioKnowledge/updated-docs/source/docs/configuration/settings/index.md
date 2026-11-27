# Trio Settings

![Trio Logo](../../assets/images/trio-logo.png){ .skip-lightbox width="75" align="left" }
Welcome to the Trio Settings homepage! Here you'll find explanations of all the settings in Trio. They are organized by their appearance in the Settings Menu in the Trio app.  

- - -

Please use the navigation menu :fontawesome-solid-bars:, search bar :fontawesome-solid-magnifying-glass:, or the menu below to find the section you are looking for.

<div class="grid cards" markdown>

-   __[Devices](devices/index.md)__

    - - -
    
    Set up your pump, cgm, and smart watch

-   __[Therapy](therapy/index.md)__

    - - -
    
    Set your "Trio" of core settings (Basal, ISF, and CR), Glucose Target, and Units & Limits
    
-   __[Algorithm](algorithm/index.md)__

    - - -
    
    Configure Trio's algorithm, SMBs, and dynamic options
    
-   __[Features](features/index.md)__

    - - -
    
    Set up bolusing options, shortcuts, remote control, and personalize the app
    
-   __[Notifications](notifications/index.md)__

    - - -
    
    Customize app notifications, including live activity and calendar events
    
-   __[Services](services/index.md)__

    - - -
    
    Connect Nightscout, Tidepool, and Apple Health
    
-   __[Dosing Modes](closed-loop.md)__
    
</div>


## Export Settings

Use [Export Settings](export-settings.md) to share a versioned configuration for review.


## 1.0.2 source references

- **F01 — Dosing Mode replaces the documented Closed Loop switch**
    - [Trio/Sources/Models/DosingMode.swift:16](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Models/DosingMode.swift#L16)
    - [Trio/Sources/Modules/Settings/View/SettingsRootView.swift:218](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Modules/Settings/View/SettingsRootView.swift#L218)
- **F08 — Document the Settings CSV export and effective-mode annotations**
    - [Trio/Sources/Modules/Settings/View/SettingsRootView.swift:394](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Modules/Settings/View/SettingsRootView.swift#L394)
    - [Trio/Sources/Modules/SettingsExport/SettingsExportStateModel.swift:1249](https://github.com/nightscout/Trio/blob/0b29cd53415e7f0e668677749cad8daf81c68c2f/Trio/Sources/Modules/SettingsExport/SettingsExportStateModel.swift#L1249)
