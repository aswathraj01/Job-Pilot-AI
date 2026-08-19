/**
 * Job-Pilot AI Background Service Worker (Manifest V3)
 * Handles API communication with the Job-Pilot backend.
 */

const API_BASE = 'http://localhost:8000/api/v1';

/**
 * Save a job URL to Job-Pilot AI.
 * @param {string} url - The job posting URL
 * @param {string} accessToken - JWT access token
 * @returns {Promise<{success: boolean, job?: object, error?: string}>}
 */
async function saveJobToAPI(url, accessToken) {
  try {
    const response = await fetch(`${API_BASE}/jobs/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ url, status: 'saved' }),
    });

    if (response.status === 409) {
      return { success: false, error: 'Job is already being tracked!' };
    }
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      return { success: false, error: err.detail || `API error ${response.status}` };
    }

    const job = await response.json();
    return { success: true, job };
  } catch (err) {
    return { success: false, error: `Network error: ${err.message}` };
  }
}

/**
 * Refresh the access token using the stored refresh token.
 */
async function refreshAccessToken(refreshToken) {
  try {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

// ── Message Handler ────────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'SAVE_JOB') {
    handleSaveJob(message.url).then(sendResponse);
    return true; // Keep channel open for async response
  }

  if (message.type === 'GET_CURRENT_TAB_URL') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      sendResponse({ url: tabs[0]?.url || '' });
    });
    return true;
  }

  if (message.type === 'CHECK_AUTH') {
    chrome.storage.local.get(['access_token'], (result) => {
      sendResponse({ isLoggedIn: !!result.access_token });
    });
    return true;
  }
});

async function handleSaveJob(url) {
  const storage = await chrome.storage.local.get(['access_token', 'refresh_token']);
  let accessToken = storage.access_token;

  if (!accessToken) {
    return { success: false, error: 'Not logged in. Open Job-Pilot AI and sign in first.' };
  }

  let result = await saveJobToAPI(url, accessToken);

  // If 401, try token refresh
  if (!result.success && result.error?.includes('401')) {
    const refreshToken = storage.refresh_token;
    if (refreshToken) {
      const newTokens = await refreshAccessToken(refreshToken);
      if (newTokens) {
        await chrome.storage.local.set({
          access_token: newTokens.access_token,
          refresh_token: newTokens.refresh_token,
        });
        result = await saveJobToAPI(url, newTokens.access_token);
      }
    }
  }

  return result;
}
