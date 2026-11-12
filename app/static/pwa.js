(() => {
  const button = document.querySelector('#install-app');
  let installPrompt;
  if ('serviceWorker' in navigator && window.isSecureContext) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/service-worker.js', { scope: '/', updateViaCache: 'none' })
        .catch(() => { /* Browsing still works if installation is unavailable. */ });
    });
  }
  if (!button) return;
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    installPrompt = event;
    button.hidden = false;
  });
  button.addEventListener('click', async () => {
    if (!installPrompt) return;
    const prompt = installPrompt;
    installPrompt = null;
    button.hidden = true;
    try {
      await prompt.prompt();
      await prompt.userChoice;
    } catch (_) { /* Browser installation remains available from its menu. */ }
  });
  window.addEventListener('appinstalled', () => {
    installPrompt = null;
    button.hidden = true;
  });
})();
