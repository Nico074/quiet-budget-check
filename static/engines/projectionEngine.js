(() => {
  const chart = document.querySelector(".projection-chart");
  if (!chart) return;
  const bars = Array.from(chart.querySelectorAll("span"));
  const base = bars.map((b) => parseFloat(b.style.getPropertyValue("--p")) || 55);
  const income = document.getElementById("projIncome");
  const expense = document.getElementById("projExpense");

  const apply = () => {
    const inc = income ? parseInt(income.value, 10) : 0;
    const exp = expense ? parseInt(expense.value, 10) : 0;
    const delta = Math.max(-20, Math.min(20, inc - exp));
    bars.forEach((b, i) => {
      const v = Math.max(30, Math.min(95, base[i] + delta));
      b.style.setProperty("--p", `${v}%`);
    });
  };

  if (income) income.addEventListener("input", apply);
  if (expense) expense.addEventListener("input", apply);
})();
