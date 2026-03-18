// Initialize Lucide Icons
lucide.createIcons();

// DOM Elements
const genForm = document.getElementById('gen-form');
const requestSection = document.getElementById('request-section');
const statusSection = document.getElementById('status-section');
const resultSection = document.getElementById('result-section');
const logsContainer = document.getElementById('logs');
const currentStatusBadge = document.getElementById('current-status');
const hitlPanel = document.getElementById('hitl-panel');
const briefPreview = document.getElementById('brief-preview');
const approveBtn = document.getElementById('approve-btn');
const newRequestBtn = document.getElementById('new-request-btn');
const hideRequestBtn = document.getElementById('hide-request-btn');

// Pipeline Steps
const steps = {
    planner: document.querySelector('[data-step="planner"]'),
    researcher: document.querySelector('[data-step="researcher"]'),
    writer: document.querySelector('[data-step="writer"]'),
    editor: document.querySelector('[data-step="editor"]'),
    seo: document.querySelector('[data-step="seo"]')
};

let currentRequestId = null;
let eventSource = null;

// Tab Management
const tabBtns = document.querySelectorAll('.tab-btn');
const tabPanes = document.querySelectorAll('.tab-pane');

tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        tabBtns.forEach(b => b.classList.remove('active'));
        tabPanes.forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(`${tab}-view`).classList.add('active');
    });
});

// Toggle Request Form
newRequestBtn.addEventListener('click', () => {
    requestSection.classList.remove('hidden');
    genForm.reset();
});

hideRequestBtn.addEventListener('click', () => {
    requestSection.classList.add('hidden');
});

// Reset visualizer
function resetVisualizer() {
    Object.values(steps).forEach(s => {
        s.classList.remove('active', 'completed');
    });
    logsContainer.innerHTML = '';
}

// Log message to UI
function log(message, type = 'info') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    const time = new Date().toLocaleTimeString();
    entry.textContent = `[${time}] ${message}`;
    logsContainer.appendChild(entry);
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

// Update step visualization
function updateStep(nodeName, status) {
    if (!steps[nodeName]) return;

    // Mark previous steps as completed
    const nodeOrder = ['planner', 'researcher', 'writer', 'editor', 'seo'];
    const idx = nodeOrder.indexOf(nodeName);

    for (let i = 0; i < idx; i++) {
        steps[nodeOrder[i]].classList.remove('active');
        steps[nodeOrder[i]].classList.add('completed');
    }

    if (status === 'active') {
        steps[nodeName].classList.add('active');
    } else if (status === 'completed') {
        steps[nodeName].classList.remove('active');
        steps[nodeName].classList.add('completed');
    }
}

// Connect to SSE stream
function connectStream(requestId) {
    if (eventSource) eventSource.close();

    eventSource = new EventSource(`/api/v1/stream/${requestId}`);

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Stream event:', data);

        switch (data.event) {
            case 'started':
                currentStatusBadge.textContent = 'Processing';
                log(`Pipeline started: Node ${data.node}`);
                updateStep(data.node, 'active');
                break;

            case 'node_complete':
                if (data.node === '__interrupt__') {
                    log('⏸ Pipeline paused for brief approval...');
                    // Fallback: poll status if awaiting_approval event was missed
                    setTimeout(() => pollForApproval(currentRequestId), 800);
                } else {
                    log(`✅ Step completed: ${data.node}`);
                    updateStep(data.node, 'completed');
                }
                break;

            case 'awaiting_approval':
                console.log('HITL: Awaiting approval event received', data);
                currentStatusBadge.textContent = 'Action Required';
                currentStatusBadge.classList.add('warning');
                log('🔶 Pipeline paused: Awaiting brief approval — please review below.', 'info');

                // Force show both sections to be sure
                statusSection.classList.remove('hidden');
                hitlPanel.classList.remove('hidden');

                if (data.brief) {
                    briefPreview.textContent = JSON.stringify(data.brief, null, 2);
                } else {
                    briefPreview.textContent = "Loading brief details...";
                    pollForApproval(currentRequestId); // Fetch if missing
                }
                break;

            case 'resuming':
                hitlPanel.classList.add('hidden');
                currentStatusBadge.textContent = 'Processing';
                log(`Resuming pipeline at: ${data.node}`);
                updateStep(data.node, 'active');
                break;

            case 'completed':
                currentStatusBadge.textContent = 'Finished';
                log('Pipeline completed successfully!', 'info');
                fetchResults(requestId);
                eventSource.close();
                break;

            case 'failed':
                currentStatusBadge.textContent = 'Failed';
                log(`Error: ${data.error}`, 'error');
                eventSource.close();
                break;
        }
    };

    eventSource.onerror = (err) => {
        console.error('SSE Error:', err);
        log('Connection lost, polling for status...', 'info');
        eventSource.close();
        // Fallback: poll to catch any missed events
        setTimeout(() => pollForApproval(currentRequestId), 1000);
    };
}

// Fallback poll: check /api/v1/status in case SSE events were missed
async function pollForApproval(requestId) {
    if (!requestId) return;
    try {
        const res = await fetch(`/api/v1/status/${requestId}`);
        const data = await res.json();
        if (data.status === 'awaiting_approval') {
            console.log('HITL: Status poll detected awaiting_approval');
            currentStatusBadge.textContent = 'Action Required';
            currentStatusBadge.classList.add('warning');

            statusSection.classList.remove('hidden');
            hitlPanel.classList.remove('hidden');

            if (data.brief) {
                briefPreview.textContent = JSON.stringify(data.brief, null, 2);
            }
        } else if (data.status === 'completed') {
            fetchResults(requestId);
        } else if (data.status === 'failed') {
            log(`Error: ${data.error}`, 'error');
        } else if (data.status === 'processing') {
            // Still running, check again in 3s
            setTimeout(() => pollForApproval(requestId), 3000);
        }
    } catch (err) {
        console.error('Status poll failed:', err);
    }
}

// Fetch final results
async function fetchResults(requestId) {
    try {
        const response = await fetch(`/api/v1/content/${requestId}`);
        const data = await response.json();

        resultSection.classList.remove('hidden');

        // Article
        document.getElementById('article-view').innerHTML = formatMarkdown(data.final_content || '');

        // Social
        let socialHtml = '<h3>Social Media Post Concepts</h3>';
        if (data.social_media_posts) {
            for (const [platform, post] of Object.entries(data.social_media_posts)) {
                socialHtml += `<div class="social-post"><strong>${platform.toUpperCase()}</strong><pre>${post}</pre></div>`;
            }
        }
        document.getElementById('social-view').innerHTML = socialHtml;

        // Images
        let imagesHtml = '';
        if (data.generated_images) {
            data.generated_images.forEach(img => {
                imagesHtml += `<div class="image-card">
                    <img src="${img.url}" alt="Generated Image" style="width:100%; border-radius:12px; margin-bottom:12px;">
                    <p><strong>Prompt:</strong> ${img.prompt}</p>
                    <p><strong>Style:</strong> ${img.style}</p>
                </div>`;
            });
        }
        document.getElementById('images-view').innerHTML = imagesHtml;

        // Translations
        let transHtml = '';
        if (data.translated_content) {
            for (const [lang, content] of Object.entries(data.translated_content)) {
                transHtml += `<div class="translation-unit"><h3>${lang.toUpperCase()}</h3><div class="trans-body">${formatMarkdown(content)}</div></div>`;
            }
        }
        document.getElementById('translations-view').innerHTML = transHtml;

    } catch (err) {
        log(`Failed to fetch results: ${err}`, 'error');
    }
}

// Simple Markdown Formatter (Placeholder for a real library)
function formatMarkdown(text) {
    return text
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
        .replace(/\*(.*)\*/gim, '<em>$1</em>')
        .replace(/\n/gim, '<br>');
}

// Form Submission
genForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const payload = {
        request: document.getElementById('request').value,
        word_count: parseInt(document.getElementById('word_count').value),
        tone: document.getElementById('tone').value,
        require_approval: document.getElementById('require_approval').checked,
        generate_image: document.getElementById('gen_image').checked,
        generate_social_posts: document.getElementById('gen_social').checked,
        languages: document.getElementById('languages').value.split(',').map(s => s.trim()).filter(s => s)
    };

    try {
        log('Submitting request to API...');
        const response = await fetch('/api/v1/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        currentRequestId = data.request_id;

        requestSection.classList.add('hidden');
        statusSection.classList.remove('hidden');
        resetVisualizer();
        log(`Request ID: ${currentRequestId}`);

        connectStream(currentRequestId);

    } catch (err) {
        log(`Failed to start generation: ${err}`, 'error');
    }
});

// Approve Brief
approveBtn.addEventListener('click', async () => {
    if (!currentRequestId) return;

    try {
        log('Sending approval...');
        await fetch(`/api/v1/approve/${currentRequestId}`, { method: 'POST' });
        hitlPanel.classList.add('hidden');
    } catch (err) {
        log(`Failed to approve: ${err}`, 'error');
    }
});
