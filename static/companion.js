const thread = document.getElementById("assistantThread");
const input = document.getElementById("assistantInput");
const sendBtn = document.getElementById("assistantSend");
const actionButtons = document.querySelectorAll(".assistant-action");

const appendMsg = (text, cls = "") => {
  if (!thread) return;
  const div = document.createElement("div");
  div.className = `assistant-msg ${cls}`.trim();
  div.textContent = text;
  thread.appendChild(div);
  thread.scrollTop = thread.scrollHeight;
};

const sendMessage = async (text) => {
  if (!text) return;
  appendMsg(text, "user");
  if (input) input.value = "";
  try {
    const body = new URLSearchParams({ message: text });
    const res = await fetch("/companion", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    const data = await res.json();
    appendMsg(data.reply || "I’m here to help.");
  } catch {
    appendMsg("I couldn’t reach the Companion. Try again.");
  }
};

if (sendBtn && input) {
  sendBtn.addEventListener("click", () => sendMessage(input.value.trim()));
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMessage(input.value.trim());
    }
  });
}

actionButtons.forEach((btn) => {
  btn.addEventListener("click", () => sendMessage(btn.dataset.msg || btn.textContent));
});
