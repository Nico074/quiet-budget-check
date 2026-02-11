const stepsByPeriod = {
  monthly: [
    { income: 3200, fixed: 2100, days: 12, today: 30, status: "OK", budget: 91, msg: "You’re within your expected pace." },
    { income: 3400, fixed: 2300, days: 14, today: 160, status: "ATTENTION", budget: 78, msg: "This puts serious pressure on your month." },
    { income: 3100, fixed: 1950, days: 11, today: 95, status: "CAUTION", budget: 105, msg: "You’re a bit above the safe pace." },
  ],
  fortnightly: [
    { income: 1600, fixed: 1050, days: 10, today: 20, status: "OK", budget: 55, msg: "You’re within your expected pace." },
    { income: 1700, fixed: 1200, days: 9, today: 95, status: "ATTENTION", budget: 40, msg: "This puts serious pressure on your period." },
    { income: 1500, fixed: 980, days: 8, today: 60, status: "CAUTION", budget: 58, msg: "You’re a bit above the safe pace." },
  ],
  weekly: [
    { income: 800, fixed: 520, days: 5, today: 15, status: "OK", budget: 53, msg: "You’re within your expected pace." },
    { income: 820, fixed: 600, days: 4, today: 55, status: "ATTENTION", budget: 35, msg: "This puts serious pressure on your week." },
    { income: 760, fixed: 480, days: 4, today: 35, status: "CAUTION", budget: 45, msg: "You’re a bit above the safe pace." },
  ],
};

let i = 0;

function money(n){ return `$${n.toLocaleString()}`; }

const periodSelect = document.getElementById("period");
const demoIncomeLabel = document.getElementById("demoIncomeLabel");
const demoFixedLabel = document.getElementById("demoFixedLabel");
const demoTodayLabel = document.getElementById("demoTodayLabel");
const demoDaysLabel = document.getElementById("demoDaysLabel");
const demoIncomeVal = document.getElementById("demoIncomeVal");
const demoFixedVal = document.getElementById("demoFixedVal");
const demoTodayVal = document.getElementById("demoTodayVal");
const demoDaysVal = document.getElementById("demoDaysVal");

const periodConfig = {
  monthly: {
    incomeLabel: "Monthly income",
    fixedLabel: "Fixed expenses",
    todayLabel: "Today’s spend",
    daysLabel: "Days left",
    income: 3200,
    fixed: 2100,
    days: 12,
  },
  fortnightly: {
    incomeLabel: "Income (2 weeks)",
    fixedLabel: "Fixed expenses (2 weeks)",
    todayLabel: "Today’s spend",
    daysLabel: "Days left (2 weeks)",
    income: 1600,
    fixed: 1050,
    days: 10,
  },
  weekly: {
    incomeLabel: "Weekly income",
    fixedLabel: "Fixed expenses (week)",
    todayLabel: "Today’s spend",
    daysLabel: "Days left (week)",
    income: 800,
    fixed: 520,
    days: 5,
  },
};

function currentPeriod() {
  if (periodSelect && periodConfig[periodSelect.value]) {
    return periodConfig[periodSelect.value];
  }
  return periodConfig.monthly;
}

function currentSteps() {
  const key = periodSelect && stepsByPeriod[periodSelect.value] ? periodSelect.value : "monthly";
  return stepsByPeriod[key];
}

function applyPeriodUI() {
  const p = currentPeriod();
  if (demoIncomeLabel) demoIncomeLabel.textContent = p.incomeLabel;
  if (demoFixedLabel) demoFixedLabel.textContent = p.fixedLabel;
  if (demoTodayLabel) demoTodayLabel.textContent = p.todayLabel;
  if (demoDaysLabel) demoDaysLabel.textContent = p.daysLabel;
  if (demoIncomeVal) demoIncomeVal.textContent = money(p.income);
  if (demoFixedVal) demoFixedVal.textContent = money(p.fixed);
  if (demoDaysVal) demoDaysVal.textContent = String(p.days);
}

function render(s){
  const p = currentPeriod();
  if (demoIncomeVal) demoIncomeVal.textContent = money(s.income);
  if (demoFixedVal) demoFixedVal.textContent = money(s.fixed);
  if (demoTodayVal) demoTodayVal.textContent = money(s.today);
  if (demoDaysVal) demoDaysVal.textContent = String(s.days);

  if (demoIncomeLabel) demoIncomeLabel.textContent = p.incomeLabel;
  if (demoFixedLabel) demoFixedLabel.textContent = p.fixedLabel;
  if (demoTodayLabel) demoTodayLabel.textContent = p.todayLabel;
  if (demoDaysLabel) demoDaysLabel.textContent = p.daysLabel;

  document.getElementById("d_budget").textContent = `$${s.budget}/day`;
  document.getElementById("d_msg").textContent    = s.msg;

  const box = document.getElementById("d_box");
  box.style.borderColor =
    s.status === "ATTENTION" ? "rgba(255,80,80,.35)" :
    s.status === "CAUTION" ? "rgba(255,190,80,.35)" :
    "rgba(80,255,160,.28)";
}

applyPeriodUI();
render(currentSteps()[0]);
if (periodSelect) {
  periodSelect.addEventListener("change", () => {
    applyPeriodUI();
    i = 0;
    render(currentSteps()[i]);
  });
}
setInterval(() => {
  const steps = currentSteps();
  i = (i + 1) % steps.length;
  render(steps[i]);
}, 2200);
