(() => {
  const species = document.querySelector('#animal-species');
  const list = document.querySelector('#animal-breeds');
  const data = document.querySelector('#animal-options');
  if (!species || !list || !data) return;
  const breeds = JSON.parse(data.textContent);
  function updateBreeds() {
    const suggestions = breeds[species.value] || [...new Set(Object.values(breeds).flat())];
    list.replaceChildren(...suggestions.map(name => {
      const option = document.createElement('option');
      option.value = name;
      return option;
    }));
  }
  species.addEventListener('change', updateBreeds);
  // Keep an existing or manually entered breed when updating suggestions.
  updateBreeds();
})();
