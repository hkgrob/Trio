/* Full configuration review: preserve every row, interpret schedules and explain interactions. */
const TrioConfiguration = (() => {
    const base = typeof TrioBrowserKB !== 'undefined' ? TrioBrowserKB : require('./browser-kb.js');
    const references = {
        modes:'configuration/settings/closed-loop.md', limits:'configuration/settings/therapy/units-limits.md',
        basal:'configuration/settings/therapy/basal-rates.md', isf:'configuration/settings/therapy/isf.md',
        carbRatio:'configuration/settings/therapy/carb-ratios.md', target:'configuration/settings/therapy/glucose-targets.md',
        smb:'configuration/settings/algorithm/smb-settings.md', dynamic:'configuration/settings/algorithm/dynamic-settings.md',
        autosens:'configuration/settings/algorithm/autosens.md', additionals:'configuration/settings/algorithm/additionals.md',
        calculator:'usage/features/bolus-calculator.md', meal:'configuration/settings/features/meal-settings.md',
        overrides:'usage/features/overrides.md', tempTargets:'usage/features/temp-targets.md',
        remote:'configuration/settings/features/remote-control.md', shortcuts:'configuration/settings/features/shortcuts.md',
        export:'configuration/settings/export-settings.md', notifications:'configuration/settings/notifications/trio-notifications.md'
    };
    const doc = name => ({path:'updated-docs/source/docs/'+references[name],url:'../updated-docs/site/'+references[name].replace(/\.md$/,'.html')});
    const sensitive = name => /secret|password|credential|api.?key|access.?token|auth.?token|authorization|nightscout.?url|server.?url|username|email/i.test(name);
    function redact(value, name='') {
        if (sensitive(name)) return '[redacted credential or connection detail]';
        if (Array.isArray(value)) return value.map(v=>redact(v,name));
        if (value && typeof value==='object') return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,redact(v,k)]));
        if (typeof value==='string') return value.replace(/https?:\/\/[^\s]+/gi,'[redacted connection URL]');
        return value;
    }
    function minuteOfDay(value) {
        const match = /^(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)?$/i.exec(String(value).trim());
        if (!match) return null;
        let hour=Number(match[1]), minute=Number(match[2]);
        if (minute>59 || (match[3] ? hour<1||hour>12 : hour>23)) return null;
        if (match[3]) hour=hour%12+(match[3].toUpperCase()==='PM'?12:0);
        return hour*60+minute;
    }
    const timeLabel = minute => String(Math.floor(minute/60)).padStart(2,'0')+':'+String(minute%60).padStart(2,'0');
    const scheduleKinds = {'Basal Rates':'basal','Insulin Sensitivities':'isf','Carb Ratios':'carbRatio','Glucose Targets':'target'};
    const formatNumber = n => Number(Number(n).toFixed(4));
    function review(text, filename, catalog, fields, release) {
        const rows=[], schedules={basal:[],isf:[],carbRatio:[],target:[]}, presets=[], metadata={}, scalars={}, customFindings=[], duplicates=new Set(), counts={};
        const alias = new Map();
        for (const field of catalog) for (const key of [field.name,field.json_key,field.id,field.model+'.'+field.json_key]) alias.set(key,field);
        function add(level,code,title,message,evidence=[],settings=[]) { customFindings.push({level,code,title,message,evidence,settings}); }
        function scalar(key,value,row) {
            const field=alias.get(key), name=field?.name||key;
            row.key=name;
            if (Object.hasOwn(scalars,name)) { duplicates.add(name); row.assessment='conflict'; return; }
            scalars[name]=value; row.assessment=field?'interpreted':'context';
        }
        function number(raw,unit) {
            const cleaned=String(raw).split(' (mode is using ')[0].trim();
            if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?%?$/i.test(cleaned)) return null;
            let value=Number(cleaned.replace(/%$/,''));
            if (!Number.isFinite(value)) return null;
            if (unit==='%'||cleaned.endsWith('%')) value/=100;
            if (/^mmol\/L(?:\/U)?$/i.test(unit)) value*=18;
            return value;
        }
        function retain(row) {
            row.id='R'+(rows.length+1); row.value=redact(row.value,row.name);
            counts[row.category]=(counts[row.category]||0)+1; rows.push(row); return row;
        }
        function schedule(kind,start,raw,unit,row) {
            const minute=minuteOfDay(start), value=typeof raw==='number'?raw:number(raw,unit);
            const valid=minute!==null&&value!==null&&Number.isFinite(value)&&(kind==='basal'?value>=0:value>0);
            schedules[kind].push({start,minute,value,unit,valid,row_id:row.id}); row.assessment=valid?'schedule':'invalid';
            if (!valid) add('error','schedule-value','Invalid '+kind+' schedule row',row.name+' needs a valid time and '+(kind==='basal'?'nonnegative':'positive')+' value.',[doc(kind)],[row.id]);
        }
        if (filename.toLowerCase().endsWith('.csv')) {
            const parsed=base.parseCSV(text), headers=parsed.shift();
            if (!['Setting Category','Subcategory','Setting Name','Value','Unit'].every(h=>headers.includes(h)) || new Set(headers).size!==headers.length) throw Error('Use the English Trio Settings CSV export with its five distinct columns.');
            for (const cells of parsed) {
                if (cells.length!==headers.length) throw Error('CSV column count does not match the header.');
                const item=Object.fromEntries(headers.map((h,i)=>[h,cells[i]]));
                const row=retain({category:item['Setting Category'],subcategory:item.Subcategory,name:item['Setting Name'],value:item.Value,unit:item.Unit,assessment:'context'});
                const name=row.name, unit=row.unit, raw=String(row.value), kind=scheduleKinds[row.subcategory];
                if (row.category==='Metadata'&&name!=='Dosing Mode') { metadata[name]=row.value;row.assessment='metadata';continue; }
                if (sensitive(name)) { row.assessment='redacted';continue; }
                if (kind) {
                    const time=/\(([^)]+)\)/.exec(name);
                    schedule(kind,time?.[1]||'',raw,unit,row);continue;
                }
                if (/Presets$/.test(row.category)) { presets.push(row);row.assessment='preset';continue; }
                const rawStored=raw.split(' (mode is using ')[0];
                if (name==='Dynamic ISF') {
                    if (!['Disabled','Sigmoid','Logarithmic'].includes(rawStored)) { row.assessment='invalid';add('error','dynamic-selection','Unknown Dynamic ISF selection',rawStored,[doc('dynamic')],[row.id]);continue; }
                    scalar('useNewFormula',rawStored!=='Disabled',row);
                    if (rawStored!=='Disabled') scalar('sigmoid',rawStored==='Sigmoid',{assessment:'interpreted'});
                    continue;
                }
                const mapping=fields[name];
                const key=mapping?.name || base.csvNames[name];
                if (!key) continue;
                let value;
                if (key==='dosingMode') value=({'Closed Loop':'closed','Open Loop':'open','Low Glucose Suspend':'lowGlucoseSuspend','Basal Testing':'basalTesting'})[rawStored]||rawStored;
                else if (key==='bolusShortcut') value=rawStored==='Enabled'?'limitWithSafetyChecks':rawStored==='Disabled'?'notAllowed':rawStored;
                else if (['Enabled','Disabled','true','false'].includes(rawStored)) value=['Enabled','true'].includes(rawStored);
                else if (mapping?.type==='Decimal'||mapping?.type==='Int'||(!mapping&&number(rawStored,unit)!==null)) value=number(rawStored,unit)??rawStored;
                else value=rawStored;
                scalar(key,value,row);
            }
        } else {
            const parsed=base.parseJSON(text.replace(/^\uFEFF/,''));
            if (!parsed||typeof parsed!=='object'||Array.isArray(parsed)) throw Error('Expected a settings JSON object.');
            const modelNames={preferences:'Preferences',settings:'TrioSettings',pumpSettings:'PumpSettings'};
            function entry(key,value,category) {
                const row=retain({category,subcategory:'',name:key,value,unit:'stored units',assessment:'context'});
                if (sensitive(key)) {row.assessment='redacted';return;}
                if (alias.has(key)||['closedLoop','TrioSettings.closedLoop'].includes(key)) scalar(key,value,row);
            }
            for (const [key,value] of Object.entries(parsed)) {
                if (Object.hasOwn(modelNames,key)&&value&&typeof value==='object'&&!Array.isArray(value)) {
                    for (const [k,v] of Object.entries(value)) entry(modelNames[key]+'.'+k,v,key);
                } else if (['basalProfile','basal_profile','carbRatios','carb_ratios','insulinSensitivities','insulin_sensitivities','bgTargets','bg_targets'].includes(key)) {
                    const kind=key.includes('basal')?'basal':/carb/i.test(key)?'carbRatio':/sensitiv/i.test(key)?'isf':'target';
                    const array=Array.isArray(value)?value:value?.schedule||value?.sensitivities||value?.targets;
                    if (!Array.isArray(array)) {entry(key,value,'Therapy');continue;}
                    const unit=value?.units||'mg/dL';
                    for (const part of array) {
                        const raw=part.rate??part.ratio??part.sensitivity??part.low??part.value;
                        const row=retain({category:'Therapy',subcategory:kind,name:key+' ('+(part.start??part.time??'')+')',value:raw,unit,assessment:'context'});
                        const converted=(kind==='isf'||kind==='target')&&/^mmol/i.test(unit)&&typeof raw==='number'?raw*18:raw;
                        schedule(kind,part.start??part.time??'',converted,unit,row);
                    }
                } else if (/presets/i.test(key)) { const row=retain({category:'Presets',subcategory:key,name:key,value,unit:'',assessment:'preset'});presets.push(row); }
                else if (key==='metadata'&&value&&typeof value==='object') { for(const [k,v] of Object.entries(value)){metadata[k]=redact(v,k);retain({category:'Metadata',subcategory:'',name:k,value:v,unit:'',assessment:'metadata'});} }
                else entry(key,value,'Settings');
            }
        }
        for(const key of duplicates) {delete scalars[key];add('error','duplicate-setting','Conflicting setting entries',key+' appears more than once. It is excluded from effective-value calculations until the conflict is resolved.',[doc('export')],[key]);}
        const mechanical=base.evaluate(JSON.stringify(scalars),'normalized.json',catalog,release);
        const values={...mechanical.provided_valid_values}, effective={...mechanical.effective_known_values};
        // Retain typed enum/context fields even when the base primitive validator has no enum table.
        for(const [key,value] of Object.entries(scalars)) if(!Object.hasOwn(values,key)&&!mechanical.findings.some(f=>f.level==='error'&&f.message.startsWith(key+':'))) {
            const field=alias.get(key);
            if (field && !['Bool','Int','Decimal'].includes(field.type) && typeof value==='string') {values[key]=value;effective[key]=value;}
        }
        mechanical.metadata=metadata;
        if(metadata['App Version']&&!/^1\.0\.2(?:$|[^0-9])/.test(String(metadata['App Version']))) add('review','export-version','Export version differs from the reference','This export is '+metadata['App Version']+'; the accepted documentation describes 1.0.2.',[doc('export')]);
        for(const [kind,entries] of Object.entries(schedules)) {
            entries.sort((a,b)=>(a.minute??Infinity)-(b.minute??Infinity));
            const times=new Set();
            for(const point of entries) if(point.minute!==null) {if(times.has(point.minute)){point.valid=false;add('error','duplicate-schedule-time','Duplicate '+kind+' start time',point.start+' occurs more than once.',[doc(kind)],[point.row_id]);}times.add(point.minute);}
            if(entries.length&&entries[0].minute!==0) add('incomplete','schedule-midnight','Incomplete '+kind+' schedule','A midnight entry is missing; a complete 24-hour profile cannot be established.',[doc(kind)]);
            if(!entries.length) add('incomplete','missing-schedule-'+kind,'Missing '+kind+' schedule','The export does not supply this therapy schedule; no values are assumed.',[doc(kind)]);
        }
        const basal=schedules.basal, complete=basal.length&&basal[0].minute===0&&basal.every(e=>e.valid);
        const dailyBasal=complete?formatNumber(basal.reduce((sum,e,i)=>sum+e.value*((basal[i+1]?.minute??1440)-e.minute)/60,0)):null;
        const maxProfileBasal=complete?Math.max(...basal.map(e=>e.value)):null;
        const sections=[];
        function section(id,title,summary,evidence,settings=[]) {sections.push({id,title,summary,evidence,settings});}
        const mode=effective.dosingMode;
        section('automation','Automation and dosing mode',mode===undefined?'Dosing mode is missing. Actual automation cannot be established from this export.':mode==='closed'?'Closed Loop permits automated dosing, subject to settings, connected devices and current safety checks.':mode==='open'?'Open Loop does not enact automated insulin decisions. Enabled SMB options remain saved but cannot cause automated delivery in this mode.':mode==='lowGlucoseSuspend'?'LGS uses effective Max IOB 0 and predictive reductions. Saved Max IOB is preserved; negative IOB can be replenished to zero.':'Basal Testing uses low-only suspension, effective Max IOB 0, Autosens 100%, and Dynamic ISF off.',[doc('modes')],['dosingMode','maxIOB']);
        const conditions=['enableSMBAlways','enableSMBWithCOB','enableSMBAfterCarbs','enableSMBWithTemptarget','enableSMB_high_bg'];
        const enabled=conditions.filter(k=>effective[k]===true), unknown=conditions.filter(k=>!Object.hasOwn(effective,k));
        section('smb','SMB and UAM permissions',enabled.length?'Enabled SMB conditions: '+enabled.join(', ')+'. UAM '+(effective.enableUAM===true?'is enabled':effective.enableUAM===false?'is disabled':'was not supplied')+'. Eligibility still depends on glucose/IOB forecasts, targets, overrides, timing and safety checks.':unknown.length?'Some SMB permission fields are absent, so eligibility is unknown.':'All SMB enabling conditions are off. UAM alone does not grant SMB permission.',[doc('smb')],conditions.concat(['enableUAM','allowSMBWithHighTemptarget','smbInterval']));
        if(enabled.length&&effective.maxIOB===0) add('behavior','zero-iob-with-smb','SMB permissions with effective Max IOB 0','The permissions are saved, but positive-IOB correction is constrained. Negative IOB replenishment remains possible; a permission is not proof of a delivered dose.',[doc('smb'),doc('modes')],['maxIOB',...enabled]);
        if(effective.enableSMBAlways===true) add('behavior','smb-condition-redundancy','SMB Always takes precedence','Individual COB/After-Carbs/Temp-Target/High-Glucose permissions are redundant while Always is enabled. A High Glucose Target is not a universal SMB floor.',[doc('smb')],conditions);
        if(effective.enableSMB_high_bg===true&&!Object.hasOwn(effective,'enableSMB_high_bg_target')) add('incomplete','smb-high-target-missing','High-glucose SMB threshold missing','This condition is enabled but its target was not exported.',[doc('smb')],['enableSMB_high_bg','enableSMB_high_bg_target']);
        section('therapy','Therapy profiles and delivery limits',dailyBasal===null?'A complete valid basal schedule is needed to calculate programmed daily basal and baseline limit interactions.':`Programmed profile basal totals ${dailyBasal} U/day, with a highest scheduled rate of ${maxProfileBasal} U/hr. This is scheduled basal, not measured total daily insulin or actual delivered basal.`,[doc('basal'),doc('limits')],['maxBasal','maxBolus','maxIOB']);
        if(maxProfileBasal!==null&&typeof values.maxBasal==='number'&&maxProfileBasal>values.maxBasal) add('review','basal-above-limit','Scheduled basal exceeds Maximum Basal','The highest exported basal rate is above the configured Maximum Basal. Check the source export and pump/profile configuration; no setting is changed here.',[doc('limits'),doc('basal')],['maxBasal']);
        const intervalCaps=complete?basal.map(e=>({start:timeLabel(e.minute),profile_basal:e.value,
            nominal_smb_cap:typeof effective.maxSMBBasalMinutes==='number'?formatNumber(e.value*effective.maxSMBBasalMinutes/60):null,
            nominal_uam_cap:typeof effective.maxUAMSMBBasalMinutes==='number'?formatNumber(e.value*effective.maxUAMSMBBasalMinutes/60):null,
            nominal_temp_basal_limit:['maxBasal','maxDailySafetyMultiplier','currentBasalSafetyMultiplier'].every(k=>typeof effective[k]==='number')?formatNumber(Math.min(effective.maxBasal,effective.maxDailySafetyMultiplier*maxProfileBasal,effective.currentBasalSafetyMultiplier*e.value)):null})):[];
        const inactive=[];
        const off=(names,reason)=>names.forEach(name=>{if(Object.hasOwn(values,name))inactive.push({name,stored:values[name],reason});});
        if(mode==='open') off(conditions.concat(['maxSMBBasalMinutes','maxUAMSMBBasalMinutes','smbDeliveryRatio']),'Open Loop does not enact automated dosing.');
        if(mode==='basalTesting') off(['maxIOB','autosensMin','autosensMax','useNewFormula','sigmoid'],'The dosing mode derives an effective value instead of using the saved preference.');
        if(effective.useNewFormula===false) off(['adjustmentFactor','adjustmentFactorSigmoid','sigmoid'],'Dynamic ISF is disabled.');
        else if(effective.useNewFormula===true) off(effective.sigmoid===true?['adjustmentFactor']:effective.sigmoid===false?['adjustmentFactorSigmoid']:[],'The other Dynamic ISF formula is selected.');
        if(effective.fattyMeals===false) off(['fattyMealFactor'],'The Reduced Bolus option is disabled.');
        if(effective.sweetMeals===false) off(['sweetMealFactor'],'The Super Bolus option is disabled.');
        if(effective.useFPUconversion===false) off(['delay','minuteInterval','individualAdjustmentFactor'],'Fat and protein conversion is disabled.');
        if(effective.useCustomPeakTime===false) off(['insulinPeakTime'],'Custom peak time is disabled; the selected insulin curve supplies its default peak.');
        section('sensitivity','Sensitivity and Dynamic ISF',effective.useNewFormula===true?'Dynamic ISF is enabled using '+(effective.sigmoid===true?'the sigmoid formula':effective.sigmoid===false?'the logarithmic formula':'an unreported formula selection')+'. Runtime TDD sufficiency and active adjustments still matter.':effective.useNewFormula===false?'Dynamic ISF is disabled. Saved formula factors are not applied by that feature. Autosens and profile schedules remain separate inputs.':'The Dynamic ISF selection was not supplied.',[doc('dynamic'),doc('autosens')],['useNewFormula','sigmoid','autosensMin','autosensMax','adjustmentFactor','adjustmentFactorSigmoid','tddAdjBasal']);
        const factor=effective.overrideFactor;
        const reduced=effective.fattyMeals===true&&typeof factor==='number'&&typeof effective.fattyMealFactor==='number'?formatNumber(factor*effective.fattyMealFactor*100):null;
        section('meals','Meal calculator and carbohydrate handling',typeof factor==='number'?`Positive calculator recommendations use ${formatNumber(factor*100)}% Recommended Bolus Percentage${reduced!==null?`; selecting Reduced Bolus yields a combined ${reduced}% factor`:''}. Current IOB is already subtracted. Super Bolus is added afterward when selected; SMB Delivery Ratio is separate.`:'Recommended Bolus Percentage was not supplied. Calculator percentages, current IOB/COB and carbohydrate schedules are needed to explain a particular recommendation.',[doc('calculator'),doc('meal')],['overrideFactor','fattyMeals','fattyMealFactor','sweetMeals','sweetMealFactor','maxCOB','maxMealAbsorptionTime']);
        section('presets','Overrides and temporary targets',presets.length?`${presets.length} preset rows are included. Presets describe saved choices, not which override or temporary target is active now. A preset can change the meaning of the baseline settings only when actually activated.`:'No preset rows were exported. Absence does not establish that no override or temporary target is active.',[doc('overrides'),doc('tempTargets')]);
        section('permissions','Devices, remote access and notifications','Device/service/notification rows are retained below. An exported permission or selected device does not prove connectivity, delivery, alarm permission or runtime health. Shortcut and remote bolus validation remain distinct from automated dosing.',[doc('remote'),doc('shortcuts'),doc('notifications')],['bolusShortcut','cgm','smoothGlucose','useLiveActivity']);
        section('history','What Nightscout history can add','Glucose entries, delivered-treatment history, profiles and device status can help explain actual outcomes and active adjustments. A static configuration alone cannot establish glucose control, current IOB/COB, whether SMBs were delivered, or why a particular loop was blocked.',[doc('export')]);
        const findings=[...mechanical.findings,...customFindings];
        const invalidNames=new Set(mechanical.findings.filter(f=>f.level==='error'&&f.code==='type-or-enum').map(f=>f.message.split(':')[0]));
        for(const row of rows) if(invalidNames.has(row.key)) row.assessment='invalid';
        return {...mechanical,provided_valid_values:values,effective_known_values:effective,findings,errors:findings.filter(f=>f.level==='error').length,
            rows,presets,schedules,sections,inactive_settings:inactive,derived:{programmed_daily_basal:dailyBasal,highest_profile_basal:maxProfileBasal,reduced_bolus_combined_percent:reduced,baseline_caps:intervalCaps,cap_scope:'Unadjusted exported profile before runtime sensitivity, overrides, prediction, IOB headroom and pump rounding. These are configured ceilings, not dose recommendations.'},
            coverage:{total_rows:rows.length,categories:counts,interpreted:rows.filter(r=>['interpreted','schedule','preset','metadata'].includes(r.assessment)).length,context_only:rows.filter(r=>r.assessment==='context').length,invalid:rows.filter(r=>['invalid','conflict'].includes(r.assessment)).length,redacted:rows.filter(r=>r.assessment==='redacted').length},
            input_summary:{filename,scope:'Full exported configuration retained in memory; connection credentials are redacted.'},
            unassessed:rows.filter(r=>r.assessment==='context').map(r=>({name:r.name,reason:'Retained for contextual questions; no specific mechanical rule applied.'}))};
    }
    return {review,redact,minuteOfDay,references};
})();
if (typeof module!=='undefined') module.exports=TrioConfiguration;
