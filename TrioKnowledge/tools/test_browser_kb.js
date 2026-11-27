const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const kb = require('./browser-kb.js');
const root=path.resolve(__dirname,'..');
const read=name=>JSON.parse(fs.readFileSync(path.join(root,'knowledge',name),'utf8'));
const catalog=read('settings-catalog.json'), facts=read('facts.json');
const fixtures = [
    {name:'empty',value:{}},
    {name:'aliases',value:{preferences:{max_iob:0,SMBInterval:3},settings:{dosingMode:'closed'}}},
    {name:'missing permissions',value:{enableUAM:true}},
    {name:'UAM no permission',value:{enableUAM:true,enableSMBAlways:false,enableSMBWithCOB:false,enableSMBAfterCarbs:false,enableSMBWithTemptarget:false,enableSMB_high_bg:false}},
    {name:'basal testing',value:{dosingMode:'basalTesting',maxIOB:5,autosensMin:0.7,autosensMax:1.2,useNewFormula:true,sigmoid:true,threshold_setting:60}},
    {name:'LGS',value:{dosingMode:'lowGlucoseSuspend',maxIOB:5}},
    {name:'higher threshold',value:{dosingMode:'basalTesting',threshold_setting:90}},
    {name:'invalid types',value:{enableUAM:'true',SMBInterval:true,maxIOB:null}},
    {name:'picker bounds',value:{maxSMBBasalMinutes:10,maxUAMSMBBasalMinutes:16}},
    {name:'picker minimum',value:{maxSMBBasalMinutes:15}},
    {name:'factor mistake',value:{overrideFactor:80}},
    {name:'duplicate aliases',value:{maxIOB:1,max_iob:2}},
    {name:'legacy',value:{closedLoop:true}},
    {name:'new key priority',value:{dosingMode:'open',closedLoop:true}},
    {name:'unknown',value:{notASetting:100}},
    {name:'dependencies',value:{autosensMin:0.9,autosensMax:0.8,allowSMBWithHighTemptarget:true,overrideFactor:0.8}},
    {name:'CSV',filename:'settings.csv',text:'\uFEFFSetting Category,Subcategory,Setting Name,Value,Unit\r\nMetadata,,Dosing Mode,Basal Testing,\r\nTherapy,,Maximum Insulin on Board (IOB),5 (mode is using 0),U\r\nFeatures,,Recommended Bolus Percentage,80,%\r\nTherapy,,Minimum Safety Threshold,4.0,mmol/L\r\nAlgorithm,,Dynamic ISF,Logarithmic (mode is using Disabled),\r\nTherapy,,Basal Rate,0.7,U/hr\r\n'},
    {name:'CSV disabled sigmoid unknown',filename:'settings.csv',text:'Setting Category,Subcategory,Setting Name,Value,Unit\nAlgorithm,,Dynamic ISF,Disabled,\n'},
    {name:'CSV version boundary',filename:'settings.csv',text:'Setting Category,Subcategory,Setting Name,Value,Unit\nMetadata,,App Version,1.0.20,\nMetadata,,Dosing Mode,Open Loop,\n'},
    {name:'CSV quotes/newline',filename:'settings.csv',text:'Setting Category,Subcategory,Setting Name,Value,Unit\nFeatures,,"Unknown, \"\"quoted\"\" row","first\nsecond",\nMetadata,,Dosing Mode,Open Loop,\n'}
];
const prepared=fixtures.map(f=>({...f,filename:f.filename||'settings.json',text:f.text||JSON.stringify(f.value)}));
const python = `import sys,json,tempfile\nfrom pathlib import Path\nsys.path.insert(0,${JSON.stringify(__dirname)})\nimport trio_kb\nresults=[]\nwith tempfile.TemporaryDirectory() as directory:\n for f in json.load(sys.stdin):\n  p=Path(directory)/f['filename'];p.write_text(f['text']);results.append(trio_kb.evaluate(p))\nprint(json.dumps(results))\n`;
const reference=JSON.parse(execFileSync('python3',['-c',python],{input:JSON.stringify(prepared),encoding:'utf8'}));
const plain=value=>JSON.parse(JSON.stringify(value));
const comparable=r=>({values:r.provided_valid_values,effective:r.effective_known_values,checked:r.checked_settings,unassessed:r.unassessed,findings:r.findings.map(f=>({level:f.level,code:f.code,evidence:f.evidence})),errors:r.errors,metadata:r.metadata});
for(let i=0;i<prepared.length;i++) {
    const f=prepared[i],actual=kb.evaluate(f.text,f.filename,catalog,'test-release');
    assert.deepEqual(plain(comparable(actual)),comparable(reference[i]),f.name+' agrees with Python');
}
assert.throws(()=>kb.parseJSON('{"a":1,"a":2}'),/Duplicate JSON key/);
assert.throws(()=>kb.parseJSON('{"preferences":{"max_iob":1,"max_iob":2}}'),/Duplicate JSON key/);
assert.throws(()=>kb.parseJSON('{"a":1} trailing'),/Unexpected/);
assert.throws(()=>kb.parseCSV('a,b\n"unterminated'),/Unterminated/);
assert.throws(()=>kb.parseSettings('Kategorie,Wert\nA,1','settings.csv'),/English/);
assert.throws(()=>kb.parseSettings('Setting Category,Subcategory,Setting Name,Value,Unit\nAlgorithm,,SMB Interval,,minutes','settings.csv'),/Invalid numeric/);
assert.equal(kb.ask('Does UAM insulin already count when I bolus late?',facts,[]).answers[0].id,'F11');
assert.equal(kb.ask('???',facts,[]).answers.length,0);
const report=kb.evaluate('{"dosingMode":"basalTesting","max_iob":5}','settings.json',catalog,'test');
const answer=kb.ask('What is my Max IOB?',facts,[],report);
assert.deepEqual(plain(answer.configuration.find(f=>f.name==='maxIOB')),{name:'maxIOB',stored:5,effective:0});
assert.equal(kb.ask('an unrelated zeppelin question',facts,[]).answers.length,0);
console.log(`${prepared.length} browser/Python evaluation parity cases and 10 parser/question checks passed.`);
