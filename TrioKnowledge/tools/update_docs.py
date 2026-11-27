#!/usr/bin/env python3
"""Create a full local documentation edition, highlighted HTML and unified diffs."""
import difflib
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit, unquote

import markdown
from bs4 import BeautifulSoup
from latex2mathml.converter import convert as mathml

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / 'upstream/source'
OUTPUT = ROOT / 'updated-docs'
DOCS = OUTPUT / 'source/docs'
SITE = OUTPUT / 'site'
FACTS = json.loads((ROOT / 'knowledge/facts.json').read_text())
SHA = json.loads((ROOT / 'upstream/manifest.json').read_text())['app_commit']
CHANGES = {}


def replace(text, old, new, count=1):
    if text.count(old) != count:
        raise ValueError(f'Expected {count} occurrences of {old[:90]!r}, got {text.count(old)}')
    return text.replace(old, new)


def edit(path, ids, transform):
    target = DOCS / path
    original = UPSTREAM / 'docs' / path
    old = original.read_text() if original.exists() else ''
    new = transform(old)
    if old == new:
        raise ValueError('Edit made no change: ' + path)
    if ids:
        new += '\n\n## 1.0.2 source references\n\n'
        for fact in FACTS:
            if fact['id'] in ids:
                new += f"- **{fact['id']} — {fact['title']}**\n"
                for ref in fact['evidence']:
                    if not ref['path'].startswith('upstream/'):
                        new += f"    - [{ref['path']}:{ref['line']}]({ref['url']})\n"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new)
    CHANGES[path] = {'findings': ids, 'new_page': not old}


def apply_updates():
    edit('configuration/settings/closed-loop.md', ['F01', 'F02'], lambda _: '''# Dosing Modes

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
''')
    def setup(text):
        text = replace(text, '[**Step 8:** Enable Closed Loop](#step-8-enable-closed-loop)', '[**Step 8:** Choose Dosing Mode](#step-8-enable-closed-loop)')
        start = text.index('## **Step 8:** Enable Closed Loop')
        end = text.index('\n- - -', start)
        return text[:start] + '''## **Step 8:** Choose Dosing Mode {#step-8-enable-closed-loop}

After connecting your pump and CGM, open **Settings → Dosing Mode**. Trio 1.0.2 offers Closed Loop, Open Loop, Low Glucose Suspend and Basal Testing. The default is Open Loop, which displays recommendations without enacting automated dosing or low protection.

Closed Loop permits full automation subject to settings and safety checks. Low Glucose Suspend permits predictive reductions with effective Max IOB 0. Basal Testing uses low-only suspension and derives additional sensitivity constraints while preserving saved preferences. Read [Dosing Modes](settings/closed-loop.md) before choosing the mode for your intended workflow.

Earlier Closed Loop switch screenshots do not represent this picker. Manual actions are separate from automated enactment; choosing a mode does not itself validate an individual bolus.
''' + text[end:]
    edit('configuration/new-user-setup.md', ['F01','F02'], setup)
    edit('configuration/settings/index.md', ['F01','F08'], lambda t: replace(t, '__[Close The Loop](closed-loop.md)__', '__[Dosing Modes](closed-loop.md)__') + '\n\n## Export Settings\n\nUse [Export Settings](export-settings.md) to share a versioned configuration for review.\n')
    edit('configuration/settings/therapy/basal-rates.md', ['F02'], lambda t: t[:t.index('### Basal Testing')] + '''### Basal Testing

Trio 1.0.2 provides a dedicated [Basal Testing dosing mode](../closed-loop.md#basal-testing). It derives Max IOB 0, Autosens bounds 100%, Dynamic ISF and sigmoid off, and a threshold preference of at least 72 mg/dL, without overwriting your saved preferences. It permits low-glucose suspension rather than normal predictive adjustments. Entering the mode attempts to cancel an automatic temporary basal, subject to delivery-state checks. The mode is distinct from Low Glucose Suspend and from manually changing saved algorithm settings. Planning and interpreting a basal test also depends on food, activity and recent insulin; the mode alone does not establish that a test is appropriate.

''' + t[t.index('### Basal Adjustment'):])
    mode_note = '\n\n## Effective settings in constrained dosing modes\n\nIn [Basal Testing](../closed-loop.md#basal-testing), the effective Autosens Min and Max are both 100%, and Dynamic ISF / sigmoid are disabled. These derived values preserve the saved preferences. Low Glucose Suspend derives Max IOB 0 but does not impose those additional sensitivity constraints. Read [Dosing Modes](../closed-loop.md) when interpreting displayed or exported settings.\n'
    for path in ['configuration/settings/algorithm/autosens.md','configuration/settings/algorithm/dynamic-settings.md']:
        edit(path, ['F02'], lambda t: t + mode_note)
    def limits(t):
        t = replace(t, '**Setting Limits:** _1-30 units_', '**Setting Limits:** _0.5-30 units_')
        t = replace(t, 'This only limits manual boluses given on the Treatments screen.', 'The calculator caps its recommendation using this setting. Remote and Shortcut bolus commands also use it in their shared validation; it is not limited to the Treatments screen.')
        return t + '\n\n## Saved versus effective Max IOB\n\nLow Glucose Suspend and Basal Testing derive effective Max IOB 0 while retaining the saved preference. Basal Testing additionally changes effective sensitivity settings. These mode constraints do not establish a universal limit for every manual bolus entry path. See [Dosing Modes](../closed-loop.md) and the [calculator safety gates](../../../usage/features/bolus-calculator.md#recommendation-safety-gates).\n\nThe Max Bolus picker accepts 0.5–30 U in 0.5 U steps in `DecimalPickerSettings.swift`; available pump-specific settings and rounding can impose further constraints.\n'
    edit('configuration/settings/therapy/units-limits.md', ['F02','F06','F10'], limits)
    def smb(t):
        t = replace(t, '**Setting Limits:** _30-180 minutes_', '**Setting Limits:** _15-180 minutes (5-minute steps)_', 2)
        t = replace(t, 'The largest SMB Bill can receive is **1.0 unit** every 5 minutes.', 'The basal-minute cap in this example is **1.0 unit per eligible SMB** before other constraints. This does not guarantee delivery every five minutes.')
        start, end = t.index('## Max Allowed Glucose Rise for SMB'), t.index('## Are SMBs Allowed?')
        t = t[:start] + '''## Max Allowed Glucose Rise for SMB
**Default:** _20%_  
**Setting Limits:** _10%–40%_

The 1.0.2 Swift dosing engine disables SMBs when `glucoseStatus.maxDelta > min(configured fraction, 0.4) × current glucose`. Equality does not trigger this particular block. This is a comparison with current glucose and the computed maximum delta, not simply a percentage change divided by the previous glucose reading.

For example, if the computed maximum delta is 25 mg/dL and current glucose is 115 mg/dL, the default threshold is `0.2 × 115 = 23 mg/dL`. Because 25 exceeds 23, this check blocks SMB delivery on that determination. Passing this check alone does not promise a dose or a compensating high temporary basal; the rest of the determination still applies.

''' + t[end:]
        return t + '''

## Permission, UAM and dose-cap selection in 1.0.2

Enabling UAM is not itself an SMB-enabling condition. The permission function first considers override/scheduled SMB blocks and high Temp Target restrictions, then the enabled SMB conditions (Always, COB, After Carbs, low Temp Target, and High Glucose). Later guard-glucose and maximum-delta checks can still block delivery.

The simplified basal-minute formula assumes the relevant current profile basal, no overriding SMB/UAM-minute setting and no extra override factor. The code selects the UAM-minute branch when current IOB is positive and exceeds meal COB divided by carb ratio; otherwise it uses the SMB-minute branch. Active advanced overrides can replace the minutes and scale the basal factor. The defaults remain 30 minutes for both settings; allowable picker limits are not a recommendation to increase a limit.
'''
    edit('configuration/settings/algorithm/smb-settings.md', ['F03','F12'], smb)
    edit('configuration/settings/algorithm/additionals.md', ['F11','F12'], lambda t: replace(t, 'The minimum minutes since the last SMB or manual bolus that an automated SMB will be permitted.', 'The elapsed-time eligibility gate after the last SMB or manual bolus. In 1.0.2, the engine clamps this setting to 1–10 minutes and, when the last bolus age is available, requires that age to be strictly greater than the interval. It does not schedule a dose or change the underlying loop cadence.') + '\n\n## Manual recommendation versus automated SMB percentage\n\nSMB Delivery Ratio scales automated SMB calculations. [Recommended Bolus Percentage](../features/bolus-calculator.md) separately scales positive calculator recommendations. The defaults are 50% and 80% respectively; these controls are not interchangeable.\n')
    def remote(t):
        t = replace(t, 'No recent bolus >20% of the requested amount in the last 10 minutes', 'Boluses delivered since the command was sent total less than 20% of the requested amount (equality is rejected)')
        start, end = t.index('**Duplicate Bolus Prevention**'), t.index('**Time Window Validation**')
        t = t[:start] + '''**Duplicate Bolus Prevention**

Remote bolus validation sums delivered boluses since the original command timestamp. It rejects a request when that total is **greater than or equal to 20%** of the requested bolus. It does not use an individual-bolus comparison or a fixed ten-minute lookback.

For a synthetic 5 U command, the threshold is 1 U. Two boluses delivered after the command was sent, totaling exactly 1 U, trigger rejection. A bolus delivered before the command timestamp is outside this particular lookback. This example explains the validation rule, not a suggested dose.

The same validator is used by Shortcuts, whose caller instead uses the default six-minute lookback. Command age/expiry validation is a separate check.

''' + t[end:]
        t = replace(t, '| "Recent bolus detected" | Similar bolus in last 10 minutes | Wait 10 minutes or verify this isn\'t a duplicate |', '| "Recent bolus detected" | Boluses since the command timestamp total at least 20% of the request | Inspect delivered doses and command timing; do not resend based only on a timer |')
        return t
    edit('configuration/settings/features/remote-control.md', ['F04'], remote)
    def calc(t):
        t = replace(t, 'Your glucose trend (Delta) takes into account how much your glucose readings have changed over the last 15 minutes.', 'In Trio 1.0.2, the calculator selects glucose readings newer than 20 minutes ago and subtracts the oldest selected value from the newest. The actual interval depends on available readings; with fewer than two readings, delta is zero. It does not normalize this difference to a fixed 15-minute interval, despite the internal `fifteenMinutesInsulin` name.')
        return t + '''

## Backdated carbohydrate entries

For a backdated meal calculation, Trio uses simulated COB and sets new carbs to zero. For an ordinary entry, it adds existing COB and new carbs, capped at Max COB. This avoids counting a backdated entry both as newly entered carbs and as simulated remaining COB.

The calculator already subtracts current IOB, including automated insulin represented in that IOB. A late meal bolus should not be explained as ignoring all previously delivered UAM/SMB insulin. The calculation still depends on the accuracy and freshness of the stored glucose, COB and IOB inputs.

## Recommendation safety gates

The recommendation is zero if current glucose is below 54 mg/dL, minimum predicted glucose is below 54 mg/dL, or the last successful loop is more than 15 minutes old. These checks concern the calculated recommendation, not a universal prohibition on every insulin entry or delivery path.

Otherwise the implementation applies a nonnegative clamp, then Max Bolus, then `Max IOB − current IOB`, and finally pump bolus rounding. There is no second nonnegative clamp after the Max IOB headroom step; negative headroom therefore remains an implementation edge case rather than a guaranteed zero-result condition.

## Two different percentage controls

Positive manual-calculator results are multiplied by Recommended Bolus Percentage and, if selected, Reduced Bolus Percentage. The Super Bolus component is added afterward. SMB Delivery Ratio belongs to automated SMB dosing and is a separate control. See [calculator configuration](../../configuration/settings/features/bolus-calculator.md) and [SMB Delivery Ratio](../../configuration/settings/algorithm/additionals.md#smb-delivery-ratio).
'''
    edit('usage/features/bolus-calculator.md', ['F05','F06','F11'], calc)
    edit('configuration/settings/features/bolus-calculator.md', ['F06','F11'], lambda t: t + '\n\n## How the settings affect the recommendation\n\nRecommended Bolus Percentage scales a positive calculator result after current IOB has been subtracted; it is not the automated SMB Delivery Ratio. Reduced Bolus multiplies that positive result further, while Super Bolus is added afterward. The [calculator guide](../../../usage/features/bolus-calculator.md#recommendation-safety-gates) describes backdated COB, stale/low-glucose gates and the limit/rounding order.\n')
    edit('configuration/settings/features/shortcuts.md', ['F04','F10'], lambda t: replace(t, 'If [Allow Bolusing with Shortcuts](#allow-bolusing-with-shortcuts) is enabled, you will be able to use shortcuts to deliver a bolus.', '''If [Allow Bolusing with Shortcuts](#allow-bolusing-with-shortcuts) is enabled, the internal `bolusShortcut` selection permits the validated bolus path (`limitWithSafetyChecks` rather than `notAllowed`).

Before rounding and enactment, the shared validator checks Max Bolus, available current IOB, Max IOB headroom, and cumulative boluses within the default **six-minute** lookback. A recent total **greater than or equal to 20%** of the requested amount rejects the request. Enabling permission does not guarantee a request will be accepted.

Logging external insulin is a separate action that does not deliver through the pump; that path has a bound of three times Max Bolus. It should not be confused with requesting a pump bolus.'''))
    def cgm(t):
        t = replace(t, '!!! warning "You must build the `dev` branch to use the FreeStyle Libre 3 / 3 Plus CGM at this time"\n    The FreeStyle Libre 3 / 3 Plus CGM is in `dev` and is in open-beta for now. In the in-app menu, it is listed as "FreeStyle Libre 3 / 3+ (Beta)".', '''!!! info "Available in main / Trio 1.0.2"
    The pinned 1.0.2 app includes the Libre 3/3+ driver; `dev` is not required solely for Libre 3 availability. Its app-menu label still includes "(Beta)".

!!! warning "Upgrading to Trio 1.0.2: re-pair the sensor"
    The official 1.0.2 release notes say the changed driver cannot retain the previous pairing. Re-pair the existing sensor after the upgrade; the release notes do not require a new sensor. Read the [official version-specific upgrade note](https://github.com/nightscout/Trio/releases/tag/v1.0.2). Initial sensor activation and recovering/re-pairing a running sensor are different workflows.

!!! note "Driver-procedure validation scope"
    The detailed procedure retained below comes from the captured docs source. Sensor startup/recovery behavior depends on the pinned LibreLoop driver and the sensor's prior state; this alignment update does not independently validate every driver-screen instruction.''')
        return t
    edit('configuration/settings/devices/cgm.md', ['F07'], cgm)
    edit('includes/supported-cgms.md', ['F07'], lambda t: t.replace('Open-beta in `dev` branch', 'Included in main / 1.0.2; Beta label'))
    edit('install/build/mac/update.md', ['F07'], lambda t: t + '\n\n## Libre 3 / 3+ upgrade note for Trio 1.0.2\n\nThe 1.0.2 driver update requires re-pairing an existing Libre 3/3+ sensor. The [official release notes](https://github.com/nightscout/Trio/releases/tag/v1.0.2) state that a new sensor is not required. Check this separately from pump-session continuity and follow the version-specific CGM instructions.\n')
    def watch(t):
        t = replace(t, 'As long as nothing is published in Garmin Connect IQ, every Garmin watch needs to be individually compiled. You can do this yourself using VS Code with the monkeyC plugin and a Garmin SDK. If not, see the link below for the released watches.', 'The sideloading instructions below are retained from the upstream guide. Current Connect IQ distribution and model support were not verified in this code-alignment review; check the relevant project release before choosing an installation method.')
        return t + '''

## Garmin configuration in Trio 1.0.2

After adding the device, configure the supported **watchface** and **datafield** independently in Trio. The available watchface choices include a Complication mode for compatible faces with Connect IQ complication slots. Configure primary/secondary attribute choices as appropriate for the selected integration.

Changing the selected watchface in Trio automatically disables watchface data transmission. Follow the displayed sequence: choose the configuration in Trio, change the face on the watch, then resume transmission when prompted. The **Disable watchface data transmission** control is inverted relative to the internal `isWatchfaceDataEnabled` value: turning Disable on makes the internal enabled flag false.

This describes the verified configuration controls and transition behavior. It does not confirm every watch model, current app-store listing or connection state. Existing screenshots may predate these controls.
'''
    edit('configuration/settings/devices/smart-watch.md', ['F09'], watch)
    edit('configuration/settings/features/index.md', ['F08'], lambda t: t + '\n\n## Review and share configuration\n\n[Export Settings](../export-settings.md) saves a selected-category CSV for configuration review. It is available from the main Settings screen.\n')
    edit('configuration/settings/export-settings.md', ['F08','F02'], lambda _: '''# Export Settings

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
''')


EXTENSIONS = ['extra','admonition','toc','pymdownx.details','pymdownx.superfences','pymdownx.tabbed','pymdownx.arithmatex','pymdownx.tilde','pymdownx.caret','pymdownx.mark','pymdownx.smartsymbols']


def expand_includes(text, current, depth=0):
    if depth > 8:
        raise ValueError('Include nesting too deep')
    def include(match):
        name, options = match.groups()
        source_root = UPSTREAM if current.resolve().is_relative_to(UPSTREAM.resolve()) else OUTPUT / 'source'
        docs_root = source_root / 'docs'
        candidates = [current.parent / name, docs_root / name, source_root / name]
        path = next((p.resolve() for p in candidates if p.is_file()), None)
        if path is None or not path.is_relative_to(source_root.resolve()):
            raise ValueError('Missing/unsafe include ' + name)
        body = path.read_text()
        for option in ['start','end']:
            value = re.search(option + r'="([^"]+)"', options)
            if value:
                if value[1] not in body:
                    raise ValueError('Missing include marker ' + value[1])
                body = body.split(value[1],1)[1 if option == 'start' else 0]
        # Include-relative Markdown links must be rebased to the containing page.
        def rebase(link):
            url = link[1]
            if urlsplit(url).scheme or url.startswith(('#','/')):
                return link[0]
            part, _, fragment = url.partition('#')
            destination = path.parent / part
            return '](' + os.path.relpath(destination,current.parent) + ('#'+fragment if fragment else '') + ')'
        body = re.sub(r'\]\(([^\s)]+)\)', rebase, body)
        return expand_includes(body,current,depth+1)
    return re.sub(r'{%\s*include-markdown\s+"([^"]+)"(.*?)%}', include, text, flags=re.S)


def render(text, current):
    text = expand_includes(text, current)
    body = markdown.markdown(text, extensions=EXTENSIONS, extension_configs={'pymdownx.tabbed':{'alternate_style':True},'pymdownx.arithmatex':{'generic':False}}, output_format='html')
    soup = BeautifulSoup(body, 'html.parser')
    for formula in soup.select('.arithmatex'):
        script = formula.find('script')
        if script:
            rendered = mathml(script.get_text(), display='block' if 'display' in script.get('type', '') else 'inline')
            formula.clear()
            formula.append(BeautifulSoup(rendered, 'html.parser'))
    return str(soup)


STYLE = '''body{font:16px/1.65 system-ui;margin:0;color:#232035;background:#f7f6fa}header,main{max-width:1000px;margin:auto;padding:22px}header{border-bottom:1px solid #dcd7e8}article{background:white;padding:28px;border-radius:12px}a{color:#51338e;overflow-wrap:anywhere}img,video{max-width:100%;height:auto}pre{white-space:pre-wrap;background:#f3f0f8;padding:14px;overflow-wrap:anywhere}code{overflow-wrap:anywhere}table{display:block;max-width:100%;overflow-x:auto;border-collapse:collapse}th,td{border:1px solid #dcd7e8;padding:8px;text-align:left}.changed-block,ins{background:#fff1a8;box-shadow:-4px 0 #b48700;padding-left:6px;text-decoration:none}.new-page article{border-left:5px solid #b48700}.removed{background:#ffe5e5}del{background:#ffd1d1;color:#822}.diff-line{display:block;white-space:pre-wrap}.diff-add{background:#dcf4df}.diff-remove{background:#ffe1e1}.admonition,details{padding:12px 16px;background:#f1edf8;margin:16px 0}.admonition-title{font-weight:600}.tabbed-set input{display:none}.tabbed-labels{display:flex;flex-wrap:wrap;gap:12px;font-weight:600}.tabbed-block{border-left:2px solid #ccc;padding-left:14px}.note{font-size:14px;color:#5b5469}.toolbar{display:flex;gap:15px;flex-wrap:wrap}button,input{font:inherit;padding:9px;border:1px solid #aaa;border-radius:7px}.hide-highlights .changed-block{background:transparent;box-shadow:none;padding-left:0}h1,h2,h3,h4{line-height:1.3;scroll-margin-top:15px}h2{margin-top:32px}#doc-list li{margin:7px 0}summary{cursor:pointer}@media(max-width:600px){header,main{padding:14px}article{padding:16px}}@media print{header button,.toolbar{display:none}article{padding:0}body{background:white}.changed-block{print-color-adjust:exact}details{break-inside:avoid}}'''


def main():
    OUTPUT.mkdir(exist_ok=True)
    shutil.copytree(UPSTREAM, OUTPUT / 'source', dirs_exist_ok=True)
    apply_updates()
    SITE.mkdir(exist_ok=True)
    pages, corpus, link_issues = [], [], []
    files = sorted(DOCS.rglob('*.md'))
    for path in files:
        relative = str(path.relative_to(DOCS))
        old_path = UPSTREAM / 'docs' / relative
        old = old_path.read_text() if old_path.exists() else ''
        text = path.read_text()
        rendered = BeautifulSoup(render(text,path),'html.parser')
        previous = BeautifulSoup(render(old,old_path),'html.parser')
        rendered_changed = str(rendered) != str(previous)
        old_blocks = {str(node) for node in previous.find_all(['p','li','h1','h2','h3','h4','h5','h6','td','th','pre','blockquote'])}
        for node in rendered.find_all(['p','li','h1','h2','h3','h4','h5','h6','td','th','pre','blockquote']):
            if str(node) not in old_blocks:
                node['class'] = list(node.get('class',[])) + ['changed-block']
                node['data-change'] = 'added-or-revised'
        target = SITE / Path(relative).with_suffix('.html')
        target.parent.mkdir(parents=True,exist_ok=True)
        # Keep all images/media local; transform source links into rendered-page links.
        for element in rendered.find_all(['a','img','video','source']):
            attr = 'href' if element.name == 'a' else 'src'
            url = element.get(attr)
            if not url or url.startswith(('#','mailto:','tel:','data:')):
                continue
            parts = urlsplit(url)
            if parts.scheme or parts.netloc:
                continue
            local = (DOCS / unquote(parts.path).lstrip('/')) if parts.path.startswith('/') else path.parent / unquote(parts.path)
            local = local.resolve()
            if not local.is_relative_to((OUTPUT / 'source').resolve()):
                link_issues.append({'page':relative,'url':url,'reason':'outside source tree'})
                continue
            if element.name == 'a' and local.suffix == '.md' and local.is_relative_to(DOCS.resolve()):
                destination = SITE / local.relative_to(DOCS.resolve()).with_suffix('.html')
            else:
                destination = local
            element[attr] = os.path.relpath(destination,target.parent) + ('#'+parts.fragment if parts.fragment else '')
            if not local.exists():
                link_issues.append({'page':relative,'url':url,'reason':'upstream target missing'})
        title = rendered.find('h1')
        title = title.get_text(' ',strip=True) if title else Path(relative).stem.replace('-', ' ').title()
        changed = text != old or rendered_changed
        is_include = relative.startswith('includes/')
        diff = ''.join(difflib.unified_diff(expand_includes(old,old_path).splitlines(True),expand_includes(text,path).splitlines(True),fromfile='upstream/'+relative,tofile='updated/'+relative))
        if changed:
            diff_path = OUTPUT / 'diffs' / (relative+'.diff')
            diff_path.parent.mkdir(parents=True,exist_ok=True)
            diff_path.write_text(diff)
        diff_html = ''.join('<span class="diff-line '+('diff-add' if line.startswith('+') and not line.startswith('+++') else 'diff-remove' if line.startswith('-') and not line.startswith('---') else '')+'">'+html.escape(line.rstrip('\n'))+'</span>' for line in diff.splitlines(True))
        home = os.path.relpath(OUTPUT / 'index.html',target.parent)
        graph = os.path.relpath(ROOT / 'knowledge/explorer.html',target.parent)
        source_url = os.path.relpath(path,target.parent)
        upstream_url = os.path.relpath(old_path,target.parent) if old_path.exists() else None
        original_link = f'<a href="{html.escape(upstream_url)}">Original Markdown</a>' if upstream_url else 'New page'
        banner = 'Updated text is highlighted in yellow; removals and replacements appear in the full diff below.' if changed else 'Unchanged from the captured source. Inherited content has not all been revalidated against 1.0.2.'
        document = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} · Trio 1.0.2 local edition</title><style>{STYLE}</style><header><nav class="toolbar"><a href="{home}">All documents</a><a href="{graph}">Ask questions / evaluate settings</a><a href="{source_url}">Updated Markdown</a>{original_link}</nav><p class="note">Local alignment draft · main / 1.0.2 · {SHA[:12]}. Upstream authorship and licensing retained.</p><p>{banner}</p><button id="toggle" type="button" aria-pressed="true">Hide change highlighting</button></header><main><article>{rendered}</article>{'<details><summary>Full changes: added (+) and removed (−) text</summary><pre>'+diff_html+'</pre></details>' if changed else ''}</main><script>document.getElementById('toggle').onclick=function(){{const hidden=document.body.classList.toggle('hide-highlights');this.textContent=hidden?'Show change highlighting':'Hide change highlighting';this.setAttribute('aria-pressed',String(!hidden));}};</script></html>'''
        target.write_text(document)
        pages.append({'path':relative,'title':title,'html':'site/'+str(Path(relative).with_suffix('.html')),'changed':changed,'source_changed':text!=old,'include':is_include,'sha256':hashlib.sha256(text.encode()).hexdigest(),'original_sha256':hashlib.sha256(old.encode()).hexdigest() if old else None,**CHANGES.get(relative,{})})
        corpus.append({'kind':'updated-docs','title':title,'path':'updated-docs/source/docs/'+relative,'url':'../updated-docs/site/'+str(Path(relative).with_suffix('.html')),'start_line':1,'end_line':len(text.splitlines()),'text':text})
    (OUTPUT / 'manifest.json').write_text(json.dumps({'app_commit':SHA,'source_documents':len(files),'rendered_documents':len(pages),'changed_documents':sum(p['changed'] for p in pages),'new_documents':sum(p.get('new_page',False) for p in pages),'pages':pages,'inherited_link_issues':link_issues},indent=2)+'\n')
    (OUTPUT / 'search-corpus.json').write_text(json.dumps(corpus)+'\n')
    entries=''.join(f'<li data-title="{html.escape(p["title"].lower(),quote=True)}"><a href="{html.escape(p["html"])}">{html.escape(p["title"])}</a> · {"UPDATED" if p["changed"] else "unchanged"}{" · include fragment" if p["include"] else ""}</li>' for p in pages)
    overview=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Trio 1.0.2 · Full updated documentation</title><style>{STYLE}</style><header><h1>Trio 1.0.2 documentation</h1><p>Complete local edition with reviewed corrections highlighted.</p><nav class="toolbar"><a href="../knowledge/explorer.html">Ask questions / evaluate settings</a><a href="../review/DOCUMENTATION-UPDATE-REPORT.md">Alignment review</a><a href="source/LICENSE">Upstream license</a><a href="manifest.json">Coverage and change manifest</a></nav></header><main><article><p><strong>{len(pages)} documents</strong> · {sum(p['changed'] for p in pages)} changed or new · all original pages, include fragments and assets retained.</p><p>This is a local alignment draft against main / v1.0.2 ({SHA[:12]}), not an official upstream release. Yellow text blocks are added or revised. Each changed page includes a full red/green diff; all pages retain original-source links. Old screenshots are preserved and may depict earlier controls. Detailed driver procedures, hardware behavior and unedited material are not all revalidated.</p><label for="search">Find a document</label> <input id="search" type="search" placeholder="SMB, calculator, dosing, export…"><ul id="doc-list">{entries}</ul></article></main><script>document.getElementById('search').oninput=function(){{const q=this.value.toLowerCase();for(const row of document.querySelectorAll('#doc-list li'))row.hidden=!row.dataset.title.includes(q);}};</script></html>'''
    (OUTPUT / 'index.html').write_text(overview)
    combined=''.join((OUTPUT / 'diffs' / (p['path']+'.diff')).read_text() for p in pages if p['changed'])
    (OUTPUT / 'all-changes.diff').write_text(combined)
    print(json.dumps({'rendered':len(pages),'changed':sum(p['changed'] for p in pages),'inherited_link_issues':len(link_issues)},indent=2))


if __name__ == '__main__':
    main()
