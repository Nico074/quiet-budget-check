(() => {
  const streakGlow = document.querySelector(".streak-glow");
  if (!streakGlow) return;
  const streak = parseInt(streakGlow.dataset.streak || "0", 10);
  if (streak >= 3) {
    streakGlow.classList.add("active");
  }
})();
