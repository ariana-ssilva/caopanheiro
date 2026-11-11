(() => {
  const toggle = document.querySelector('.menu-toggle');
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.querySelector('.sidebar-overlay');
  if (!toggle || !sidebar || !overlay) return;
  const mobile = window.matchMedia('(max-width: 700px)');
  function setOpen(open, returnFocus = false) {
    document.body.classList.toggle('menu-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    overlay.hidden = !open;
    sidebar.inert = mobile.matches && !open;
    if (open) sidebar.querySelector('a').focus();
    else if (returnFocus) toggle.focus();
  }
  toggle.addEventListener('click', () => setOpen(toggle.getAttribute('aria-expanded') !== 'true'));
  overlay.addEventListener('click', () => setOpen(false, true));
  document.addEventListener('keydown', event => {
    if (toggle.getAttribute('aria-expanded') !== 'true') return;
    if (event.key === 'Escape') setOpen(false, true);
    if (event.key === 'Tab') {
      const items = [toggle, ...sidebar.querySelectorAll('a, button')];
      const first = items[0], last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  mobile.addEventListener('change', () => setOpen(false));
  setOpen(false);
})();
