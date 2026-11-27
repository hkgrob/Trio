# Official Trio v1.0.2 release notes

Source: https://github.com/nightscout/Trio/releases/tag/v1.0.2
Published: 2026-10-07T19:40:39Z

# Trio v1.0.2  ![trio](https://raw.githubusercontent.com/nightscout/trio-docs/e78591c461fa022ef7426a2ca65996f0899546da/docs/favicon.ico)

This release ships an updated driver for Libre 3/3+, brings in a large round of pump and sensor driver updates, fixes alarms that warned too early, a basal rate that showed the wrong number, and a handful of other small issues. 

> [!IMPORTANT]
> **Using a FreeStyle Libre 3 or 3+? You must pair your sensor again after updating.**
> Trio has switched to an updated Libre driver. It cannot carry your old pairing over, so your sensor will stop sending readings until you re-pair it.
> **You do not need a new sensor.** Keep the one you are wearing. Open **Settings → CGM → FreeStyle Libre 3 / 3+**, tap **Pair New Sensor**, and scan the sensor with your phone, exactly like you did the very first time.
> Do this as soon as you update. Until you do, Trio has no glucose data and cannot loop.

---

## What's Changed At A Glance

- **Not-looping alerts warn you sooner** – Trio now nudges you at 20, 40, 60, 80 and 100 minutes, and sounds a critical alarm at 120. Before, you got one critical alarm at 20 minutes and nothing else
- **New alarm sound defaults for new installs** – critical alarms make a sound, the quieter two types stay silent. If you already have Trio, your own alarm settings are untouched
- **Updated driver for Libre 3 / 3+** – more reliable pairing, and a nearby Libre sensor can no longer be paired by mistake. Re-pairing is required, see above
- **The basal rate on the Home chart is correct again** – it no longer shows a temp basal that was already cancelled, and it tells you when delivery is suspended
- **Omnipod pairing in a household with several pods** – Trio now only counts pods that are actually ready to pair, so you no longer get a "too many pods found" error
- **Medtrum patch fixes** – no more crash when a patch reports a halted delivery, and Trio stops you priming before the patch is filled
- **Eversense fixes** – readings no longer stop unexpectedly, the sensor reconnects after you restart Trio, and more useful data is sent to Eversense DMS
- **AccuChek and Eversense show warm-up and expiry** – you can see on the Home screen when a sensor is warming up and when it runs out
- **Calibrations now show as fingersticks** – a calibration you enter is saved as a manual reading with the red drop on the chart, not as a sensor reading
- **Dexcom sensor states can go to Nightscout** – an off-by-default switch posts a note like "CGM: sensorFailed" when a G6 or G7 reading has no usable glucose


---

## FreeStyle Libre 3 / 3+

Trio's Libre support moved to a new driver, RoundWhiteDiscKit, together with the current version of LibreLoop ([#1609](https://github.com/nightscout/Trio/pull/1609)).

**You must pair your sensor again after updating** – see the note at the top. Nothing else about Libre changes for you.

What the new driver brings:

- **Pairing is more reliable.** It uses a proper app credential, which Trio checks before it is used.
- **The right sensor gets paired.** Trio now matches the sensor from your NFC scan by its Bluetooth address, so another Libre-family sensor nearby – a Lingo, for example – can no longer win the scan.
- **More information when something goes wrong.** Settings → Debug Info now shows your sensor's security version and region.

Libre 3 / 3+ support is still marked **(Beta)** in Trio. It has been tested on a U.S. and EU Libre 3 Plus.

---

## Alarms

- **Not-looping alerts now escalate** ([#1552](https://github.com/nightscout/Trio/pull/1552)). Trio used to go straight to one critical alarm at 20 minutes. Now you get a gentler nudge at 20, 40, 60, 80 and 100 minutes, and a critical alarm at 120 minutes. All six are handed to iOS up front, so the warnings keep coming even if iOS puts Trio to sleep. Any successful loop clears them.
- **New sound defaults, for new installs only.** On a fresh install, Critical alarms play a sound and Time-Sensitive and Normal alarms are silent. **If you already have Trio installed, your alarm settings are left exactly as you set them.**

---

## Pumps

### Omnipod

- **Pairing in a house with more than one pod user.** Trio now counts only pods that are actually candidates for pairing, so the "too many pods found" error is gone.
- **Keep-alive stays out of the background.** The "When Open" keep-alive timer no longer runs while Trio is in the background, even if your CGM wakes the app up.
- **Silence Pod end time.** Picking a time that has already passed no longer hangs the screen.
- **Known pods reconnect more simply**, with one automatic retry if the pod drops the link. Pod pairing and pod end are now recorded as pump events.

### Medtrum

- **Priming is blocked until the patch is filled**, and the priming screen now shows the reservoir level.
- **Trio will not connect to the wrong base**, and patch states are checked properly rather than guessed at.

### Dana

- Temp basal rates are rounded to two decimal places, and the pump keeps a heartbeat during Continuous mode.

---

## Sensors

### Eversense

A large driver update ([#1593](https://github.com/nightscout/Trio/pull/1593)):

- **Readings no longer stop unexpectedly**, and crashes during state changes are fixed.
- **Your transmitter reconnects after you restart Trio**, instead of needing to be set up again.
- **Uploads no longer stall** when Trio is in the background, and E3 alarms are fixed.
- The 365 handshake retries if it fails, and the vibration toggle silences the transmitter properly.
- **More is sent to Eversense DMS** to help their support team: app information, transmitter battery history and glucose logs.

### AccuChek SmartGuide

- **Trio warns you if your sensor model is not supported.**
- Calibration screens were tidied up.

### Both AccuChek and Eversense

- **Warm-up and expiry now show on the Home screen** ([#1592](https://github.com/nightscout/Trio/pull/1592)), the same way they do for other sensors.
- **Calibrations are stored as fingersticks** ([#1472](https://github.com/nightscout/Trio/pull/1472)). A reading you enter yourself is now saved as a manual glucose entry – the red drop on the chart – rather than being mixed in with sensor readings.

### Dexcom

- **Sensor states can be sent to Nightscout** ([#1420](https://github.com/nightscout/Trio/pull/1420)). A new switch under **Nightscout → Upload**, off by default, posts a note such as "CGM: sensorFailed" whenever a G6 or G7 reading arrives without usable glucose. Each state is noted once per occurrence.

---

## In the App

- **The basal rate on the Home chart is right again** ([#1556](https://github.com/nightscout/Trio/pull/1556)). It no longer shows a temp basal that has already been cancelled – for example after switching to Basal Testing. It also shows your scheduled rate before the pump has any history, marks a manual temp basal as manual, and says when delivery is suspended.
- **Override presets no longer crash the Adjustments screen** ([#1571](https://github.com/nightscout/Trio/pull/1571)). Presets saved by older builds with missing or unusual values were enough to bring the screen down.
- **The bolus keyboard stops covering the field you are typing in** ([#1434](https://github.com/nightscout/Trio/pull/1434)), along with some related scrolling problems in the Treatments view.
- **Settings hints are no longer cut off** in longer translations ([#1408](https://github.com/nightscout/Trio/pull/1408)), and the two Home grid toggles no longer touch each other at small text sizes ([#1575](https://github.com/nightscout/Trio/pull/1575)).
- Updated translations across Trio and its drivers, from our Crowdin and Lokalise contributors.

---

## Upgrade Notes

### From `1.0.1` or `1.0`

**If you use a Libre 3 / 3+, pair your sensor again straight after updating** – see the note at the top of these release notes. That is the only thing you have to do.

Everything else carries over: no settings change, no migration, no onboarding. If you are a new Trio user, check your alarm sound settings, as the defaults for new installs changed.

### From `0.8.4`

Read the [`1.0` release notes](https://github.com/nightscout/Trio/releases/tag/v1.0) – everything in their upgrade section still applies to you, including checking your alarm settings and your App Diagnostics preference. Your configuration, therapy settings, history and device connections carry over; there is no onboarding wizard and no settings reset.

### From `0.2.x`

Read the [`0.7.0` upgrade notes](https://github.com/nightscout/Trio/releases/tag/v0.7.0#upgrade-notes) and the [Migration Guide on TrioDocs](https://triodocs.org/configuration/migration/trio-02x-migration/) first, then the [`1.0` notes](https://github.com/nightscout/Trio/releases/tag/v1.0).

### From `1.0.1.x` (`dev`)

You are already running this code. No action needed beyond switching to `main`.

---

## A Note From The Trio Team

**Trio has not been reviewed by the FDA or any other regulatory body.** Nothing in these notes is medical advice; if a change here affects how you manage your diabetes, talk it through with your care team.

---

## Contributors

**Code:** @dnzxy, @bastiaanv, @ps2, @marionbarker, @bjorkert, @kingst, @LiroyvH, @aditmer, @jwoglom, @kristinkand, @lolzivkovic

**Drivers:** the OmnipodKit, EversenseKit, MedtrumKit, DanaKit, AccuChekKit, LibreLoop, RoundWhiteDiscKit and LoopKit maintainers – see the submodule pull requests for full credit.

**Translators:** Crowdin and Lokalise contributors across all supported languages.

---

<details>
<summary><b>Full Changelog</b></summary>

| PR | Change | Author |
|---|---|---|
| [#1408](https://github.com/nightscout/Trio/pull/1408) | Fix localized settings hint layout | @aditmer |
| [#1420](https://github.com/nightscout/Trio/pull/1420) | Report Dexcom sensor states to Nightscout as notes | @bjorkert |
| [#1434](https://github.com/nightscout/Trio/pull/1434) | Update TreatmentsRootView.swift to fix auto-scrolling and some (related) bugs | @LiroyvH |
| [#1472](https://github.com/nightscout/Trio/pull/1472) | fix: store calibrations as manual fingersticks | @bastiaanv |
| [#1552](https://github.com/nightscout/Trio/pull/1552) | Adjust Not-Looping Alerts Escalation | @dnzxy |
| [#1556](https://github.com/nightscout/Trio/pull/1556) | Fix stale basal rate on home chart | @dnzxy |
| [#1565](https://github.com/nightscout/Trio/pull/1565) | minor codeowners fix | @jwoglom |
| [#1571](https://github.com/nightscout/Trio/pull/1571) | Fix two crash risks in Override preset row rendering | @kristinkand |
| [#1575](https://github.com/nightscout/Trio/pull/1575) | Fix home view toggle placement | @lolzivkovic |
| [#1592](https://github.com/nightscout/Trio/pull/1592) | Fix: Eversense & Accuchek expires & warming up | @bastiaanv |
| [#1593](https://github.com/nightscout/Trio/pull/1593) | chore: update EversenseKit | @bastiaanv |
| [#1609](https://github.com/nightscout/Trio/pull/1609) | Replace LibreCRKit with RoundWhiteDiscKit and track LoopKit's LibreLoop | @ps2 |
| [#1612](https://github.com/nightscout/Trio/pull/1612) | Update scripts and selected submodules | @marionbarker |
| [#1614](https://github.com/nightscout/Trio/pull/1614) | Run swiftformat and extract missing strings | @kingst |

**Full diff:** https://github.com/nightscout/Trio/compare/v1.0.1...v1.0.2

</details>

