/**
 * Job-Pilot AI Content Script
 * Injects a floating "Save to Job-Pilot" button on supported job pages.
 */

(function () {
  'use strict';

  // Don't inject twice
  if (document.getElementById('jobpilot-btn')) return;

  const button = document.createElement('div');
  button.id = 'jobpilot-btn';
  button.innerHTML = `
    <div class="jp-icon">🚀</div>
    <span class="jp-label">Save to Job-Pilot</span>
  `;
  button.title = 'Save this job to Job-Pilot AI';

  document.body.appendChild(button);

  button.addEventListener('click', async () => {
    button.classList.add('jp-loading');
    button.querySelector('.jp-label').textContent = 'Saving...';

    const result = await chrome.runtime.sendMessage({
      type: 'SAVE_JOB',
      url: window.location.href,
    });

    if (result.success) {
      button.classList.remove('jp-loading');
      button.classList.add('jp-success');
      button.querySelector('.jp-icon').textContent = '✅';
      button.querySelector('.jp-label').textContent = 'Saved!';
      setTimeout(() => { button.classList.remove('jp-success'); }, 3000);
    } else {
      button.classList.remove('jp-loading');
      button.classList.add('jp-error');
      button.querySelector('.jp-icon').textContent = '❌';
      button.querySelector('.jp-label').textContent = result.error || 'Error';
      setTimeout(() => {
        button.classList.remove('jp-error');
        button.querySelector('.jp-icon').textContent = '🚀';
        button.querySelector('.jp-label').textContent = 'Save to Job-Pilot';
      }, 4000);
    }
  });
})();
