#!/usr/bin/env python3
"""Offline evidence retrieval and mechanical configuration review; no pump connection."""
import argparse
import csv
from decimal import Decimal
import json
import math
from pathlib import Path
import re
import sqlite3

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / 'knowledge' / name).read_text())


def ask(question, limit=6):
    facts = read('facts.json')
    words = set(re.findall(r'[a-z0-9]+', question.lower())) - {'what', 'how', 'does', 'the', 'a', 'is', 'in', 'trio', 'to', 'and', 'for', 'of', 'my', 'can', 'are', 'do', 'with', 'settings', 'i', 'when', 'it', 'that', 'this', 'me', 'an', 'be', 'should', 'which', 'why'}
    if not words:
        return {'question': question, 'answers': [], 'evidence': [], 'note': 'Please include a topic such as UAM, IOB, dosing mode or bolus percentage.'}
    scored = []
    for fact in facts:
        keytext = ' '.join(fact['keywords']).lower()
        score = sum(2 for w in words if re.search(r'\b' + re.escape(w) + r'\b', keytext))
        score += sum(3 for phrase in fact['keywords'] if ' ' in phrase and phrase.lower() in question.lower())
        if score:
            scored.append((score, fact))
    scored.sort(key=lambda x: -x[0])
    if scored:
        scored = [(score, fact) for score, fact in scored if score >= scored[0][0] * 0.65]
    conn = sqlite3.connect(ROOT / 'knowledge/trio.sqlite')
    conn.row_factory = sqlite3.Row
    expression = ' OR '.join('"' + w + '"' for w in sorted(words))
    rows = conn.execute('SELECT c.*, bm25(search, 5, 1) AS score FROM search JOIN chunks c ON c.id=search.rowid WHERE search MATCH ? ORDER BY score LIMIT ?', (expression, limit)).fetchall()
    conn.close()
    return {'question': question, 'release': read('build-summary.json')['app_commit'],
            'method': 'Offline extractive retrieval. Curated answers are relevant evidence, not a generated or exhaustive answer to every question.',
            'answers': [{'id': f['id'], 'title': f['title'], 'status': f['status'], 'answer': f['answer'], 'evidence': f['evidence']} for _, f in scored[:3]],
            'evidence': [dict(row) for row in rows]}


# English CSV export names from SettingsExportStateModel. Other/localized rows remain visible as unassessed.
CSV_NAMES = {
    'Dosing Mode': 'dosingMode', 'Glucose Units': 'units',
    'Maximum Insulin on Board (IOB)': 'maxIOB', 'Maximum Bolus': 'maxBolus', 'Maximum Basal Rate': 'maxBasal',
    'Maximum Carbs on Board (COB)': 'maxCOB', 'Recommended Bolus Percentage': 'overrideFactor',
    'Reduced Bolus Percentage': 'fattyMealFactor', 'Super Bolus Percentage': 'sweetMealFactor',
    'Enable SMB Always': 'enableSMBAlways', 'Enable SMB With COB': 'enableSMBWithCOB',
    'Enable SMB With Temptarget': 'enableSMBWithTemptarget', 'Enable SMB After Carbs': 'enableSMBAfterCarbs',
    'Allow SMB With High Temptarget': 'allowSMBWithHighTemptarget', 'Enable UAM': 'enableUAM',
    'Max SMB Basal Minutes': 'maxSMBBasalMinutes', 'Max UAM Basal Minutes': 'maxUAMSMBBasalMinutes',
    'SMB Interval': 'smbInterval', 'SMB Delivery Ratio': 'smbDeliveryRatio',
    'Autosens Max': 'autosensMax', 'Autosens Min': 'autosensMin',
    'Max Daily Safety Multiplier': 'maxDailySafetyMultiplier', 'Current Basal Safety Multiplier': 'currentBasalSafetyMultiplier',
    'Enable Dynamic ISF': 'useNewFormula', 'Enable Sigmoid': 'sigmoid',
    'Minimum Safety Threshold': 'threshold_setting', 'Max Allowed Glucose Rise for SMB': 'maxDeltaBGthreshold',
    'Enable SMB With High Glucose': 'enableSMB_high_bg', 'Rewind Resets Autosens': 'rewindResetsAutosens',
    'Enable Reduced Bolus Option': 'fattyMeals', 'Enable Super Bolus Option': 'sweetMeals',
    'High Glucose Target': 'enableSMB_high_bg_target', 'Duration of Insulin Action': 'insulinActionCurve'
}
MODE_NAMES = {'Closed Loop': 'closed', 'Open Loop': 'open', 'Low Glucose Suspend': 'lowGlucoseSuspend', 'Basal Testing': 'basalTesting'}


def input_settings(path):
    if path.suffix.lower() != '.csv':
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError('Duplicate JSON key: ' + key)
                result[key] = value
            return result
        data = json.loads(path.read_text(), object_pairs_hook=pairs)
        if not isinstance(data, dict):
            raise ValueError('Expected a JSON object')
        entries = []
        for key, value in data.items():
            if key in ('preferences', 'settings', 'pumpSettings') and isinstance(value, dict):
                model = {'preferences': 'Preferences', 'settings': 'TrioSettings', 'pumpSettings': 'PumpSettings'}[key]
                entries.extend((model + '.' + k, v) for k, v in value.items())
            else:
                entries.append((key, value))
        return entries, [], {}, []
    entries, skipped, metadata, notes = [], [], {}, []
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not {'Setting Name', 'Value', 'Unit', 'Setting Category'}.issubset(reader.fieldnames or []):
            raise ValueError('CSV must use the English Trio export headers: Setting Category, Subcategory, Setting Name, Value, Unit')
        for row in reader:
            name, raw, unit = row['Setting Name'], row['Value'], row['Unit']
            if row['Setting Category'] == 'Metadata' and name != 'Dosing Mode':
                metadata[name] = raw
                continue
            if name == 'Dynamic ISF':
                stored = raw.split(' (mode is using ', 1)[0]
                if stored not in ('Disabled', 'Sigmoid', 'Logarithmic'):
                    skipped.append({'name': name, 'reason': 'Unrecognized Dynamic ISF selection'})
                    continue
                entries.append(('useNewFormula', stored != 'Disabled'))
                if stored != 'Disabled':
                    entries.append(('sigmoid', stored == 'Sigmoid'))
                if stored == 'Disabled':
                    notes.append({'setting': 'sigmoid', 'note': 'CSV hides stored sigmoid when Dynamic ISF is disabled; stored value remains unknown.'})
                if stored != raw:
                    notes.append({'setting': 'useNewFormula', 'export_annotation': raw})
                continue
            key = CSV_NAMES.get(name)
            if key is None:
                skipped.append({'name': name, 'reason': 'Unmapped export row; not evaluated'})
                continue
            if '(mode is using ' in raw:
                notes.append({'setting': key, 'export_annotation': raw})
                raw = raw.split(' (mode is using ', 1)[0]
            if key == 'dosingMode':
                value = MODE_NAMES.get(raw, raw)
            elif key == 'units':
                value = raw
            elif raw in ('Enabled', 'Disabled', 'true', 'false'):
                value = raw in ('Enabled', 'true')
            else:
                value = float(raw.rstrip('%'))
                if unit == '%' or raw.endswith('%'):
                    value /= 100
                if unit == 'mmol/L':
                    value *= 18
                    notes.append({'setting': key, 'conversion': 'CSV mmol/L converted to stored mg/dL (x18)'})
            entries.append((key, value))
    return entries, skipped, metadata, notes


def evaluate(path):
    catalog = read('settings-catalog.json')
    aliases = {}
    for field in catalog:
        for key in {field['name'], field['json_key'], field['id'], field['model'] + '.' + field['json_key']}:
            aliases.setdefault(key, []).append(field)
    entries, skipped, metadata, notes = input_settings(path)
    findings, values, checked = [], {}, []
    def add(level, code, message, evidence=None):
        findings.append({'level': level, 'code': code, 'message': message, 'evidence': evidence or []})
    # Follow the app's explicit-new-key-first legacy migration.
    legacy = [(k, v) for k, v in entries if k in ('closedLoop', 'TrioSettings.closedLoop')]
    entries = [(k, v) for k, v in entries if k not in ('closedLoop', 'TrioSettings.closedLoop')]
    if legacy:
        if any(type(v) is not bool for _, v in legacy):
            add('error', 'legacy-type', 'closedLoop must be a JSON boolean')
        elif not any(k in ('dosingMode', 'TrioSettings.dosingMode') for k, _ in entries):
            entries.append(('dosingMode', 'closed' if legacy[-1][1] else 'open'))
            notes.append({'migration': 'Legacy closedLoop mapped to dosingMode using the app decoder rule'})
        else:
            notes.append({'migration': 'Explicit dosingMode takes precedence over legacy closedLoop'})
    for key, value in entries:
        options = aliases.get(key, [])
        if len(options) != 1:
            skipped.append({'name': key, 'reason': 'Unknown or ambiguous setting; not evaluated'})
            continue
        field = options[0]
        name, typ = field['name'], field['type']
        evidence = [{'path': 'knowledge/code/' + field['source'], 'line': field['line']}]
        if name in values:
            add('error', 'duplicate-setting', f'{name} supplied through multiple aliases; remove duplicates.', evidence)
            continue
        valid = True
        if typ == 'Bool':
            valid = type(value) is bool
        elif typ in ('Decimal', 'Int'):
            valid = type(value) in (float, int) and math.isfinite(value) and (typ != 'Int' or value == int(value))
        elif typ == 'DosingMode':
            valid = value in ('closed', 'open', 'lowGlucoseSuspend', 'basalTesting')
        elif typ == 'BolusShortcutLimit':
            valid = value in ('notAllowed', 'limitWithSafetyChecks')
        elif typ == 'GlucoseUnits':
            valid = value in ('mg/dL', 'mmol/L')
        elif typ == 'InsulinCurve':
            valid = value in ('rapid-acting', 'ultra-rapid', 'bilinear')
        else:
            skipped.append({'name': key, 'reason': f'Type {typ} is cataloged but not validated'})
            continue
        if not valid:
            add('error', 'type-or-enum', f'{name}: invalid {typ} value {value!r}', evidence)
            continue
        values[name] = value
        checked.append(field['id'])
        picker = field.get('picker')
        if picker and typ in ('Decimal', 'Int'):
            ref = [{'path': 'knowledge/code/' + picker['source'], 'line': picker['line']}]
            if not picker['min'] <= value <= picker['max']:
                add('review', 'outside-picker-range', f"{name}={value}; picker range {picker['min']}–{picker['max']}. This is a UI bound, not proof the app rejects imported values.", ref)
            else:
                offset = (Decimal(str(value)) - Decimal(str(picker['min']))) / Decimal(str(picker['step']))
                if abs(offset - offset.to_integral_value()) > Decimal('0.00001'):
                    add('review', 'off-picker-step', f"{name}={value} does not align with picker step {picker['step']}.", ref)
    if metadata.get('App Version') and not re.match(r'^1\.0\.2(?:$|[^0-9])', metadata['App Version']):
        add('review', 'version-mismatch', 'Export is not labeled 1.0.2; this knowledge base is pinned to 1.0.2.')
    if all(k in values for k in ('autosensMin', 'autosensMax')) and values['autosensMin'] > values['autosensMax']:
        add('review', 'autosens-order', 'autosensMin exceeds autosensMax; bounds are inconsistent.', ['F02'])
    mode = values.get('dosingMode')
    effective = dict(values)
    if mode is None:
        add('incomplete', 'mode-missing', 'Dosing mode not supplied; effective automation and mode overrides cannot be established.', ['F01', 'F02'])
    elif mode == 'open':
        add('behavior', 'open-loop', 'Automated dosing enactment is off; forecasts do not mean insulin was delivered.', ['F01'])
    elif mode in ('lowGlucoseSuspend', 'basalTesting'):
        effective['maxIOB'] = 0
        add('behavior', 'mode-max-iob', 'Effective maxIOB is 0 in this mode; the stored preference is preserved. Negative IOB replenishment can occur in LGS.', ['F01', 'F02'])
        if mode == 'basalTesting':
            effective.update(autosensMin=1, autosensMax=1, useNewFormula=False, sigmoid=False)
            if 'threshold_setting' in values:
                effective['threshold_setting'] = max(values['threshold_setting'], 72)
            else:
                add('incomplete', 'threshold-missing', 'Basal Testing uses max(stored threshold, 72 mg/dL); stored threshold is not supplied.', ['F02'])
            add('behavior', 'basal-testing', 'Basal Testing fixes sensitivity bounds at 1, disables dynamic formula/sigmoid and only permits low-glucose suspension.', ['F02'])
    if values.get('enableUAM') is True:
        conditions = ['enableSMBAlways', 'enableSMBWithCOB', 'enableSMBAfterCarbs', 'enableSMBWithTemptarget', 'enableSMB_high_bg']
        if all(values.get(k) is False for k in conditions):
            add('behavior', 'uam-without-smb-permission', 'UAM is on but all supplied SMB enabling conditions are off; UAM alone does not enable SMB.', ['F12'])
        elif not any(values.get(k) is True for k in conditions):
            add('incomplete', 'smb-permission-unknown', 'UAM alone does not enable SMB. Some SMB permission settings are absent, so eligibility is unknown.', ['F12'])
    if values.get('allowSMBWithHighTemptarget') is True:
        add('behavior', 'high-target-permission', 'High Temp Target does not by itself block SMB when this permission is on; other conditions still apply.', ['F12'])
    if 'smbInterval' in values:
        add('behavior', 'interval-gate', 'SMB interval is elapsed-time eligibility, not guaranteed delivery frequency.', ['F12'])
    if 'overrideFactor' in values:
        add('behavior', 'manual-factor', f"Recommended Bolus Percentage is {values['overrideFactor'] * 100:g}%; it scales positive manual calculator recommendations, separately from SMB Delivery Ratio.", ['F11'])
    if not checked:
        add('incomplete', 'nothing-evaluated', 'No supported setting values were evaluated.')
    return {'scope': 'Mechanical configuration review, not dosing optimization, clinical safety certification or pump simulation.',
            'release': read('build-summary.json')['app_commit'], 'metadata': metadata,
            'checked_settings': checked, 'provided_valid_values': values, 'effective_known_values': effective,
            'missing_values': 'Not defaulted. Absent settings, schedules, active overrides, glucose/pump state and treatment history remain unknown.',
            'unassessed': skipped, 'input_notes': notes, 'findings': findings,
            'errors': sum(f['level'] == 'error' for f in findings)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    query = sub.add_parser('ask')
    query.add_argument('question')
    query.add_argument('--limit', type=int, default=6)
    query.add_argument('--json', action='store_true')
    review = sub.add_parser('evaluate')
    review.add_argument('file', type=Path)
    graph = sub.add_parser('neighbors')
    graph.add_argument('topic')
    args = parser.parse_args()
    try:
        if args.command == 'ask':
            result = ask(args.question, args.limit)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(result.get('method', result.get('note', '')))
                for answer in result['answers']:
                    print(f"\n{answer['id']}: {answer['title']} [{answer['status']}]\n{answer['answer']}")
                    for evidence in answer['evidence']:
                        print(f"  {evidence['local_path']}:{evidence['line']}\n  {evidence['url']}")
                print('\nRetrieved passages:')
                for hit in result['evidence']:
                    print(f"\n[{hit['kind']}] {hit['path']}:{hit['start_line']}–{hit['end_line']}\n{hit['url']}\n{hit['text'][:1000]}")
        elif args.command == 'evaluate':
            result = evaluate(args.file)
            print(json.dumps(result, indent=2))
            raise SystemExit(2 if result['errors'] else 0)
        else:
            data = read('graph.json')
            ids = {n['id'] for n in data['nodes'] if args.topic.lower() in (n['id'] + ' ' + n['label']).lower()}
            edges = [e for e in data['edges'] if e['from'] in ids or e['to'] in ids]
            neighbor_ids = ids | {e[side] for e in edges for side in ('from', 'to')}
            print(json.dumps({'nodes': [n for n in data['nodes'] if n['id'] in neighbor_ids], 'edges': edges}, indent=2))
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(2, f'Error: {error}\n')


if __name__ == '__main__':
    main()
