(() => {
  const species = document.querySelector('#animal-species');
  const breed = document.querySelector('#animal-breed');
  const data = document.querySelector('#animal-options');
  if (!species || !breed || !data) return;
  const breeds = JSON.parse(data.textContent);
  function updateBreeds(preserveExisting = false) {
    const current = breed.value;
    const choices = breeds[species.value] || [...new Set(Object.values(breeds).flat())];
    const options = [new Option('Não informada', '')];
    if (preserveExisting && current && !choices.includes(current)) {
      options.push(new Option(current, current));
    }
    options.push(...choices.map(name => new Option(name, name)));
    breed.replaceChildren(...options);
    breed.value = choices.includes(current) || preserveExisting ? current : '';
  }
  species.addEventListener('change', () => updateBreeds());
  // Preserve legacy/custom breeds on edit without carrying dog breeds over to cats.
  updateBreeds(true);
})();
