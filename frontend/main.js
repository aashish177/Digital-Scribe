const $ = (id) => document.getElementById(id);

const genForm = $('gen-form');
const submitBtn = $('submit-btn');
const requestSection = $('request-section');
const statusSection = $('status-section');
const resultSection = $('result-section');
const logsContainer = $('logs');
const statusBadge = $('current-status');
const progressTitle = $('progress-title');
const hitlPanel = $('hitl-panel');
const briefPreview = $('brief-preview');
const approveBtn = $('approve-btn');

const STEP_ORDER = ['planner', 'researcher', 'writer', 'editor', 'seo', 'translator', 'social_media', 'image_gen'];
const STEP_LABELS = {
    planner: 'Plan', researcher: 'Research', writer: 'Write', editor: 'Edit',
    seo: 'SEO', translator: 'Translate', social_media: 'Social', image_gen: 'Image'
};
const steps = Object.fromEntries(STEP_ORDER.map(n => [n, document.querySelector(`[data-step="${n}"]`)]));
const PARALLEL = ['translator', 'social_media', 'image_gen'];
const AGENT_NAMES = {
    planner: 'Planner', researcher: 'Researcher', writer: 'Writer', editor: 'Editor',
    seo: 'SEO', translator: 'Translator', social_media: 'Social', image_gen: 'Image idea'
};

let agentData = {};
let agentStatus = {};
let selectedAgent = null;
let selectedPinned = false;
let runTotals = null;

let currentRequestId = null;
let eventSource = null;
let articleMarkdown = '';
let articleTitle = 'article';

// Model output is untrusted, so it is sanitized before it reaches the DOM.
function renderMarkdown(text) {
    if (window.marked && window.DOMPurify) {
        return DOMPurify.sanitize(marked.parse(text || ''));
    }
    const div = document.createElement('div');
    div.textContent = text || '';
    return `<p style="white-space:pre-wrap">${div.innerHTML}</p>`;
}

function setStatus(text, kind = '') {
    statusBadge.textContent = text;
    statusBadge.className = `status ${kind}`;
    if (kind === 'err') {
        requestSection.classList.remove('hidden');
        submitBtn.disabled = false;
    }
}

function log(message, type = 'info') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    logsContainer.appendChild(entry);
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

// Tabs
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => showTab(btn.dataset.tab));
});

function showTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.id === `${tab}-view`));
}

// Example topics
document.querySelectorAll('.chip[data-example]').forEach(chip => {
    chip.addEventListener('click', () => {
        $('request').value = chip.dataset.example;
        $('request').focus();
    });
});

// Steps
function resetSteps() {
    Object.values(steps).forEach(s => s.classList.remove('active', 'completed', 'skipped'));
    logsContainer.innerHTML = '';
    agentData = {};
    agentStatus = {};
    selectedAgent = null;
    selectedPinned = false;
    runTotals = null;
    renderAgents();
}

function markActive(node) {
    if (steps[node] && !steps[node].classList.contains('completed')) steps[node].classList.add('active');
    if (agentStatus[node] !== 'done' && agentStatus[node] !== 'skip') agentStatus[node] = 'run';
    renderAgents();
}

function markCompleted(node, summary) {
    const idx = STEP_ORDER.indexOf(node);
    if (idx === -1) return;
    const parallel = PARALLEL.includes(node);
    const upTo = parallel ? [node] : STEP_ORDER.slice(0, idx + 1);
    upTo.forEach(n => {
        steps[n].classList.remove('active');
        if (n === node && summary && summary.skipped) {
            steps[n].classList.add('skipped');
            agentStatus[n] = 'skip';
        } else {
            steps[n].classList.add('completed');
            agentStatus[n] = summary && summary.errors ? 'err' : 'done';
        }
    });
    if (summary) agentData[node] = summary;
    if (!parallel) {
        const next = node === 'seo' ? PARALLEL : [STEP_ORDER[idx + 1]].filter(Boolean);
        next.forEach(markActive);
    }
    if (!selectedPinned && !(summary && summary.skipped)) selectedAgent = node;
    renderAgents();
}

function finishSteps(data) {
    const agents = data.agents || {};
    const produced = {
        translator: data.translated_content && Object.keys(data.translated_content).length > 0,
        social_media: data.social_media_posts && Object.keys(data.social_media_posts).length > 0,
        image_gen: data.generated_images && data.generated_images.length > 0,
    };
    STEP_ORDER.forEach(node => {
        const el = steps[node];
        el.classList.remove('active');
        const skipped = agents[node] ? agents[node].skipped : (node in produced && !produced[node]);
        el.classList.toggle('skipped', !!skipped);
        el.classList.toggle('completed', !skipped);
        agentStatus[node] = skipped ? 'skip' : 'done';
    });
    if (data.agents) agentData = data.agents;
    runTotals = data.totals || null;
    if (!selectedPinned) selectedAgent = 'researcher';
    renderAgents();
}

// Agents view
function setView(view) {
    const agents = view === 'agents';
    document.querySelectorAll('.view-toggle button').forEach(b => b.classList.toggle('on', b.dataset.view === view));
    $('agent-console').classList.toggle('hidden', !agents);
    document.querySelector('.steps').classList.toggle('hidden', agents);
    statusSection.classList.toggle('wide', agents);
    try { localStorage.setItem('ds-view', view); } catch (e) { /* storage can be blocked */ }
    renderAgents();
}

document.querySelectorAll('.view-toggle button').forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));

function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
}

const fmtTokens = (u) => u ? (u.input_tokens + u.output_tokens).toLocaleString() : '—';
const fmtCost = (c) => c == null ? '—' : c < 0.01 ? `$${c.toFixed(4)}` : `$${c.toFixed(3)}`;

function agentSubtitle(node, s, status) {
    if (status === 'skip') {
        return node === 'translator' ? 'Skipped · no languages' : 'Skipped · turned off';
    }
    if (status === 'run') return PARALLEL.includes(node) ? 'Running in parallel…' : 'Working…';
    if (!s || status !== 'done' && status !== 'err') return PARALLEL.includes(node) ? 'Runs in parallel' : 'Waiting';
    if (s.errors) return 'Failed';
    switch (node) {
        case 'planner': return `Brief · ${(s.outline || []).length} sections · ${(s.queries || []).length} queries`;
        case 'researcher': return `${s.chunk_count || 0} chunks from ${s.source_count || 0} sources`;
        case 'writer': return `${(s.word_count || 0).toLocaleString()} words${s.attempts > 1 ? ` · ${s.attempts} attempts` : ''}`;
        case 'editor': return 'Polished the draft';
        case 'seo': return s.slug ? `/${s.slug}` : 'Title and description';
        case 'translator': return (s.languages || []).join(', ') || 'Translated';
        case 'social_media': return (s.platforms || []).join(', ') || 'Posts drafted';
        case 'image_gen': return 'Cover image concept';
        default: return '';
    }
}

function traceItem(node) {
    const s = agentData[node];
    const status = agentStatus[node] || 'wait';
    const btn = el('button', `trace-item t-${status}${selectedAgent === node ? ' sel' : ''}`);
    btn.type = 'button';
    btn.disabled = !(status === 'done' || status === 'err');
    btn.append(el('i', 'dot'));
    const text = el('div');
    text.append(el('div', 'tname', AGENT_NAMES[node]), el('div', 'tsub', agentSubtitle(node, s, status)));
    btn.append(text);
    const meta = el('div', 'tmeta');
    if (s && s.duration != null) {
        meta.append(document.createTextNode(`${s.duration.toFixed(1)}s`), el('br'), document.createTextNode(s.usage ? `${fmtTokens(s.usage)} tok` : ''));
    }
    btn.append(meta);
    btn.addEventListener('click', () => {
        selectedAgent = node;
        selectedPinned = true;
        renderAgents();
    });
    return btn;
}

function renderAgents() {
    const trace = $('trace');
    if (!trace) return;
    trace.innerHTML = '';
    STEP_ORDER.filter(n => !PARALLEL.includes(n)).forEach(n => trace.appendChild(el('li')).appendChild(traceItem(n)));
    const par = el('li', 'trace-par');
    PARALLEL.forEach(n => par.appendChild(traceItem(n)));
    trace.appendChild(par);
    renderDetail();
}

function renderDetail() {
    const box = $('agent-detail');
    box.innerHTML = '';
    const node = selectedAgent;
    const s = node && agentData[node];
    if (!s || s.skipped) {
        box.append(el('p', 'muted', 'Agent details appear here as each one finishes. Click a finished agent to inspect it.'));
        appendTotals(box);
        return;
    }
    box.append(el('h4', null, AGENT_NAMES[node]));
    const blurbs = {
        planner: 'Turns the request into a brief and research queries',
        researcher: 'Hybrid search (vector + BM25), reranked with FlashRank',
        writer: 'Drafts the article from the brief and research',
        editor: 'Edits against the style guide without changing facts',
        seo: 'Writes the search title, description and slug',
        translator: 'Translates the final article',
        social_media: 'Drafts posts for each platform',
        image_gen: 'Suggests a cover image concept',
    };
    box.append(el('div', 'muted', blurbs[node]));

    const kv = el('div', 'kv');
    [[s.duration != null ? `${s.duration.toFixed(1)}s` : '—', 'Time'],
     [s.usage ? s.usage.input_tokens.toLocaleString() : '—', 'Tokens in'],
     [s.usage ? s.usage.output_tokens.toLocaleString() : '—', 'Tokens out'],
     [fmtCost(s.cost), 'Cost']].forEach(([v, k]) => {
        const cell = el('div');
        cell.append(el('b', null, v), el('span', null, k));
        kv.appendChild(cell);
    });
    box.append(kv);

    if (s.errors) s.errors.forEach(e => box.append(el('p', 'err', e)));

    const queries = node === 'researcher' ? (agentData.planner && agentData.planner.queries) : s.queries;
    if (queries && queries.length) {
        box.append(el('div', 'lbl', node === 'researcher' ? 'Queries from the planner' : 'Research queries'));
        queries.forEach(q => box.append(el('span', 'q', q)));
    }
    if (node === 'planner' && s.outline && s.outline.length) {
        box.append(el('div', 'lbl', 'Outline'));
        const ul = el('ul');
        s.outline.forEach(o => ul.append(el('li', null, o)));
        box.append(ul);
    }
    if (node === 'researcher' && s.chunks && s.chunks.length) {
        box.append(el('div', 'lbl', 'Top retrieved chunks'));
        s.chunks.forEach(c => {
            const card = el('div', 'chunk');
            const src = el('div', 'chunk-src');
            src.append(el('span', null, c.title), el('span', 'chunk-score', c.score != null ? c.score.toFixed(2) : ''));
            card.append(src, el('div', null, c.text + (c.text.length >= 240 ? '…' : '')));
            box.append(card);
        });
    }
    if (node === 'editor' && s.notes) {
        box.append(el('div', 'lbl', 'Changes'), el('div', 'pre', s.notes));
    }
    if (node === 'seo' && s.title) {
        box.append(el('div', 'lbl', 'Search title'), el('div', null, s.title));
    }
    if (node === 'image_gen' && s.prompt) {
        box.append(el('div', 'lbl', 'Prompt'), el('div', null, s.prompt));
    }
    appendTotals(box);
}

function appendTotals(box) {
    const done = Object.values(agentData).filter(s => s && !s.skipped);
    if (!done.length) return;
    const t = runTotals || {
        duration: done.reduce((a, s) => a + (s.duration || 0), 0),
        tokens: done.reduce((a, s) => a + (s.usage ? s.usage.input_tokens + s.usage.output_tokens : 0), 0),
        cost: done.some(s => s.cost != null) ? done.reduce((a, s) => a + (s.cost || 0), 0) : null,
    };
    const totals = el('div', 'totals');
    const item = (label, value) => {
        const span = el('span', null, `${label} `);
        span.append(el('b', null, value));
        return span;
    };
    totals.append(
        item(runTotals ? 'Agent time' : 'So far', `${t.duration.toFixed(1)}s`),
        item('Tokens', t.tokens.toLocaleString()),
        item('Est. cost', fmtCost(t.cost)),
    );
    if (t.model) totals.append(item('Model', t.model));
    box.append(totals);
}

try { setView(localStorage.getItem('ds-view') === 'agents' ? 'agents' : 'simple'); } catch (e) { setView('simple'); }

// Brief review
function renderBrief(brief) {
    briefPreview.innerHTML = '';
    if (!brief) {
        briefPreview.textContent = 'Loading the brief…';
        return;
    }
    const dl = document.createElement('dl');
    const add = (label, value) => {
        if (!value || (Array.isArray(value) && !value.length)) return;
        const dt = document.createElement('dt');
        dt.textContent = label;
        const dd = document.createElement('dd');
        if (Array.isArray(value)) {
            const ul = document.createElement('ul');
            value.forEach(v => {
                const li = document.createElement('li');
                li.textContent = v;
                ul.appendChild(li);
            });
            dd.appendChild(ul);
        } else {
            dd.textContent = value;
        }
        dl.append(dt, dd);
    };
    add('Title', brief.title);
    add('Audience', brief.target_audience);
    add('Tone', brief.tone);
    add('Length', brief.word_count_target ? `${brief.word_count_target} words` : null);
    add('Outline', brief.outline);
    add('Keywords', brief.seo_keywords && brief.seo_keywords.join(', '));
    briefPreview.appendChild(dl);
}

function showApproval(brief) {
    setStatus('Waiting for you', 'warn');
    progressTitle.textContent = 'Review the brief';
    statusSection.classList.remove('hidden');
    hitlPanel.classList.remove('hidden');
    renderBrief(brief);
}

// Streaming
function connectStream(requestId) {
    if (eventSource) eventSource.close();
    eventSource = new EventSource(`/api/v1/stream/${requestId}`);

    eventSource.onmessage = (event) => {
        let data;
        try {
            data = JSON.parse(event.data);
        } catch (err) {
            log(`Unreadable stream event: ${String(event.data).slice(0, 80)}`, 'error');
            return;
        }
        switch (data.event) {
            case 'started':
                setStatus('Working');
                log(`Started: ${data.node}`);
                markActive(data.node);
                break;
            case 'node_complete':
                if (data.node === '__interrupt__') {
                    log('Paused for brief review');
                    setTimeout(() => pollStatus(currentRequestId), 800);
                } else {
                    log(`Done: ${STEP_LABELS[data.node] || data.node}`);
                    markCompleted(data.node, data.summary);
                }
                break;
            case 'awaiting_approval':
                log('Brief ready for review');
                showApproval(data.brief);
                if (!data.brief) pollStatus(currentRequestId);
                break;
            case 'resuming':
                hitlPanel.classList.add('hidden');
                progressTitle.textContent = 'Writing your article';
                setStatus('Working');
                log(`Resuming at ${data.node}`);
                markActive(data.node);
                break;
            case 'completed':
                setStatus('Done', 'ok');
                progressTitle.textContent = 'Article ready';
                log('Pipeline finished');
                eventSource.close();
                fetchResults(requestId);
                break;
            case 'failed':
                eventSource.close();
                if (data.error === 'Stream timed out') {
                    log('Stream went quiet, checking status…');
                    pollStatus(currentRequestId);
                    break;
                }
                setStatus('Failed', 'err');
                progressTitle.textContent = 'Something went wrong';
                log(`Error: ${data.error}`, 'error');
                submitBtn.disabled = false;
                break;
        }
    };

    eventSource.onerror = () => {
        log('Connection lost, checking status…');
        eventSource.close();
        setTimeout(() => pollStatus(currentRequestId), 1000);
    };
}

async function pollStatus(requestId) {
    if (!requestId) return;
    try {
        const res = await fetch(`/api/v1/status/${requestId}`);
        const data = await res.json();
        if (data.status === 'awaiting_approval') {
            showApproval(data.brief);
        } else if (data.status === 'completed') {
            setStatus('Done', 'ok');
            fetchResults(requestId);
        } else if (data.status === 'failed') {
            setStatus('Failed', 'err');
            log(`Error: ${data.error}`, 'error');
        } else if (data.status === 'processing' || data.status === 'pending') {
            setTimeout(() => pollStatus(requestId), 3000);
        }
    } catch (err) {
        log(`Status check failed: ${err}`, 'error');
    }
}

// Results
async function fetchResults(requestId) {
    try {
        const res = await fetch(`/api/v1/content/${requestId}`);
        const data = await res.json();

        articleMarkdown = data.final_content || '';
        articleTitle = (data.seo_metadata && data.seo_metadata.url_slug) || (data.brief && data.brief.title) || 'article';

        $('article-view').innerHTML = renderMarkdown(articleMarkdown);
        renderSocial(data.social_media_posts);
        renderTranslations(data.translated_content);
        renderSources(data.sources);
        renderSeo(data.seo_metadata);
        renderTimings(data.execution_times);
        renderImage(data.generated_images);
        renderNotes(data.edit_notes);
        finishSteps(data);

        showTab('article');
        resultSection.classList.remove('hidden');
        submitBtn.disabled = false;
        resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
        log(`Could not load the article: ${err}`, 'error');
    }
}

function renderSocial(posts) {
    const view = $('social-view');
    view.innerHTML = '';
    const entries = Object.entries(posts || {});
    document.querySelector('[data-tab="social"]').classList.toggle('hidden', !entries.length);
    entries.forEach(([platform, text]) => {
        const card = document.createElement('div');
        card.className = 'social-post';
        const name = document.createElement('div');
        name.className = 'social-platform';
        name.textContent = platform;
        const body = document.createElement('div');
        body.className = 'social-text';
        body.textContent = typeof text === 'string' ? text : JSON.stringify(text, null, 2);
        card.append(name, body);
        view.appendChild(card);
    });
}

function renderTranslations(translations) {
    const view = $('translations-view');
    view.innerHTML = '';
    const entries = Object.entries(translations || {});
    document.querySelector('[data-tab="translations"]').classList.toggle('hidden', !entries.length);
    entries.forEach(([lang, content]) => {
        const block = document.createElement('section');
        block.className = 'translation';
        const label = document.createElement('div');
        label.className = 'translation-lang';
        label.textContent = lang;
        const body = document.createElement('div');
        body.innerHTML = renderMarkdown(content);
        block.append(label, body);
        view.appendChild(block);
    });
}

function renderSources(sources) {
    const list = $('sources-list');
    list.innerHTML = '';
    if (!sources || !sources.length) {
        const li = document.createElement('li');
        li.className = 'empty';
        li.textContent = 'No sources were retrieved for this topic.';
        list.appendChild(li);
        return;
    }
    sources.forEach(s => {
        const li = document.createElement('li');
        if (Number.isInteger(s.n)) li.value = s.n;
        const a = document.createElement('a');
        a.textContent = s.title;
        if (/^https?:\/\//.test(s.url)) {
            a.href = s.url;
            a.target = '_blank';
            a.rel = 'noopener noreferrer';
        }
        li.appendChild(a);
        list.appendChild(li);
    });
}

function renderSeo(meta) {
    const block = $('seo-block');
    if (!meta || !meta.title) {
        block.classList.add('hidden');
        return;
    }
    $('seo-title').textContent = meta.title;
    $('seo-slug').textContent = meta.url_slug ? `example.com/${meta.url_slug}` : '';
    $('seo-desc').textContent = meta.meta_description || '';
    block.classList.remove('hidden');
}

function renderTimings(times) {
    const block = $('timing-block');
    const container = $('timings');
    container.innerHTML = '';
    const entries = STEP_ORDER.filter(n => times && times[n] != null).map(n => [n, times[n]]);
    if (!entries.length) {
        block.classList.add('hidden');
        return;
    }
    const max = Math.max(...entries.map(([, t]) => t));
    let total = 0;
    entries.forEach(([node, t]) => {
        total += t;
        const row = document.createElement('div');
        row.className = 'timing-row';
        const name = document.createElement('span');
        name.textContent = STEP_LABELS[node];
        const track = document.createElement('div');
        const bar = document.createElement('div');
        bar.className = 'timing-bar';
        bar.style.width = `${Math.max(4, (t / max) * 100)}%`;
        track.appendChild(bar);
        const val = document.createElement('span');
        val.className = 'timing-val';
        val.textContent = `${t.toFixed(1)}s`;
        row.append(name, track, val);
        container.appendChild(row);
    });
    const sum = document.createElement('div');
    sum.className = 'timing-total';
    sum.textContent = `Total ${total.toFixed(1)}s`;
    container.appendChild(sum);
    block.classList.remove('hidden');
}

function renderImage(images) {
    const block = $('image-block');
    const first = images && images[0];
    if (!first || !first.prompt) {
        block.classList.add('hidden');
        return;
    }
    $('image-prompt').textContent = first.style ? `${first.prompt} (${first.style})` : first.prompt;
    block.classList.remove('hidden');
}

function renderNotes(notes) {
    const block = $('notes-block');
    if (!notes) {
        block.classList.add('hidden');
        return;
    }
    $('edit-notes').textContent = notes;
    block.classList.remove('hidden');
}

// Actions
$('copy-btn').addEventListener('click', async () => {
    try {
        await navigator.clipboard.writeText(articleMarkdown);
        $('copy-btn').textContent = 'Copied';
        setTimeout(() => ($('copy-btn').textContent = 'Copy Markdown'), 1500);
    } catch (err) {
        log(`Copy failed: ${err}`, 'error');
    }
});

$('download-btn').addEventListener('click', () => {
    const blob = new Blob([articleMarkdown], { type: 'text/markdown' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${articleTitle.toString().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'article'}.md`;
    a.click();
    URL.revokeObjectURL(a.href);
});

$('new-request-btn').addEventListener('click', () => {
    resultSection.classList.add('hidden');
    statusSection.classList.add('hidden');
    requestSection.classList.remove('hidden');
    $('request').focus();
    window.scrollTo({ top: 0, behavior: 'smooth' });
});

// Submit
genForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        request: $('request').value.trim(),
        word_count: parseInt($('word_count').value, 10),
        tone: $('tone').value,
        require_approval: $('require_approval').checked,
        generate_image: $('gen_image').checked,
        generate_social_posts: $('gen_social').checked,
        languages: $('languages').value.split(',').map(s => s.trim()).filter(Boolean),
    };
    if (!payload.request) return;

    submitBtn.disabled = true;
    resultSection.classList.add('hidden');
    hitlPanel.classList.add('hidden');
    resetSteps();
    progressTitle.textContent = 'Writing your article';
    $('progress-topic').textContent = payload.request;
    setStatus('Starting');
    requestSection.classList.add('hidden');
    statusSection.classList.remove('hidden');

    try {
        log('Sending request…');
        const res = await fetch('/api/v1/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        currentRequestId = data.request_id;
        log(`Request ${currentRequestId.slice(0, 8)}`);
        connectStream(currentRequestId);
    } catch (err) {
        setStatus('Failed', 'err');
        log(`Could not start: ${err}`, 'error');
        submitBtn.disabled = false;
    }
});

// Approve brief
approveBtn.addEventListener('click', async () => {
    if (!currentRequestId) return;
    approveBtn.disabled = true;
    try {
        await fetch(`/api/v1/approve/${currentRequestId}`, { method: 'POST' });
        hitlPanel.classList.add('hidden');
        // Reconnect only if the stream already ended; the server drops all listeners when one closes.
        if (!eventSource || eventSource.readyState === EventSource.CLOSED) connectStream(currentRequestId);
    } catch (err) {
        log(`Approval failed: ${err}`, 'error');
    } finally {
        approveBtn.disabled = false;
    }
});
