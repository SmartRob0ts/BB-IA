(() => {
  "use strict";

  const BACKEND_URL = "http://localhost:8000";
  const $ = (id) => document.getElementById(id);

  /* ── Auth guard ──────────────────────────────────────────────────────────── */
  const token = localStorage.getItem("bbIA_token");
  if (!token) {
    window.location.replace("conta.html");
  }

  function authHeaders() {
    return { "Content-Type": "application/json", Authorization: "Token " + token };
  }

  /* ── Toast ───────────────────────────────────────────────────────────────── */
  let _toastTimer;
  function toast(msg, type = "") {
    const el = $("toast");
    el.textContent = msg;
    el.className = "toast visible" + (type ? " " + type : "");
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(() => (el.className = "toast"), 3500);
  }

  /* ── Mobile menu ─────────────────────────────────────────────────────────── */
  $("menu-btn").addEventListener("click", () => {
    const m = $("mobile-menu");
    const o = m.classList.toggle("open");
    $("menu-btn").setAttribute("aria-expanded", String(o));
  });

  /* ── Logout ──────────────────────────────────────────────────────────────── */
  $("logout-btn").addEventListener("click", async () => {
    try {
      await fetch(BACKEND_URL + "/api/auth/logout/", {
        method: "POST",
        headers: authHeaders(),
      });
    } catch { /* silencioso */ }
    localStorage.removeItem("bbIA_token");
    localStorage.removeItem("bbIA_user");
    window.location.replace("conta.html");
  });

  /* ── API helpers ─────────────────────────────────────────────────────────── */
  async function apiFetch(path, opts = {}) {
    const res = await fetch(BACKEND_URL + path, {
      headers: authHeaders(),
      ...opts,
    });
    if (res.status === 401) {
      localStorage.removeItem("bbIA_token");
      window.location.replace("conta.html");
      return null;
    }
    return { ok: res.ok, status: res.status, data: await res.json() };
  }

  function fmtBRL(n) {
    return Number(n).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     STATE
  ══════════════════════════════════════════════════════════════════════════ */
  let _profile = null;     // { pix_limit, credit_limit, credit_limit_changed }
  let _investments = [];   // array de investment objects

  /* ══════════════════════════════════════════════════════════════════════════
     BOOT — fetch user + profile + investments
  ══════════════════════════════════════════════════════════════════════════ */
  async function boot() {
    // Greeting from cached user data
    try {
      const cached = JSON.parse(localStorage.getItem("bbIA_user") || "{}");
      if (cached.name) {
        $("greeting-name").textContent = "Olá, " + cached.name.split(" ")[0] + "!";
        $("greeting-email").textContent = cached.email || "";
      }
    } catch { /* silencioso */ }

    // Fetch fresh user data
    const meRes = await apiFetch("/api/auth/me/");
    if (!meRes) return;
    if (meRes.ok) {
      const { user, profile } = meRes.data;
      localStorage.setItem("bbIA_user", JSON.stringify(user));
      $("greeting-name").textContent = "Olá, " + user.name.split(" ")[0] + "!";
      $("greeting-email").textContent = user.email;
      if (profile) {
        _profile = profile;
        renderProfile();
      }
    }

    // Fetch investments
    const invRes = await apiFetch("/api/investments/");
    if (!invRes) return;
    if (invRes.ok) {
      _investments = invRes.data.investments || [];
      renderInvestments();
    }
  }

  /* ══════════════════════════════════════════════════════════════════════════
     PROFILE / LIMITS
  ══════════════════════════════════════════════════════════════════════════ */
  function renderProfile() {
    if (!_profile) return;
    $("pix-limit-display").textContent    = fmtBRL(_profile.pix_limit);
    $("credit-limit-display").textContent = fmtBRL(_profile.credit_limit);

    const creditBtn    = $("credit-edit-btn");
    const lockedNotice = $("credit-locked-notice");
    const creditSub    = $("credit-limit-sub");

    if (_profile.credit_limit_changed) {
      creditBtn.disabled = true;
      lockedNotice.hidden = false;
      creditSub.innerHTML = "Limite já alterado — <strong>solicite aumento via agente</strong>";
    } else {
      creditBtn.disabled = false;
      lockedNotice.hidden = true;
      creditSub.innerHTML = "Pode ser alterado <strong>uma vez</strong> pelo cliente";
    }
  }

  // ── Edit buttons ─────────────────────────────────────────────────────────
  document.querySelectorAll(".edit-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const field = btn.dataset.field;
      const form  = $(field + "-edit-form");
      if (form) {
        form.hidden = !form.hidden;
        if (!form.hidden) {
          const inp = $(field + "-input");
          if (inp && _profile) {
            inp.value = field === "pix"
              ? _profile.pix_limit
              : _profile.credit_limit;
          }
          inp && inp.focus();
        }
      }
    });
  });

  // ── Cancel buttons ────────────────────────────────────────────────────────
  document.querySelectorAll(".cancel-limit-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const form = $(btn.dataset.field + "-edit-form");
      if (form) form.hidden = true;
      const errEl = $(btn.dataset.field + "-error");
      if (errEl) errEl.textContent = "";
    });
  });

  // ── Save buttons ──────────────────────────────────────────────────────────
  document.querySelectorAll(".save-limit-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const field  = btn.dataset.field;
      const inp    = $(field + "-input");
      const errEl  = $(field + "-error");
      errEl.textContent = "";

      const val = parseFloat(inp.value);
      if (isNaN(val) || val < 0) {
        errEl.textContent = "Informe um valor válido.";
        return;
      }

      const patch = field === "pix"
        ? { pix_limit: val }
        : { credit_limit: val };

      btn.disabled = true;
      btn.textContent = "Salvando…";
      try {
        const res = await apiFetch("/api/profile/", {
          method: "PATCH",
          body: JSON.stringify(patch),
        });
        if (!res) return;
        if (!res.ok) {
          const errs = res.data.errors || [res.data.error || "Erro ao salvar."];
          errEl.textContent = errs.join(" ");
          return;
        }
        _profile = res.data.profile;
        renderProfile();
        $(field + "-edit-form").hidden = true;
        toast("Limite atualizado com sucesso!", "success");
      } finally {
        btn.disabled = false;
        btn.textContent = "Salvar";
      }
    });
  });

  /* ══════════════════════════════════════════════════════════════════════════
     INVESTMENTS
  ══════════════════════════════════════════════════════════════════════════ */
  function renderInvestments() {
    const list    = $("invest-list");
    const empty   = $("invest-empty");
    const totalEl = $("invest-total");

    // Clear existing items (keep empty message node)
    Array.from(list.children)
      .filter((c) => c !== empty)
      .forEach((c) => c.remove());

    if (!_investments.length) {
      empty.hidden = false;
      totalEl.textContent = fmtBRL(0);
      return;
    }

    empty.hidden = true;
    let total = 0;

    for (const inv of _investments) {
      total += inv.balance;
      const item = document.createElement("div");
      item.className = "invest-item";
      item.dataset.id = inv.id;

      const left = document.createElement("div");
      left.className = "invest-item-left";

      const badge = document.createElement("span");
      badge.className = "invest-type-badge";
      badge.textContent = inv.type_label;

      const name = document.createElement("span");
      name.className = "invest-name";
      name.textContent = inv.name;

      left.append(badge, name);

      const right = document.createElement("div");
      right.style.cssText = "display:flex;align-items:center;gap:10px;";

      const bal = document.createElement("span");
      bal.className = "invest-balance";
      bal.textContent = fmtBRL(inv.balance);

      // Pending deposit badge
      if (inv.pending_deposit > 0) {
        const pend = document.createElement("span");
        pend.className = "invest-pending";
        pend.title = "Depósito pendente solicitado pelo agente";
        pend.textContent = "+ " + fmtBRL(inv.pending_deposit) + " pendente";
        right.append(pend);
      }

      const actions = document.createElement("div");
      actions.className = "invest-actions";

      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "invest-del-btn";
      delBtn.setAttribute("aria-label", "Remover " + inv.name);
      delBtn.title = "Remover investimento";
      delBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
        <path d="M10 11v6M14 11v6M9 6V4h6v2"/></svg>`;
      delBtn.addEventListener("click", () => deleteInvestment(inv.id));

      actions.append(delBtn);
      right.append(bal, actions);
      item.append(left, right);
      list.insertBefore(item, empty);
    }

    totalEl.textContent = fmtBRL(total);
  }

  // ── New investment form ───────────────────────────────────────────────────
  $("new-invest-btn").addEventListener("click", () => {
    const form = $("invest-add-form");
    form.hidden = !form.hidden;
    if (!form.hidden) {
      $("inv-name").value    = "";
      $("inv-balance").value = "";
      $("invest-add-error").textContent = "";
      $("inv-name").focus();
    }
  });

  $("invest-cancel-btn").addEventListener("click", () => {
    $("invest-add-form").hidden = true;
  });

  $("invest-save-btn").addEventListener("click", async () => {
    const name    = $("inv-name").value.trim();
    const type    = $("inv-type").value;
    const balance = parseFloat($("inv-balance").value) || 0;
    const errEl   = $("invest-add-error");
    errEl.textContent = "";

    if (!name) {
      errEl.textContent = "Informe o nome do investimento.";
      return;
    }
    if (balance < 0) {
      errEl.textContent = "Saldo não pode ser negativo.";
      return;
    }

    const btn = $("invest-save-btn");
    btn.disabled = true;
    btn.textContent = "Salvando…";
    try {
      const res = await apiFetch("/api/investments/", {
        method: "POST",
        body: JSON.stringify({ name, type, balance }),
      });
      if (!res) return;
      if (!res.ok) {
        errEl.textContent = res.data.error || "Erro ao salvar.";
        return;
      }
      _investments.push(res.data.investment);
      renderInvestments();
      $("invest-add-form").hidden = true;
      toast("Investimento adicionado!", "success");
    } finally {
      btn.disabled = false;
      btn.textContent = "Salvar investimento";
    }
  });

  // ── Delete investment ─────────────────────────────────────────────────────
  async function deleteInvestment(id) {
    if (!confirm("Remover este investimento da carteira?")) return;
    const res = await apiFetch("/api/investments/" + id + "/", { method: "DELETE" });
    if (!res) return;
    if (res.ok) {
      _investments = _investments.filter((i) => i.id !== id);
      renderInvestments();
      toast("Investimento removido.");
    } else {
      toast("Erro ao remover.", "error");
    }
  }

  /* ── Boot ────────────────────────────────────────────────────────────────── */
  boot();
})();
