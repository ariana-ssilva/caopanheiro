(() => {
  const input = document.querySelector('[data-photo-input], #animal-photo');
  if (!input) return;
  const preview = document.querySelector('#selected-photo-preview');
  const message = document.querySelector('#photo-preview-message');
  let objectUrl;
  function clearPreview() {
    preview.hidden = true;
    preview.removeAttribute('src');
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = null;
  }
  input.addEventListener('change', () => {
    clearPreview();
    input.setCustomValidity('');
    message.textContent = '';
    const file = input.files[0];
    if (!file) return;
    if (!/\.(jpe?g|png|webp)$/i.test(file.name) || file.size > 5 * 1024 * 1024) {
      const error = 'Selecione uma foto JPG, PNG ou WEBP de até 5 MB.';
      input.setCustomValidity(error);
      message.textContent = error;
      return;
    }
    objectUrl = URL.createObjectURL(file);
    preview.onload = () => {
      preview.hidden = false;
      message.textContent = 'Prévia da foto selecionada. Salve o formulário para confirmar.';
    };
    preview.onerror = () => {
      clearPreview();
      const error = 'Não foi possível abrir essa imagem. Selecione outra foto.';
      input.setCustomValidity(error);
      message.textContent = error;
    };
    preview.src = objectUrl;
  });
  window.addEventListener('pagehide', clearPreview);
})();
