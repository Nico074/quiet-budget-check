const commandOverlay = document.getElementById("commandOverlay");
const commandInput = document.getElementById("commandInput");
const commandList = document.getElementById("commandList");

const commandItems = [
  { label: "Dashboard", hint: "Go to dashboard", href: "/dashboard" },
  { label: "Run a check", hint: "Start a new check", href: "/run-check" },
  { label: "History", hint: "View checks history", href: "/history" },
  { label: "Goals", hint: "Create or update goals", href: "/goals" },
  { label: "Wallet overview", hint: "Open wallet", href: "/wallet" },
  { label: "Account", hint: "Profile and preferences", href: "/account" },
  { label: "Billing", hint: "Plan and payments", href: "/billing" },
  { label: "Upgrade", hint: "Upgrade to Pro", href: "/upgrade" },
  { label: "New goal", hint: "Jump to Goals", href: "/goals" },
  { label: "Export CSV", hint: "Open History export", href: "/history?export=1" },
];

let filtered = [...commandItems];
let activeIndex = 0;

const renderList = () => {
  commandList.innerHTML = "";
  filtered.forEach((item, idx) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "command-item";
    row.setAttribute("role", "option");
    row.dataset.index = idx.toString();
    row.innerHTML = `<span>${item.label}</span><span class="muted small">${item.hint}</span>`;
    if (idx === activeIndex) row.classList.add("active");
    row.addEventListener("click", () => {
      window.location.href = item.href;
    });
    commandList.appendChild(row);
  });
};

const openCommand = () => {
  commandOverlay.classList.add("open");
  commandOverlay.setAttribute("aria-hidden", "false");
  commandInput.value = "";
  filtered = [...commandItems];
  activeIndex = 0;
  renderList();
  commandInput.focus();
};

const closeCommand = () => {
  commandOverlay.classList.remove("open");
  commandOverlay.setAttribute("aria-hidden", "true");
};

const updateFilter = (value) => {
  const q = value.toLowerCase().trim();
  filtered = commandItems.filter(
    (item) =>
      item.label.toLowerCase().includes(q) ||
      item.hint.toLowerCase().includes(q)
  );
  activeIndex = 0;
  renderList();
};

document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    openCommand();
  }
  if (e.key === "Escape" && commandOverlay.classList.contains("open")) {
    closeCommand();
  }
});

const trigger = document.querySelector(".command-trigger");
if (trigger) {
  trigger.addEventListener("click", () => {
    openCommand();
  });
}

commandOverlay?.addEventListener("click", (e) => {
  if (e.target === commandOverlay) closeCommand();
});

commandInput?.addEventListener("input", (e) => {
  updateFilter(e.target.value);
});

commandInput?.addEventListener("keydown", (e) => {
  if (!filtered.length) return;
  if (e.key === "ArrowDown") {
    e.preventDefault();
    activeIndex = (activeIndex + 1) % filtered.length;
    renderList();
  }
  if (e.key === "ArrowUp") {
    e.preventDefault();
    activeIndex = (activeIndex - 1 + filtered.length) % filtered.length;
    renderList();
  }
  if (e.key === "Enter") {
    e.preventDefault();
    window.location.href = filtered[activeIndex].href;
  }
});
