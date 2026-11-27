"""Derive simple CSV field mappings from the pinned Trio export implementation."""
import re


def export_fields(text, catalog):
    known = {f['id']: f for f in catalog}
    fields = {}
    for match in re.finditer(r'\baddSetting\(', text):
        start = match.end()
        depth, quoted, escaped, end = 1, False, False, start
        while end < len(text) and depth:
            char = text[end]
            if quoted:
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            end += 1
        block = text[start:end]
        name = re.search(r'name:\s*(?:String\(\s*localized:\s*)?"([^"\n]+)"', block)
        if not name or '\\(' in name[1] or 'value:' not in block:
            continue
        refs = re.findall(r'(preferences|trioSettings|pumpSettings)\s*\.\s*(\w+)', block.split('value:', 1)[1])
        refs = [r for r in refs if r[1] != 'units']
        if not refs or name[1] == 'Dynamic ISF':
            continue
        model = {'preferences': 'Preferences', 'trioSettings': 'TrioSettings', 'pumpSettings': 'PumpSettings'}[refs[0][0]]
        id = model + '.' + refs[0][1]
        if id in known:
            fields[name[1]] = {'id': id, 'name': refs[0][1], 'type': known[id]['type'],
                               'source': 'Trio/Sources/Modules/SettingsExport/SettingsExportStateModel.swift',
                               'line': text[:match.start()].count('\n') + 1}
    return fields
