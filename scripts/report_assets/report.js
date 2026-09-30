"use strict";
(() => {
  const form = document.getElementById("filters");
  const suite = document.getElementById("suite");
  const focus = document.getElementById("focus");
  const search = document.getElementById("search");
  const cases = [...document.querySelectorAll("article.case")];
  const groups = [...document.querySelectorAll("#overview tbody")];
  const matchesExample = element => !suite.value || element.dataset.suite === suite.value;

  function update() {
    const query = search.value.trim().toLocaleLowerCase();
    let visible = 0;
    for (const card of cases) {
      card.hidden = !(matchesExample(card)
        && (!focus.value || card.dataset[focus.value] === "1")
        && (!query || card.dataset.search.toLocaleLowerCase().includes(query)));
      if (!card.hidden) visible += 1;
    }
    for (const group of groups) group.hidden = !matchesExample(group);
    document.getElementById("case-count").textContent = `${visible} of ${cases.length} inputs`;
    document.getElementById("empty-cases").hidden = visible !== 0;
  }

  form.addEventListener("submit", event => event.preventDefault());
  form.addEventListener("input", update);
  form.addEventListener("change", update);
  form.addEventListener("reset", () => setTimeout(update, 0));
  update();
})();
