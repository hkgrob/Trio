/* Shared browser/Node logic. No network, persistent storage, or pump access. */
const TrioBrowserKB = (() => {
    function parseJSON(text) {
        // JSON.parse discards duplicate keys; reject them before aliases are resolved.
        let i = 0;
        const ws = () => { while (/\s/.test(text[i] || '') && i < text.length) i++; };
        function string() {
            const start = i++;
            while (i < text.length) {
                if (text[i] === '\\') { i += 2; continue; }
                if (text[i++] === '"') return JSON.parse(text.slice(start, i));
            }
            throw Error('Unterminated JSON string');
        }
        function value() {
            ws();
            if (text[i] === '"') return string();
            if (text[i] === '{') {
                i++; ws(); const result = Object.create(null);
                if (text[i] === '}') { i++; return result; }
                while (i < text.length) {
                    ws(); if (text[i] !== '"') throw Error('Expected a JSON property name');
                    const key = string(); ws();
                    if (Object.hasOwn(result, key)) throw Error('Duplicate JSON key: ' + key);
                    if (text[i++] !== ':') throw Error('Expected : after JSON property');
                    result[key] = value(); ws();
                    const end = text[i++];
                    if (end === '}') return result;
                    if (end !== ',') throw Error('Expected , or } in JSON object');
                }
            } else if (text[i] === '[') {
                i++; ws(); const result = [];
                if (text[i] === ']') { i++; return result; }
                while (i < text.length) {
                    result.push(value()); ws(); const end = text[i++];
                    if (end === ']') return result;
                    if (end !== ',') throw Error('Expected , or ] in JSON array');
                }
            } else {
                const match = /^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(text.slice(i));
                if (match) { i += match[0].length; return JSON.parse(match[0]); }
            }
            throw Error('Invalid JSON near character ' + i);
        }
        const result = value(); ws();
        if (i !== text.length) throw Error('Unexpected text after JSON');
        return result;
    }

    function parseCSV(text) {
        text = text.replace(/^\uFEFF/, '');
        const rows = []; let row = [], field = '', quoted = false, afterQuote = false;
        for (let i = 0; i < text.length; i++) {
            const c = text[i];
            if (quoted) {
                if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
                else if (c === '"') { quoted = false; afterQuote = true; }
                else field += c;
            } else if (c === '"' && !field && !afterQuote) quoted = true;
            else if (c === ',' || c === '\n' || c === '\r') {
                row.push(field); field = ''; afterQuote = false;
                if (c !== ',') {
                    if (c === '\r' && text[i + 1] === '\n') i++;
                    if (row.some(x => x !== '')) rows.push(row);
                    row = [];
                }
            } else {
                if (afterQuote || c === '"') throw Error('Malformed CSV quoting');
                field += c;
            }
        }
        if (quoted) throw Error('Unterminated quoted CSV field');
        if (field || row.length || afterQuote) { row.push(field); rows.push(row); }
        if (!rows.length) throw Error('The settings file is empty');
        return rows;
    }

    const csvNames = {
        'Dosing Mode':'dosingMode', 'Glucose Units':'units', 'Maximum Insulin on Board (IOB)':'maxIOB',
        'Maximum Bolus':'maxBolus', 'Maximum Basal Rate':'maxBasal', 'Maximum Carbs on Board (COB)':'maxCOB',
        'Recommended Bolus Percentage':'overrideFactor', 'Reduced Bolus Percentage':'fattyMealFactor',
        'Super Bolus Percentage':'sweetMealFactor', 'Enable SMB Always':'enableSMBAlways',
        'Enable SMB With COB':'enableSMBWithCOB', 'Enable SMB With Temptarget':'enableSMBWithTemptarget',
        'Enable SMB After Carbs':'enableSMBAfterCarbs', 'Allow SMB With High Temptarget':'allowSMBWithHighTemptarget',
        'Enable UAM':'enableUAM', 'Max SMB Basal Minutes':'maxSMBBasalMinutes',
        'Max UAM Basal Minutes':'maxUAMSMBBasalMinutes', 'SMB Interval':'smbInterval',
        'SMB Delivery Ratio':'smbDeliveryRatio', 'Autosens Max':'autosensMax', 'Autosens Min':'autosensMin',
        'Max Daily Safety Multiplier':'maxDailySafetyMultiplier', 'Current Basal Safety Multiplier':'currentBasalSafetyMultiplier',
        'Enable Dynamic ISF':'useNewFormula', 'Enable Sigmoid':'sigmoid', 'Minimum Safety Threshold':'threshold_setting',
        'Max Allowed Glucose Rise for SMB':'maxDeltaBGthreshold', 'Enable SMB With High Glucose':'enableSMB_high_bg',
        'Rewind Resets Autosens':'rewindResetsAutosens', 'Enable Reduced Bolus Option':'fattyMeals',
        'Enable Super Bolus Option':'sweetMeals', 'High Glucose Target':'enableSMB_high_bg_target',
        'Duration of Insulin Action':'insulinActionCurve'
    };
    const modeNames = {'Closed Loop':'closed', 'Open Loop':'open', 'Low Glucose Suspend':'lowGlucoseSuspend', 'Basal Testing':'basalTesting'};

    function parseSettings(text, filename) {
        const entries = [], skipped = [], metadata = {}, notes = [];
        if (!filename.toLowerCase().endsWith('.csv')) {
            const object = parseJSON(text.replace(/^\uFEFF/, ''));
            if (!object || typeof object !== 'object' || Array.isArray(object)) throw Error('Expected a JSON object');
            const models = {preferences:'Preferences', settings:'TrioSettings', pumpSettings:'PumpSettings'};
            for (const [key, value] of Object.entries(object)) {
                if (Object.hasOwn(models, key) && value && typeof value === 'object' && !Array.isArray(value)) {
                    for (const [name, v] of Object.entries(value)) entries.push([models[key] + '.' + name, v]);
                } else entries.push([key, value]);
            }
        } else {
            const rows = parseCSV(text), headers = rows.shift();
            const required = ['Setting Name','Value','Unit','Setting Category'];
            if (!required.every(x => headers.includes(x))) throw Error('Use the English Trio Settings CSV export: Setting Category, Subcategory, Setting Name, Value, Unit');
            if (new Set(headers).size !== headers.length) throw Error('Duplicate CSV column names');
            for (const cells of rows) {
                if (cells.length !== headers.length) throw Error('CSV row has a different number of columns than its header');
                const row = Object.fromEntries(headers.map((h,i) => [h,cells[i]]));
                const name = row['Setting Name'], unit = row.Unit;
                let raw = row.Value;
                if (row['Setting Category'] === 'Metadata' && name !== 'Dosing Mode') { metadata[name] = raw; continue; }
                if (name === 'Dynamic ISF') {
                    const stored = raw.split(' (mode is using ')[0];
                    if (!['Disabled','Sigmoid','Logarithmic'].includes(stored)) { skipped.push({name,reason:'Unrecognized Dynamic ISF selection'}); continue; }
                    entries.push(['useNewFormula', stored !== 'Disabled']);
                    if (stored !== 'Disabled') entries.push(['sigmoid',stored === 'Sigmoid']);
                    else notes.push({setting:'sigmoid',note:'CSV hides stored sigmoid when Dynamic ISF is disabled; stored value remains unknown.'});
                    if (stored !== raw) notes.push({setting:'useNewFormula',export_annotation:raw});
                    continue;
                }
                const key = Object.hasOwn(csvNames,name) ? csvNames[name] : null;
                if (!key) { skipped.push({name,reason:'Unmapped export row; not evaluated'}); continue; }
                if (raw.includes('(mode is using ')) { notes.push({setting:key,export_annotation:raw}); raw = raw.split(' (mode is using ')[0]; }
                let value;
                if (key === 'dosingMode') value = modeNames[raw] || raw;
                else if (key === 'units') value = raw;
                else if (['Enabled','Disabled','true','false'].includes(raw)) value = ['Enabled','true'].includes(raw);
                else {
                    const number = raw.replace(/%$/, '').trim();
                    if (!number || !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(number)) throw Error('Invalid numeric value for ' + name);
                    value = Number(number);
                    if (unit === '%' || raw.endsWith('%')) value /= 100;
                    if (unit === 'mmol/L') { value *= 18; notes.push({setting:key,conversion:'CSV mmol/L converted to stored mg/dL (x18)'}); }
                }
                entries.push([key,value]);
            }
        }
        return {entries,skipped,metadata,notes};
    }

    function evaluate(text, filename, catalog, release) {
        let {entries,skipped,metadata,notes} = parseSettings(text,filename);
        const aliases = new Map(), findings = [], values = Object.create(null), checked = [];
        for (const f of catalog) for (const key of new Set([f.name,f.json_key,f.id,f.model+'.'+f.json_key])) {
            if (!aliases.has(key)) aliases.set(key,[]);
            aliases.get(key).push(f);
        }
        const add = (level,code,message,evidence=[]) => findings.push({level,code,message,evidence});
        const legacy = entries.filter(([k]) => ['closedLoop','TrioSettings.closedLoop'].includes(k));
        entries = entries.filter(([k]) => !['closedLoop','TrioSettings.closedLoop'].includes(k));
        if (legacy.length) {
            if (legacy.some(([,v]) => typeof v !== 'boolean')) add('error','legacy-type','closedLoop must be a JSON boolean');
            else if (!entries.some(([k]) => ['dosingMode','TrioSettings.dosingMode'].includes(k))) {
                entries.push(['dosingMode',legacy[legacy.length-1][1]?'closed':'open']);
                notes.push({migration:'Legacy closedLoop mapped to dosingMode using the app decoder rule'});
            } else notes.push({migration:'Explicit dosingMode takes precedence over legacy closedLoop'});
        }
        const enums = {DosingMode:['closed','open','lowGlucoseSuspend','basalTesting'],BolusShortcutLimit:['notAllowed','limitWithSafetyChecks'],GlucoseUnits:['mg/dL','mmol/L'],InsulinCurve:['rapid-acting','ultra-rapid','bilinear']};
        for (const [key,value] of entries) {
            const options = aliases.get(key) || [];
            if (options.length !== 1) { skipped.push({name:key,reason:'Unknown or ambiguous setting; not evaluated'}); continue; }
            const f = options[0], name = f.name, typ = f.type;
            const evidence = [{path:'knowledge/code/'+f.source,line:f.line}];
            if (Object.hasOwn(values,name)) { add('error','duplicate-setting',name+' supplied through multiple aliases; remove duplicates.',evidence); continue; }
            let valid;
            if (typ === 'Bool') valid = typeof value === 'boolean';
            else if (['Decimal','Int'].includes(typ)) valid = typeof value === 'number' && Number.isFinite(value) && (typ !== 'Int' || Number.isInteger(value));
            else if (Object.hasOwn(enums,typ)) valid = enums[typ].includes(value);
            else { skipped.push({name:key,reason:'Type '+typ+' is cataloged but not validated'}); continue; }
            if (!valid) { add('error','type-or-enum',name+': invalid '+typ+' value '+JSON.stringify(value),evidence); continue; }
            values[name] = value; checked.push(f.id);
            const p = f.picker;
            if (p && ['Decimal','Int'].includes(typ)) {
                const ref = [{path:'knowledge/code/'+p.source,line:p.line}];
                if (value < p.min || value > p.max) add('review','outside-picker-range',`${name}=${value}; picker range ${p.min}–${p.max}. This is a UI bound, not proof the app rejects imported values.`,ref);
                else { const offset=(value-p.min)/p.step; if (Math.abs(offset-Math.round(offset)) > 0.00001) add('review','off-picker-step',`${name}=${value} does not align with picker step ${p.step}.`,ref); }
            }
        }
        if (metadata['App Version'] && !/^1\.0\.2(?:$|[^0-9])/.test(metadata['App Version'])) add('review','version-mismatch','Export is not labeled 1.0.2; this knowledge base is pinned to 1.0.2.');
        if (Object.hasOwn(values,'autosensMin') && Object.hasOwn(values,'autosensMax') && values.autosensMin > values.autosensMax) add('review','autosens-order','autosensMin exceeds autosensMax; bounds are inconsistent.',['F02']);
        const mode=values.dosingMode, effective={...values};
        if (mode === undefined) add('incomplete','mode-missing','Dosing mode not supplied; effective automation and mode overrides cannot be established.',['F01','F02']);
        else if (mode === 'open') add('behavior','open-loop','Automated dosing enactment is off; forecasts do not mean insulin was delivered.',['F01']);
        else if (['lowGlucoseSuspend','basalTesting'].includes(mode)) {
            effective.maxIOB=0;
            add('behavior','mode-max-iob','Effective maxIOB is 0 in this mode; the stored preference is preserved. Negative IOB replenishment can occur in LGS.',['F01','F02']);
            if (mode === 'basalTesting') {
                Object.assign(effective,{autosensMin:1,autosensMax:1,useNewFormula:false,sigmoid:false});
                if (Object.hasOwn(values,'threshold_setting')) effective.threshold_setting=Math.max(values.threshold_setting,72);
                else add('incomplete','threshold-missing','Basal Testing uses max(stored threshold, 72 mg/dL); stored threshold is not supplied.',['F02']);
                add('behavior','basal-testing','Basal Testing fixes sensitivity bounds at 1, disables dynamic formula/sigmoid and only permits low-glucose suspension.',['F02']);
            }
        }
        if (values.enableUAM === true) {
            const conditions=['enableSMBAlways','enableSMBWithCOB','enableSMBAfterCarbs','enableSMBWithTemptarget','enableSMB_high_bg'];
            if (conditions.every(k=>values[k]===false)) add('behavior','uam-without-smb-permission','UAM is on but all supplied SMB enabling conditions are off; UAM alone does not enable SMB.',['F12']);
            else if (!conditions.some(k=>values[k]===true)) add('incomplete','smb-permission-unknown','UAM alone does not enable SMB. Some SMB permission settings are absent, so eligibility is unknown.',['F12']);
        }
        if (values.allowSMBWithHighTemptarget === true) add('behavior','high-target-permission','High Temp Target does not by itself block SMB when this permission is on; other conditions still apply.',['F12']);
        if (Object.hasOwn(values,'smbInterval')) add('behavior','interval-gate','SMB interval is elapsed-time eligibility, not guaranteed delivery frequency.',['F12']);
        if (Object.hasOwn(values,'overrideFactor')) add('behavior','manual-factor',`Recommended Bolus Percentage is ${Number((values.overrideFactor*100).toFixed(8))}%; it scales positive manual calculator recommendations, separately from SMB Delivery Ratio.`,['F11']);
        if (!checked.length) add('incomplete','nothing-evaluated','No supported setting values were evaluated.');
        return {scope:'Mechanical configuration review, not dosing optimization, clinical safety certification or pump simulation.',release,metadata,checked_settings:checked,provided_valid_values:values,effective_known_values:effective,missing_values:'Not defaulted. Absent settings, schedules, active overrides, glucose/pump state and treatment history remain unknown.',unassessed:skipped,input_notes:notes,findings,errors:findings.filter(f=>f.level==='error').length};
    }

    const stops=new Set('what how does the a is in trio to and for of my can are do with settings i when it that this me an be should which why already please tell explain'.split(' '));
    const tokens=s=>(s.replace(/([a-z])([A-Z])/g,'$1 $2').toLowerCase().match(/[a-z0-9]+/g)||[]).filter(w=>!stops.has(w));
    function ask(question, facts, corpus, report=null) {
        const words=[...new Set(tokens(question))];
        if (!words.length) return {answers:[],evidence:[],configuration:[],note:'Include a topic such as UAM, IOB, dosing mode or bolus percentage.'};
        const escape=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
        let scored=facts.map(f=>({fact:f,score:words.reduce((n,w)=>n+(new RegExp('\\b'+escape(w)+'\\b','i').test(f.keywords.join(' '))?2:0),0)+f.keywords.filter(k=>k.includes(' ')&&question.toLowerCase().includes(k.toLowerCase())).length*3})).filter(x=>x.score>0).sort((a,b)=>b.score-a.score);
        if (scored.length) scored=scored.filter(x=>x.score>=scored[0].score*0.65);
        const ranked=corpus.map(c=>{
            const titleWords=new Set(tokens(c.title)), bodyWords=new Set(tokens(c.text));
            const hits=words.filter(w=>titleWords.has(w)||bodyWords.has(w)).length;
            const weight=c.kind==='current-document'?1.5:c.kind==='current-reference'?1.4:c.kind==='code'?0.85:1;
            return {chunk:c,score:hits?weight*(hits*2+words.filter(w=>titleWords.has(w)).length*3)/Math.sqrt(1+bodyWords.size/200):0};
        }).filter(x=>x.score>0).sort((a,b)=>b.score-a.score);
        const configuration=[];
        if (report) for (const [name,value] of Object.entries(report.provided_valid_values)) {
            const aliases={overrideFactor:'recommended bolus percentage',fattyMealFactor:'reduced bolus percentage',sweetMealFactor:'super bolus percentage',threshold_setting:'minimum safety threshold',useNewFormula:'dynamic isf',sigmoid:'dynamic isf'};
            const terms=tokens(name+' '+(aliases[name]||''));
            if (words.some(w=>terms.includes(w))) configuration.push({name,stored:value,effective:report.effective_known_values[name]});
        }
        return {answers:scored.slice(0,3).map(x=>x.fact),evidence:ranked.slice(0,6).map(x=>x.chunk),configuration,
                note:scored.length?'Answers and supporting passages from the current Trio 1.0.2 reference.':'No prepared answer directly covers this question. Relevant current-source passages are shown below.'};
    }
    return {parseJSON,parseCSV,parseSettings,evaluate,ask,csvNames};
})();
if (typeof module !== 'undefined') module.exports=TrioBrowserKB;
