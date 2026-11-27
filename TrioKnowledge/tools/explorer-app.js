(() => {
    let settingsReport = null, uploadGeneration = 0;
    const display = value => esc(typeof value === 'object' ? JSON.stringify(value) : String(value));
    const evidenceLink = ref => typeof ref === 'string'
        ? `<button type="button" data-fact="${esc(ref)}">${esc(ref)} · source explanation</button>`
        : `<a href="../${esc(ref.local_path || ref.path)}">${esc(ref.path)}:${ref.line}</a>`;
    function bindFacts(container) {
        for (const button of container.querySelectorAll('[data-fact]')) button.onclick = () => {
            select(button.dataset.fact);
            $('heading').scrollIntoView({behavior:'smooth',block:'start'});
        };
    }
    function renderReport(report) {
        const ordered = [...report.findings].sort((a,b) => ['error','review','incomplete','behavior'].indexOf(a.level)-['error','review','incomplete','behavior'].indexOf(b.level));
        let content = `<p><strong>${report.checked_settings.length} settings checked</strong> · ${report.errors} invalid values · ${report.unassessed.length} unassessed rows</p><p class="note">${esc(report.missing_values)}</p>`;
        content += ordered.map(f=>`<div class="finding ${esc(f.level)}"><strong>${esc(f.level)}</strong><p>${esc(f.message)}</p><div class="toolbar">${f.evidence.map(evidenceLink).join(' ')}</div></div>`).join('');
        content += '<details><summary>Stored and effective values</summary><table><thead><tr><th>Setting</th><th>Stored</th><th>Effective known value</th></tr></thead><tbody>';
        for (const name of new Set([...Object.keys(report.provided_valid_values),...Object.keys(report.effective_known_values)])) {
            const entry = catalog.find(f=>f.name===name);
            content += `<tr><td><button type="button" data-setting="${esc(entry?.id || '')}">${esc(name)}</button></td><td>${Object.hasOwn(report.provided_valid_values,name)?display(report.provided_valid_values[name]):'Not supplied'}</td><td>${Object.hasOwn(report.effective_known_values,name)?display(report.effective_known_values[name]):'Unknown'}</td></tr>`;
        }
        content += '</tbody></table></details>';
        if (report.unassessed.length) content += `<details open><summary>Unassessed rows (${report.unassessed.length})</summary><ul>${report.unassessed.map(r=>`<li>${esc(r.name)}: ${esc(r.reason)}</li>`).join('')}</ul></details>`;
        if (report.input_notes.length || Object.keys(report.metadata).length) content += `<details><summary>Export metadata and parsing notes</summary><pre>${esc(JSON.stringify({metadata:report.metadata,notes:report.input_notes},null,2))}</pre></details>`;
        $('settings-results').innerHTML = content;
        bindFacts($('settings-results'));
        for (const button of $('settings-results').querySelectorAll('[data-setting]')) button.onclick = () => {
            if (byId.has(button.dataset.setting)) { select(button.dataset.setting); $('heading').scrollIntoView({behavior:'smooth',block:'start'}); }
        };
    }
    $('settings-file').onchange = async () => {
        const generation = ++uploadGeneration, file = $('settings-file').files[0];
        settingsReport = null;
        $('settings-results').innerHTML = '';
        $('settings-error').textContent = '';
        $('answer').innerHTML = '';
        $('clear-settings').hidden = !file;
        $('download-report').hidden = true;
        if (!file) { $('upload-status').textContent='No file selected.'; return; }
        $('upload-status').textContent='Reading '+file.name+' locally…';
        try {
            if (!/\.(csv|json)$/i.test(file.name)) throw Error('Choose a .csv or .json settings export.');
            const text = await file.text();
            if (generation !== uploadGeneration) return;
            const report = TrioBrowserKB.evaluate(text,file.name,catalog,data.release);
            settingsReport = report;
            $('upload-status').textContent=file.name+' evaluated in this tab. New questions can use the supplied settings.';
            $('download-report').hidden=false;
            renderReport(report);
        } catch (error) {
            if (generation !== uploadGeneration) return;
            $('upload-status').textContent='The file could not be evaluated.';
            $('settings-error').textContent=error.message;
        }
    };
    $('clear-settings').onclick = () => {
        uploadGeneration++;
        settingsReport=null;
        $('settings-file').value='';
        $('settings-results').innerHTML='';
        $('settings-error').textContent='';
        $('answer').innerHTML='';
        $('upload-status').textContent='Settings cleared from this tab.';
        $('clear-settings').hidden=true;
        $('download-report').hidden=true;
    };
    $('download-report').onclick = () => {
        if (!settingsReport) return;
        const url = URL.createObjectURL(new Blob([JSON.stringify(settingsReport,null,2)],{type:'application/json'}));
        const link=document.createElement('a');
        link.href=url;link.download='Trio-settings-evaluation.json';link.click();
        setTimeout(()=>URL.revokeObjectURL(url),1000);
    };
    $('ask-form').onsubmit = event => {
        event.preventDefault();
        const question=$('question').value.trim();
        if (!question) { $('answer').textContent='Enter a question first.'; return; }
        const result=TrioBrowserKB.ask(question,facts,corpus,settingsReport);
        let content=`<p class="note">${esc(result.note)}</p>`;
        if (result.configuration.length) {
            content+='<article><h3>From your supplied settings</h3>';
            for (const field of result.configuration) content+=`<p><strong>${esc(field.name)}</strong>: stored ${display(field.stored)}; effective known value ${display(field.effective)}.</p>`;
            content+='<p class="note">Other state, including schedules, active overrides and glucose history, may be absent.</p></article>';
        }
        for (const fact of result.answers) content+=`<article><h3>${esc(fact.title)}</h3><p>${esc(fact.answer)}</p><div class="toolbar"><button type="button" data-fact="${esc(fact.id)}">Explore ${esc(fact.id)} in graph</button></div>${fact.evidence.map(ref=>`<p class="answer-source">${evidenceLink(ref)} · <a href="${esc(ref.url)}">source reference</a></p>`).join('')}</article>`;
        if (result.evidence.length) content+='<details><summary>Retrieved source passages ('+result.evidence.length+')</summary>'+result.evidence.map(hit=>`<article><strong>${esc(hit.title)}</strong> · ${esc(hit.kind)}<p class="answer-source"><a href="../${esc(hit.path)}">${esc(hit.path)}:${hit.start_line}–${hit.end_line}</a> · <a href="${esc(hit.url)}">source</a></p><pre>${esc(hit.text)}</pre></article>`).join('')+'</details>';
        if (!result.answers.length && !result.evidence.length) content+='<p>No matching evidence was found. Try naming the setting or feature.</p>';
        $('answer').innerHTML=content;
        bindFacts($('answer'));
    };
})();
