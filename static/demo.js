const steps = [
  { income: 3200, fixed: 2100, today: 30, days: 12, status: "OK",     budget: 91,  msg: "You’re within your expected pace." },
  { income: 3200, fixed: 2100, today: 160, days: 12, status: "DANGER", budget: 91,  msg: "This puts serious pressure on your month." },
  { income: 3200, fixed: 2100, today: 95, days: 12, status: "CAUTION", budget: 91,  msg: "You’re a bit above the safe pace." },
];

let i = 0;

function money(n){ return `$${n.toLocaleString()}`; }

function render(s){
  document.getElementById("d_income").textContent = money(s.income);
  document.getElementById("d_fixed").textContent  = money(s.fixed);
  document.getElementById("d_today").textContent  = money(s.today);
  document.getElementById("d_days").textContent   = String(s.days);

  document.getElementById("d_tag").textContent    = s.status;
  document.getElementById("d_budget").textContent = `$${s.budget}/day`;
  document.getElementById("d_msg").textContent    = s.msg;

  const box = document.getElementById("d_box");
  box.style.borderColor =
    s.status === "DANGER" ? "rgba(255,80,80,.35)" :
    s.status === "CAUTION" ? "rgba(255,190,80,.35)" :
    "rgba(80,255,160,.28)";
}

render(steps[0]);
setInterval(() => {
  i = (i + 1) % steps.length;
  render(steps[i]);
}, 2200);
