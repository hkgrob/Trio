"""Current knowledge topics grounded in the accepted updated documentation edition."""
import json
from pathlib import Path


TOPICS = {
    'F01': ('Dosing modes', 'configuration/settings/closed-loop.md', '# Dosing Modes',
            'Settings → Dosing Mode offers Closed Loop, Open Loop, Low Glucose Suspend and Basal Testing. Open Loop is the default and enacts no automated dosing. Closed Loop permits full automation subject to settings and safety checks. LGS permits predictive reductions with effective Max IOB 0 and may replenish negative IOB up to zero. Basal Testing permits low-glucose suspension. Manual bolus commands have their own controls and validation.'),
    'F02': ('Stored and effective settings in constrained dosing modes', 'configuration/settings/closed-loop.md', '## Basal Testing',
            'Low Glucose Suspend derives effective Max IOB 0 without changing the saved preference. Basal Testing additionally derives Autosens Min and Max 100%, disables Dynamic ISF and sigmoid, and uses max(saved threshold, 72 mg/dL). Entering Basal Testing attempts to cancel an existing automatic temporary basal, subject to pump and delivery-state checks. Returning to another mode can restore the influence of saved preferences.'),
    'F03': ('SMB and UAM basal-minute limits', 'configuration/settings/algorithm/smb-settings.md', '## Max SMB Basal Minutes',
            'Max SMB Basal Minutes and Max UAM Basal Minutes each default to 30 minutes. Both pickers allow 15–180 minutes in steps of five. These values cap an eligible individual dose; they do not guarantee delivery frequency. Active advanced overrides can replace the minutes and scale the basal factor.'),
    'F04': ('Remote and Shortcut duplicate-bolus validation', 'configuration/settings/features/remote-control.md', '**Duplicate Bolus Prevention**',
            'The shared bolus validator rejects a request when cumulative recent boluses are greater than or equal to 20% of the requested amount. Remote bolus sums deliveries since the original command timestamp. Shortcuts uses the default six-minute lookback. Command expiry is a separate check. Max Bolus, available current IOB and Max IOB headroom are also validated.'),
    'F05': ('Glucose trend input in the bolus calculator', 'usage/features/bolus-calculator.md', 'In Trio 1.0.2, the calculator selects glucose readings',
            'The bolus calculator selects readings newer than 20 minutes ago and subtracts the oldest selected glucose from the newest. The interval depends on the readings available, and delta is zero with fewer than two readings. The difference is not normalized to a fixed 15-minute interval.'),
    'F06': ('Backdated carbs and calculator safety gates', 'usage/features/bolus-calculator.md', '## Backdated carbohydrate entries',
            'A backdated meal calculation uses simulated COB and zero new carbs. Ordinary entries use existing COB plus new carbs capped at Max COB. The recommendation is zero if current glucose or minimum predicted glucose is below 54 mg/dL, or the last successful loop is more than 15 minutes old. Otherwise the implementation applies a nonnegative clamp, Max Bolus, Max IOB minus current IOB, and pump bolus rounding, in that order. There is no second nonnegative clamp after the headroom cap.'),
    'F07': ('Libre 3 and 3+ in Trio 1.0.2', 'configuration/settings/devices/cgm.md', '!!! info "Available in main / Trio 1.0.2"',
            'Trio 1.0.2 main includes the Libre 3/3+ driver, whose app menu label includes Beta. Upgrading to 1.0.2 requires re-pairing the existing sensor because the driver cannot retain the previous pairing. The release notes do not require a new sensor. Initial activation and recovery or re-pairing of a running sensor are distinct workflows.'),
    'F08': ('Export Settings CSV', 'configuration/settings/export-settings.md', '# Export Settings',
            'Settings → Export Settings saves selected configuration categories to CSV. Include Metadata, Therapy, Algorithm and Features for a useful review. English columns are Setting Category, Subcategory, Setting Name, Value and Unit. Percentages use display units while JSON factors use fractions; glucose rows use the selected display unit. Some values include stored/effective mode annotations. Export supports review and sharing, not automatic import or restoration.'),
    'F09': ('Garmin configuration and data transmission', 'configuration/settings/devices/smart-watch.md', '## Garmin configuration in Trio 1.0.2',
            'Configure the Garmin watchface and datafield independently in Trio. Watchface choices include Complication mode for compatible faces. Primary and secondary attributes are configurable. Changing the selected watchface disables transmission: configure Trio, change the face on the watch, then resume transmission. The Disable watchface data transmission control is inverted relative to isWatchfaceDataEnabled.'),
    'F10': ('Shortcut bolus permissions and safety checks', 'configuration/settings/features/shortcuts.md', '### Bolus',
            'Allow Bolusing with Shortcuts maps to bolusShortcut notAllowed or limitWithSafetyChecks. The enabled path validates Max Bolus, available current IOB, Max IOB headroom and cumulative boluses within the default six-minute lookback before rounding and enactment. A total at least 20% of the request causes rejection. Logging external insulin is a separate non-delivery action with a three-times-Max-Bolus bound.'),
    'F11': ('The meal bolus calculator already subtracts automated insulin represented in IOB', 'usage/features/bolus-calculator.md', 'The calculator already subtracts current IOB',
            'The calculator combines glucose correction, glucose trend and capped COB plus new-carbs coverage, then subtracts current IOB. Automated insulin represented in that IOB is already counted. Positive results are multiplied by Recommended Bolus Percentage and, if selected, Reduced Bolus Percentage. The optional Super Bolus component is added afterward. SMB Delivery Ratio separately scales automated SMB dosing. The respective default manual and automated percentages are 80% and 50%.'),
    'F12': ('SMB permission, UAM and interval eligibility', 'configuration/settings/algorithm/smb-settings.md', '## Permission, UAM and dose-cap selection in 1.0.2',
            'UAM alone does not enable SMB. The permission function considers override and schedule blocks, high Temp Target restrictions, and enabled Always, COB, After Carbs, low Temp Target and High Glucose conditions. Guard-glucose and maximum-delta checks can still block delivery. SMB Interval is clamped to 1–10 minutes and, when last bolus age is available, requires that age to be strictly greater than the interval. It is an eligibility gate rather than a delivery timer.')
}


def load_facts(root: Path):
    facts = json.loads((root / 'review/facts.json').read_text())
    for fact in facts:
        title, path, anchor, answer = TOPICS[fact['id']]
        fact['title'], fact['answer'], fact['status'] = title, answer, 'current'
        fact.pop('update', None)
        fact['evidence'] = [{'path': 'updated-docs/source/docs/' + path, 'anchor': anchor}] + [
            ref for ref in fact['evidence'] if not ref['path'].startswith('upstream/')]
    return facts
