// Exercise the offline explorer's handlers without a browser or network access.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class Element {
    constructor() {
        this.value = '';
        this.children = [];
        this.textContent = '';
        this.innerHTML = '';
    }
    replaceChildren(...children) { this.children = children; }
    append(child) { this.children.push(child); }
    querySelectorAll() { return []; }
}

const elements = new Map();
const document = {
    getElementById(id) {
        if (!elements.has(id)) elements.set(id, new Element());
        return elements.get(id);
    },
    createElement() { return new Element(); }
};
const html = fs.readFileSync(path.join(__dirname, '../knowledge/explorer.html'), 'utf8');
const script = html.split('<script>')[1].split('</script>')[0];
vm.runInNewContext(script, { document });
const get = id => document.getElementById(id);
assert.equal(get('list').children.length, 80, 'initial topics are populated');
get('q').value = 'smbInterval';
get('q').oninput();
assert.equal(get('list').children.length, 1, 'search finds the serialized setting');
assert.match(get('list').children[0].textContent, /smbInterval/);
get('list').children[0].onclick();
assert.equal(get('heading').textContent, 'smbInterval', 'search result opens its graph');
get('q').value = 'LiBrE';
get('kind').value = 'topic';
get('kind').onchange();
assert.equal(get('list').children.length, 1, 'case-insensitive search combines with type filter');
get('list').children[0].onclick();
assert.match(get('heading').textContent, /Libre 3/);
get('q').value = 'a-topic-that-does-not-exist';
get('q').oninput();
assert.equal(get('list').children.length, 0, 'unmatched search clears stale results');
assert.match(get('stats').textContent, /0 matches/);
get('q').value = '';
get('kind').value = '';
get('q').oninput();
assert.equal(get('list').children.length, 80, 'clearing search restores topics');
get('question').value = 'Does UAM insulin already count when I bolus late?';
get('ask-form').onsubmit({preventDefault(){}});
assert.match(get('answer').innerHTML, /already subtracts automated insulin/);
assert.match(get('answer').innerHTML, /source reference/);
assert.doesNotMatch(get('answer').innerHTML, /verified-mismatch|verified-gap|Documentation action:/);
get('clear-settings').onclick();
assert.equal(get('answer').innerHTML,'','clearing private settings also clears answers');
(async () => {
    get('settings-file').files = [{name:'synthetic.json',text:async()=>'{"dosingMode":"basalTesting","max_iob":5,"threshold_setting":60}'}];
    await get('settings-file').onchange();
    assert.match(get('settings-results').innerHTML,/3 settings checked/);
    assert.match(get('settings-results').innerHTML,/Effective maxIOB is 0/);
    assert.equal(get('download-report').hidden,false);
    get('question').value='What is my Max IOB?';
    get('ask-form').onsubmit({preventDefault(){}});
    assert.match(get('answer').innerHTML,/stored 5; effective known value 0/);
    get('clear-settings').onclick();
    assert.equal(get('settings-results').innerHTML,'');
    assert.equal(get('download-report').hidden,true);
    get('question').value='What is my Max IOB?';
    get('ask-form').onsubmit({preventDefault(){}});
    assert.doesNotMatch(get('answer').innerHTML,/From your supplied settings/);
    get('settings-file').files=[{name:'bad.json',text:async()=>'{"max_iob":1,"max_iob":2}'}];
    await get('settings-file').onchange();
    assert.match(get('settings-error').textContent,/Duplicate JSON key/);
    assert.equal(get('download-report').hidden,true);
    let resolve;
    get('settings-file').files=[{name:'slow.json',text:()=>new Promise(r=>{resolve=r;})}];
    const pending=get('settings-file').onchange();
    get('clear-settings').onclick();
    resolve('{"max_iob":5}');
    await pending;
    assert.equal(get('settings-results').innerHTML,'','cleared uploads cannot restore stale private reports');
    assert.equal(get('upload-status').textContent,'Settings cleared from this tab.');
    for (const name of ['browser-kb.js','explorer-app.js']) {
        assert.doesNotMatch(fs.readFileSync(path.join(__dirname,name),'utf8'),/\b(?:fetch|XMLHttpRequest|WebSocket|localStorage|sessionStorage|indexedDB)\b/);
    }
    console.log('Explorer checks passed: graph search/filter, question answers/citations, upload/evaluate, settings-aware questions, clear, parser errors and stale-upload cancellation. No network/storage APIs.');
})().catch(error=>{console.error(error);process.exitCode=1;});
