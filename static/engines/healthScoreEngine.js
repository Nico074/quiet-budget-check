(() => {
  const el = document.getElementById("healthScore");
  if (!el) return;
  const target = parseInt(el.dataset.score || el.textContent || "0", 10);
  const trend = parseInt(el.dataset.trend || "0", 10);
  const trendEl = document.getElementById("healthTrend");
  let current = 0;

  const animate = () => {
    current = Math.min(target, current + 2);
    el.textContent = current;
    if (current < target) requestAnimationFrame(animate);
  };
  requestAnimationFrame(animate);

  if (trendEl) {
    trendEl.textContent = `${trend > 0 ? "▲ +" : trend < 0 ? "▼ " : ""}${trend}`;
  }

  const ring = el.closest(".score-ring");
  if (ring) {
    ring.classList.add("pulse");
    setTimeout(() => ring.classList.remove("pulse"), 260);
  }
})();
