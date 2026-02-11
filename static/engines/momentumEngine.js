(() => {
  const auras = document.querySelectorAll(".momentum-aura");
  if (!auras.length) return;
  auras.forEach((aura) => {
    const status = aura.dataset.status || "ok";
    aura.classList.remove("ok", "caution", "danger");
    aura.classList.add(status);
  });
})();
