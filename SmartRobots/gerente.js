(() => {
  "use strict";

  /* ─── Backend URL ─── */
  const BACKEND_URL = "http://localhost:8000";

  /* ─── Utilities ─── */
  const $ = (id) => document.getElementById(id);
  const norm = (s) =>
    String(s)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, "");
  let toastTimer;
  function toast(msg, type = "") {
    const el = $("toast");
    el.textContent = msg;
    el.className = "toast visible" + (type ? " " + type : "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (el.className = "toast"), 3000);
  }

  let cases = [];
  let canManage = false;
  function authHeaders() {
    return {"Content-Type": "application/json", Authorization: "Token " + (localStorage.getItem("bbIA_token") || "")};
  }

  /* ─── State ─── */
  const state = {
    selectedCase: cases.length ? cases[0].id : null,
    filter: "all",
    searchQuery: "",
  };

  // Token passed from chat page via URL (e.g. gerente.html?token=AT-2044)
  // Applied after fetchBackendCases() loads data, not here (cases is empty at init).
  const urlToken = new URLSearchParams(location.search).get("token");

  async function patchBackendCase(token, patch) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/cases/${token}/`, {
        method: "PATCH", headers: authHeaders(), body: JSON.stringify(patch),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Falha ao salvar atendimento.");
      await fetchBackendCases();
      toast("Atendimento atualizado.");
    } catch (error) { toast(error.message, "error"); await fetchBackendCases(); }
  }
  async function fetchBackendCases() {
    try {
      const response = await fetch(`${BACKEND_URL}/api/cases/`, {headers: authHeaders()});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Falha ao carregar atendimentos.");
      cases = data.cases.map((c) => ({...c, ts: new Date(c.ts)}));
      canManage = data.can_manage === true;
      // Deep-link: if a token was passed in the URL and exists, select it; otherwise keep current or first.
      if (urlToken && cases.some((c) => c.id === urlToken)) {
        state.selectedCase = urlToken;
      } else if (!cases.some((c) => c.id === state.selectedCase)) {
        state.selectedCase = cases[0]?.id || null;
      }
      renderManager();
    } catch (error) {
      cases = []; canManage = false; renderManager(); toast(error.message, "error");
    }
  }

  /* ─── Helpers ─── */
  function stateLabel(s) {
    return s === "waiting"
      ? ["Aguardando", "status-wait"]
      : s === "active"
        ? ["Em atendimento", "status-active"]
        : ["Concluído", "status-done"];
  }
  function priorityLabel(p) {
    return p === "high"
      ? ["Alta", "pb-high"]
      : p === "low"
        ? ["Baixa", "pb-low"]
        : ["Normal", "pb-medium"];
  }

  function filteredCases() {
    return cases.filter((c) => {
      if (state.filter !== "all" && c.status !== state.filter) return false;
      if (state.searchQuery) {
        const q = norm(state.searchQuery);
        if (
          !norm(c.id).includes(q) &&
          !norm(c.intent).includes(q) &&
          !norm(c.owner).includes(q)
        )
          return false;
      }
      return true;
    });
  }

  /* ─── Render manager ─── */
  function renderManager() {
    $("metric-waiting").textContent = cases.filter(
      (c) => c.status === "waiting",
    ).length;
    $("metric-active").textContent = cases.filter(
      (c) => c.status === "active",
    ).length;
    $("metric-done").textContent = cases.filter(
      (c) => c.status === "done",
    ).length;
    $("metric-high").textContent = cases.filter(
      (c) => c.priority === "high" && c.status !== "done",
    ).length;

    const list = $("case-list");
    list.replaceChildren();
    const visible = filteredCases();
    if (!visible.length) {
      const empty = document.createElement("p");
      empty.style.cssText =
        "text-align:center;color:#99a1b2;font-size:12.5px;padding:40px 10px;";
      empty.textContent = "Nenhum caso encontrado.";
      list.append(empty);
      renderSummary();
      return;
    }
    for (const c of [...visible].sort((a, b) => {
      const order = { high: 0, medium: 1, low: 2 };
      const so = { waiting: 0, active: 1, done: 2 };
      return (
        so[a.status] - so[b.status] ||
        (order[a.priority] || 1) - (order[b.priority] || 1)
      );
    })) {
      const row = document.createElement("button");
      row.type = "button";
      row.setAttribute("role", "listitem");
      row.className =
        "case-row" + (state.selectedCase === c.id ? " selected" : "");
      row.setAttribute(
        "aria-pressed",
        state.selectedCase === c.id ? "true" : "false",
      );
      const left = document.createElement("span");
      left.className = "case-left";
      const title = document.createElement("span");
      title.className = "case-title";
      title.textContent = c.id + " · " + c.intent;
      left.append(title);
      const owner = document.createElement("span");
      owner.className = "case-desc";
      owner.textContent = c.owner;
      left.append(owner);
      const meta = document.createElement("span");
      meta.className = "case-meta";
      const [sl, sc] = stateLabel(c.status);
      const stag = document.createElement("span");
      stag.className = "status " + sc;
      stag.textContent = sl;
      meta.append(stag);
      const [pl, pc] = priorityLabel(c.priority);
      const ptag = document.createElement("span");
      ptag.className = "priority-badge " + pc;
      ptag.textContent = pl;
      meta.append(ptag);
      const age = document.createElement("span");
      age.style.cssText = "font-size:10.5px;color:#99a1b2;";
      const mins = Math.floor((Date.now() - c.ts) / 60000);
      age.textContent =
        mins < 1
          ? "agora"
          : mins < 60
            ? mins + "min"
            : Math.floor(mins / 60) + "h";
      meta.append(age);
      left.append(meta);
      row.append(left);
      row.addEventListener("click", () => {
        state.selectedCase = c.id;
        renderManager();
      });
      list.append(row);
    }
    renderSummary();
  }

  function addField(parent, label, value) {
    const d = document.createElement("div");
    d.className = "summary-field";
    const lb = document.createElement("label");
    lb.textContent = label;
    const p = document.createElement("p");
    p.textContent = value || "Não informado";
    d.append(lb, p);
    parent.append(d);
  }

  function renderSummary() {
    const parent = $("case-summary");
    parent.replaceChildren();
    const c = cases.find((x) => x.id === state.selectedCase);
    if (!c) {
      parent.innerHTML =
        '<p class="summary-empty">Selecione um caso na fila para ver o resumo detalhado.</p>';
      return;
    }

    const chip = document.createElement("span");
    chip.className = "case-chip";
    chip.textContent =
      c.id +
      " · " +
      stateLabel(c.status)[0] +
      " · Prioridade: " +
      priorityLabel(c.priority)[0];
    parent.append(chip);

    addField(parent, "Cliente", c.owner);
    addField(parent, "Motivo do contato", c.description);
    addField(
      parent,
      "Informações coletadas pelo agente",
      c.information.length ? c.information.join("\n") : "Sem coleta adicional.",
    );
    addField(parent, "Orientações fornecidas", c.actions);
    addField(parent, "Documentos possivelmente necessários", c.documents);
    addField(parent, "Motivo do encaminhamento", c.reason);

    // Conversation history
    if (c.chat_history && c.chat_history.length) {
      const histField = document.createElement("div");
      histField.className = "summary-field";
      const histLb = document.createElement("label");
      histLb.textContent = "Histórico da conversa com o agente";
      histField.append(histLb);
      const histBox = document.createElement("div");
      histBox.style.cssText = "background:#f7f8fa;border:1px solid #e5e7eb;border-radius:6px;padding:10px 12px;max-height:320px;overflow-y:auto;font-size:12.5px;line-height:1.55;";
      c.chat_history
        .filter((m) => m.role !== "system")
        .forEach((m) => {
          const line = document.createElement("div");
          line.style.cssText = "margin-bottom:8px;";
          const who = document.createElement("strong");
          who.style.cssText = "display:inline-block;min-width:72px;color:" + (m.role === "user" ? "#1a56db" : "#374151") + ";";
          who.textContent = m.role === "user" ? "Cliente:" : "BB IA:";
          const txt = document.createElement("span");
          txt.style.cssText = "margin-left:6px;white-space:pre-wrap;color:#374151;";
          txt.textContent = m.content;
          line.append(who, txt);
          histBox.append(line);
        });
      histField.append(histBox);
      parent.append(histField);
    }

    // Notes
    const noteField = document.createElement("div");
    noteField.className = "summary-field";
    const noteLb = document.createElement("label");
    noteLb.textContent = "Notas do gerente";
    const noteArea = document.createElement("textarea");
    noteArea.className = "notes-area";
    noteArea.placeholder = "Adicione observações para este atendimento...";
    noteArea.value = c.notes || "";
    noteArea.disabled = !canManage;
    noteArea.addEventListener("change", () => patchBackendCase(c.id, {notes: noteArea.value}));
    noteField.append(noteLb, noteArea);
    parent.append(noteField);

    // Actions
    const actions = document.createElement("div");
    actions.className = "manager-actions";
    const start = document.createElement("button");
    start.className = "button button-blue";
    start.textContent = "▶ Iniciar atendimento";
    start.disabled = !canManage || c.status !== "waiting";
    start.addEventListener("click", () => patchBackendCase(c.id, {status: "active"}));
    const done = document.createElement("button");
    done.className = "button button-quiet";
    done.textContent = "✓ Marcar como concluído";
    done.disabled = !canManage || c.status !== "active";
    done.addEventListener("click", () => patchBackendCase(c.id, {status: "done"}));
    const reopen = document.createElement("button");
    reopen.className = "button button-outline";
    reopen.style.cssText =
      "color:#66718d;border-color:#ccc;background:#f7f7f7;";
    reopen.textContent = "↺ Reabrir";
    reopen.disabled = !canManage || c.status !== "done";
    reopen.addEventListener("click", () => patchBackendCase(c.id, {status: "waiting"}));
    actions.append(start, done, reopen);
    parent.append(actions);
  }

  /* ─── Event wiring ─── */
  $("menu-btn").addEventListener("click", () => {
    const m = $("mobile-menu");
    const o = m.classList.toggle("open");
    $("menu-btn").setAttribute("aria-expanded", String(o));
  });

  document.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".filter-btn")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.filter = btn.dataset.filter;
      renderManager();
    });
  });

  $("case-search").addEventListener("input", (e) => {
    state.searchQuery = e.target.value.trim();
    renderManager();
  });

  /* ─── Boot ─── */
  renderManager();
  // Carrega a fila persistida no servidor.
  fetchBackendCases();
})();
