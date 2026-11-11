(() => {
  const form = document.querySelector('#adoption-form');
  if (!form) return;
  const steps = [...form.querySelectorAll('[data-step]')];
  const progress = [...document.querySelectorAll('.step-progress li')];
  const back = document.querySelector('#step-back');
  const next = document.querySelector('#step-next');
  const submit = document.querySelector('#step-submit');
  const review = document.querySelector('#adoption-review');
  let current = 0;
  function validStep() {
    return [...steps[current].querySelectorAll('input, textarea')].every(field => field.reportValidity());
  }
  function show(focus = true) {
    steps.forEach((step, index) => { step.hidden = index !== current; });
    progress.forEach((item, index) => {
      item.classList.toggle('active', index === current);
      if (index === current) item.setAttribute('aria-current', 'step');
      else item.removeAttribute('aria-current');
    });
    back.hidden = current === 0;
    next.hidden = current === steps.length - 1;
    submit.hidden = current !== steps.length - 1;
    if (current === steps.length - 1) {
      review.replaceChildren();
      const labels = {full_name: 'Nome', phone: 'Telefone', housing: 'Moradia', household: 'Moradores', experience: 'Experiência', message: 'Mensagem'};
      for (const [name, label] of Object.entries(labels)) {
        const title = document.createElement('dt');
        const value = document.createElement('dd');
        title.textContent = label;
        value.textContent = form.elements[name].value;
        review.append(title, value);
      }
    }
    if (focus) {
      const legend = steps[current].querySelector('legend');
      legend.tabIndex = -1;
      legend.focus();
    }
  }
  // Validation runs on the visible step; the server validates the complete submission.
  form.noValidate = true;
  next.addEventListener('click', () => { if (validStep()) { current++; show(); } });
  back.addEventListener('click', () => { current--; show(); });
  form.addEventListener('submit', event => {
    if (!validStep()) { event.preventDefault(); return; }
    if (current < steps.length - 1) { event.preventDefault(); current++; show(); return; }
    submit.disabled = true;
    submit.textContent = 'Enviando…';
  });
  show(false);
})();
