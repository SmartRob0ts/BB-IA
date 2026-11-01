(() => {
  "use strict";

  const BACKEND_URL = "http://localhost:8000";
  const $ = (id) => document.getElementById(id);

  /* ── Toast ───────────────────────────────────────────────────────────────── */
  let _toastTimer;
  function toast(msg, type = "") {
    const el = $("toast");
    el.textContent = msg;
    el.className = "toast visible" + (type ? " " + type : "");
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(() => (el.className = "toast"), 3500);
  }

  /* ── Redirect if already logged in ──────────────────────────────────────── */
  if (localStorage.getItem("bbIA_token")) {
    window.location.replace("perfil.html");
  }

  /* ── Tab switching ───────────────────────────────────────────────────────── */
  const tabLogin    = $("tab-login");
  const tabRegister = $("tab-register");
  const panelLogin    = $("panel-login");
  const panelRegister = $("panel-register");

  function switchTab(which) {
    const isLogin = which === "login";
    tabLogin.classList.toggle("active", isLogin);
    tabRegister.classList.toggle("active", !isLogin);
    tabLogin.setAttribute("aria-selected", isLogin ? "true" : "false");
    tabRegister.setAttribute("aria-selected", isLogin ? "false" : "true");
    panelLogin.hidden    = !isLogin;
    panelRegister.hidden =  isLogin;
  }

  tabLogin.addEventListener("click",    () => switchTab("login"));
  tabRegister.addEventListener("click", () => switchTab("register"));

  // If ?mode=register in URL, open register tab directly
  if (new URLSearchParams(location.search).get("mode") === "register") {
    switchTab("register");
  }

  /* ── Password visibility toggle ──────────────────────────────────────────── */
  document.querySelectorAll(".pw-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const inp = $(btn.dataset.target);
      inp.type = inp.type === "password" ? "text" : "password";
      btn.setAttribute("aria-label", inp.type === "password" ? "Mostrar senha" : "Ocultar senha");
    });
  });

  /* ── Mobile menu ─────────────────────────────────────────────────────────── */
  $("menu-btn").addEventListener("click", () => {
    const m = $("mobile-menu");
    const o = m.classList.toggle("open");
    $("menu-btn").setAttribute("aria-expanded", String(o));
  });

  /* ── API helpers ─────────────────────────────────────────────────────────── */
  async function apiPost(path, body) {
    const res = await fetch(BACKEND_URL + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return { ok: res.ok, status: res.status, data: await res.json() };
  }

  function setLoading(btn, loading) {
    btn.disabled = loading;
    btn.textContent = loading
      ? (btn.id === "login-btn" ? "Entrando…" : "Criando conta…")
      : (btn.id === "login-btn" ? "Entrar na conta" : "Criar minha conta");
  }

  /* ── Login ────────────────────────────────────────────────────────────────── */
  $("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email    = $("login-email").value.trim();
    const password = $("login-password").value;
    const errEl    = $("login-error");
    const btn      = $("login-btn");
    errEl.textContent = "";

    if (!email || !password) {
      errEl.textContent = "Preencha e-mail e senha.";
      return;
    }

    setLoading(btn, true);
    try {
      const { ok, data } = await apiPost("/api/auth/login/", { email, password });
      if (!ok) {
        errEl.textContent = data.error || "Erro ao entrar.";
        return;
      }
      localStorage.setItem("bbIA_token", data.token);
      localStorage.setItem("bbIA_user",  JSON.stringify(data.user));
      toast("Login realizado! Redirecionando…", "success");
      setTimeout(() => window.location.replace("perfil.html"), 600);
    } catch {
      errEl.textContent = "Erro de conexão com o servidor.";
    } finally {
      setLoading(btn, false);
    }
  });

  /* ── Register ─────────────────────────────────────────────────────────────── */
  $("register-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name     = $("reg-name").value.trim();
    const email    = $("reg-email").value.trim();
    const password = $("reg-password").value;
    const confirm  = $("reg-confirm").value;
    const errEl    = $("register-error");
    const btn      = $("register-btn");
    errEl.textContent = "";

    if (!name || !email || !password || !confirm) {
      errEl.textContent = "Preencha todos os campos.";
      return;
    }
    if (password.length < 6) {
      errEl.textContent = "A senha deve ter pelo menos 6 caracteres.";
      return;
    }
    if (password !== confirm) {
      errEl.textContent = "As senhas não coincidem.";
      return;
    }

    setLoading(btn, true);
    try {
      const { ok, data } = await apiPost("/api/auth/register/", { name, email, password });
      if (!ok) {
        errEl.textContent = data.error || "Erro ao criar conta.";
        return;
      }
      localStorage.setItem("bbIA_token", data.token);
      localStorage.setItem("bbIA_user",  JSON.stringify(data.user));
      toast("Conta criada! Redirecionando…", "success");
      setTimeout(() => window.location.replace("perfil.html"), 600);
    } catch {
      errEl.textContent = "Erro de conexão com o servidor.";
    } finally {
      setLoading(btn, false);
    }
  });
})();
