/**
 * Job-Pilot AI Chrome Extension — Popup Script
 */

const FRONTEND_URL = 'http://localhost:3000';
const SUPPORTED_DOMAINS = [
  'linkedin.com', 'indeed.com', 'greenhouse.io', 'lever.co',
  'workday.com', 'myworkdayjobs.com', 'ashbyhq.com', 'wellfound.com',
];

let currentUrl = '';

// ── Initialization ────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  // Get current tab URL
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  currentUrl = tab?.url || '';
  document.getElementById('currentUrl').textContent = currentUrl || 'No URL detected';

  // Check authentication
  const storage = await chrome.storage.local.get(['access_token']);
  const isLoggedIn = !!storage.access_token;

  if (!isLoggedIn) {
    document.getElementById('authPrompt').style.display = 'block';
  } else {
    document.getElementById('loggedInContent').style.display = 'block';
    updateStatusBadge(currentUrl);
  }

  // Event listeners
  document.getElementById('saveBtn')?.addEventListener('click', handleSave);
  document.getElementById('openAppBtn')?.addEventListener('click', () => {
    chrome.tabs.create({ url: FRONTEND_URL });
  });
  document.getElementById('openDashboard')?.addEventListener('click', (e) => {
    e.preventDefault();
    chrome.tabs.create({ url: `${FRONTEND_URL}/jobs` });
  });
});

// ── UI Helpers ────────────────────────────────────────────────────────────────

function updateStatusBadge(url) {
  const badge = document.getElementById('statusBadge');
  const text = document.getElementById('statusText');
  const isSupported = SUPPORTED_DOMAINS.some(d => url.includes(d));

  if (isSupported) {
    badge.className = 'status-badge supported';
    text.textContent = 'Supported job board detected';
  } else {
    badge.className = 'status-badge unsupported';
    text.textContent = 'Will attempt extraction from any URL';
  }
}

function showFeedback(message, type) {
  const div = document.getElementById('feedbackDiv');
  div.textContent = message;
  div.className = `feedback ${type}`;
}

function setLoading(loading) {
  const btn = document.getElementById('saveBtn');
  const proc = document.getElementById('processingDiv');
  btn.style.display = loading ? 'none' : 'flex';
  proc.style.display = loading ? 'flex' : 'none';
}

// ── Save Handler ──────────────────────────────────────────────────────────────

async function handleSave() {
  if (!currentUrl || !currentUrl.startsWith('http')) {
    showFeedback('❌ No valid URL detected on this page.', 'error');
    return;
  }

  setLoading(true);
  document.getElementById('feedbackDiv').className = 'feedback';

  const result = await chrome.runtime.sendMessage({
    type: 'SAVE_JOB',
    url: currentUrl,
  });

  setLoading(false);

  if (result.success) {
    showFeedback('✅ Job saved! AI extraction is running in the background.', 'success');
    // Disable save button
    document.getElementById('saveBtn').disabled = true;
    document.getElementById('saveBtn').querySelector('span:last-child').textContent = 'Saved!';
  } else {
    showFeedback(`❌ ${result.error}`, 'error');
  }
}
