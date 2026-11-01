(() => {
  "use strict";
  const BACKEND_URL = "http://localhost:8000";
  const $ = (id) => document.getElementById(id);
  const messages = [];
  let busy = false;
  let sessionId = crypto.randomUUID();
  let pending = false;
  const topics = ["Suspeita de fraude", "Problema na conta", "Simular empréstimo", "Aumento de limite do cartão"];
  function toast(text) {
    $("toast").textContent = text;
    $("toast").classList.add("visible");
    setTimeout(() => $("toast").classList.remove("visible"), 5000);
  }
  function stage(n) {
    document.querySelectorAll(".timeline-item").forEach((el) => {
      const step = Number(el.dataset.step);
      el.classList.toggle("active", step === n);
      el.classList.toggle("complete", step < n);
    });
    $("chat-progress").style.width = (n === 3 ? 100 : n === 2 ? 55 : 15) + "%";
  }
  function setBusy(value) {
    busy = value;
    $("message-input").disabled = value;
    $("send-btn").disabled = value;
    $("reset-chat").disabled = value;
    $("chat-input-wrap").classList.toggle("disabled", value);
    document.querySelectorAll(".quick-action").forEach((b) => b.disabled = value);
  }
  function addMsg(from, text, choices = []) {
    messages.push({from, text, choices});
    const chat = $("chat-messages");
    chat.replaceChildren();
    messages.forEach((msg, index) => {
      const row = document.createElement("div");
      row.className = "message " + msg.from;
      if (msg.from === "assistant") {
        const avatar = document.createElement("span");
        avatar.className = "msg-avatar";
        avatar.textContent = "✦";
        row.append(avatar);
      }
      const bubble = document.createElement("div");
      bubble.className = "bubble";
      bubble.style.whiteSpace = "pre-wrap";
      bubble.textContent = msg.text;
      row.append(bubble);
      chat.append(row);
      if (index === messages.length - 1 && msg.choices.length) {
        const actions = document.createElement("div");
        actions.className = "quick-actions";
        msg.choices.forEach((label) => {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "quick-action";
          button.textContent = label;
          button.addEventListener("click", () => send(label));
          actions.append(button);
        });
        chat.append(actions);
      }
    });
    chat.scrollTop = chat.scrollHeight;
  }
  function welcome() {
    messages.length = 0;
    pending = false;
    $("token-card").classList.remove("visible");
    stage(1);
    addMsg("assistant", "Olá! Sou o BB IA, um assistente de atendimento bancário em um protótipo acadêmico. Posso orientar e registrar solicitações de simulação. Nenhuma operação bancária real é executada.\n\nNão envie senhas, CPF ou códigos de autenticação. Como posso ajudar?", topics);
  }
  async function api(path, body) {
    const token = localStorage.getItem("bbIA_token");
    if (!token) throw new Error("Entre na sua conta para conversar com o BB IA.");
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 90000);
    try {
      const response = await fetch(BACKEND_URL + path, {
        method: "POST",
        headers: {"Content-Type": "application/json", Authorization: "Token " + token},
        body: JSON.stringify(body), signal: controller.signal,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Não foi possível completar a solicitação.");
      return data;
    } finally { clearTimeout(timer); }
  }
  function showCase(c) {
    $("token-card").classList.add("visible");
    $("token-number").textContent = c.id;
    $("token-priority-badge").textContent = "Prioridade: " + ({high: "Alta", medium: "Normal", low: "Baixa"}[c.priority] || "Normal");
    $("token-position").textContent = "Atendimento de simulação";
    $("token-status").textContent = {waiting: "Aguardando", active: "Em atendimento", done: "Concluído"}[c.status] || c.status;
    stage(3);
  }
  async function send(raw) {
    const text = String(raw || "").trim();
    if (!text || busy) return;
    if (text === "Nova solicitação") return reset();
    if (text === "Ver painel do gerente") { location.href = "gerente.html"; return; }
    if (text.length > 4000) { toast("Use até 4000 caracteres por mensagem."); return; }
    $("message-input").value = "";
    addMsg("user", text);
    setBusy(true);
    $("sidebar").classList.toggle("fraud-mode", /fraude|golpe|clonagem/i.test(text));
    const payload = {message: text, session_id: sessionId};
    if (pending && text === "Confirmar atendimento") payload.action = "confirm_case";
    if (pending && text === "Cancelar encaminhamento") payload.action = "cancel_case";
    try {
      const result = await api("/api/chat/", payload);
      pending = Boolean(result.pending_confirmation);
      let choices = topics;
      if (pending) choices = ["Confirmar atendimento", "Cancelar encaminhamento"];
      if (result.case) { showCase(result.case); choices = ["Ver painel do gerente", "Nova solicitação"]; }
      else stage(2);
      addMsg("assistant", result.reply, choices);
    } catch (error) {
      addMsg("assistant", error.name === "AbortError" ? "A resposta demorou mais que o esperado. Se estava confirmando um atendimento, tente confirmar novamente nesta conversa para recuperar o mesmo protocolo." : error.message,
        pending ? ["Confirmar atendimento", "Cancelar encaminhamento"] : topics);
    } finally { setBusy(false); }
  }
  async function reset() {
    if (busy) return;
    setBusy(true);
    try {
      if (localStorage.getItem("bbIA_token")) await api("/api/chat/reset/", {session_id: sessionId});
      sessionId = crypto.randomUUID();
      welcome();
    } catch (error) { toast(error.message); }
    finally { setBusy(false); }
  }
  $("message-form").addEventListener("submit", (e) => { e.preventDefault(); send($("message-input").value); });
  $("message-input").maxLength = 4000;
  $("reset-chat").addEventListener("click", reset);
  $("menu-btn").addEventListener("click", () => {
    const open = $("mobile-menu").classList.toggle("open");
    $("menu-btn").setAttribute("aria-expanded", String(open));
  });
  welcome();
})();
