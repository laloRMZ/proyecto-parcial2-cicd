const healthBadge = document.getElementById("health-badge");
const logoutBtn = document.getElementById("logout-btn");
const loginSection = document.getElementById("login-section");
const appSection = document.getElementById("app-section");
const loginForm = document.getElementById("login-form");
const loginFeedback = document.getElementById("login-feedback");
const userForm = document.getElementById("user-form");
const usersList = document.getElementById("users-list");
const usersCount = document.getElementById("users-count");
const feedback = document.getElementById("feedback");
const simulateErrorBtn = document.getElementById("simulate-error-btn");
const cancelEditBtn = document.getElementById("cancel-edit-btn");
const editUserIdInput = document.getElementById("edit-user-id");
const usernameInput = document.getElementById("username");
const emailInput = document.getElementById("email");
const fullNameInput = document.getElementById("full_name");
const roleSelect = document.getElementById("role");
const passwordInput = document.getElementById("password");
const passwordHint = document.getElementById("password-hint");
const formTitle = document.getElementById("form-title");
const submitUserBtn = document.getElementById("submit-user-btn");
const currentUserLabel = document.getElementById("current-user-label");

const TOKEN_KEY = "proyecto2_token";
let currentUser = null;

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  currentUser = null;
}

function setFeedback(el, message, isError = false) {
  el.textContent = message;
  el.classList.toggle("error", isError);
}

function resetUserForm() {
  userForm.reset();
  editUserIdInput.value = "";
  usernameInput.disabled = false;
  passwordInput.required = true;
  passwordHint.textContent = "(mínimo 6 caracteres)";
  formTitle.textContent = "Crear Usuario";
  submitUserBtn.textContent = "Guardar Usuario";
  cancelEditBtn.classList.add("hidden");
}

async function apiFetch(url, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return fetch(url, { ...options, headers });
}

async function checkHealth() {
  try {
    const res = await fetch("/health");
    if (!res.ok) throw new Error("Healthcheck failed");
    const data = await res.json();
    healthBadge.textContent = `Estado: ${data.status.toUpperCase()}`;
    healthBadge.classList.add("ok");
    healthBadge.classList.remove("error");
  } catch {
    healthBadge.textContent = "Estado: ERROR";
    healthBadge.classList.add("error");
    healthBadge.classList.remove("ok");
  }
}

function showLoggedOutView() {
  loginSection.classList.remove("hidden");
  appSection.classList.add("hidden");
  logoutBtn.classList.add("hidden");
  resetUserForm();
}

function showLoggedInView() {
  loginSection.classList.add("hidden");
  appSection.classList.remove("hidden");
  logoutBtn.classList.remove("hidden");
  currentUserLabel.textContent = currentUser ? `Sesión: ${currentUser.username} (${currentUser.role})` : "";
}

async function loadUsers() {
  const res = await apiFetch("/api/users");
  if (res.status === 401) {
    clearSession();
    showLoggedOutView();
    return;
  }
  const data = await res.json();
  const users = data.users || [];
  usersCount.textContent = `${users.length} usuario${users.length === 1 ? "" : "s"}`;
  usersList.innerHTML = "";

  for (const user of users) {
    const li = document.createElement("li");
    li.className = "item-row";
    li.dataset.testid = `user-row-${user.username}`;

    const info = document.createElement("div");
    const title = document.createElement("div");
    title.className = "item-title";
    title.textContent = `${user.full_name} (@${user.username})`;

    const meta = document.createElement("div");
    meta.className = "item-meta";
    meta.textContent = `${user.email} · rol: ${user.role} · ${user.is_active ? "activo" : "inactivo"}`;

    info.appendChild(title);
    info.appendChild(meta);

    const btnGroup = document.createElement("div");
    btnGroup.className = "actions";

    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "edit-btn";
    editBtn.textContent = "Editar";
    editBtn.dataset.testid = `edit-btn-${user.username}`;
    editBtn.addEventListener("click", () => {
      editUserIdInput.value = String(user.id);
      usernameInput.value = user.username;
      usernameInput.disabled = true;
      emailInput.value = user.email;
      fullNameInput.value = user.full_name;
      roleSelect.value = user.role;
      passwordInput.value = "";
      passwordInput.required = false;
      passwordHint.textContent = "(opcional al editar)";
      formTitle.textContent = `Editar Usuario: ${user.username}`;
      submitUserBtn.textContent = "Actualizar Usuario";
      cancelEditBtn.classList.remove("hidden");
      setFeedback(feedback, "");
    });

    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "delete-btn";
    delBtn.textContent = "Eliminar";
    delBtn.dataset.testid = `delete-btn-${user.username}`;
    delBtn.disabled = currentUser && currentUser.id === user.id;
    delBtn.addEventListener("click", async () => {
      const delRes = await apiFetch(`/api/users/${user.id}`, { method: "DELETE" });
      if (delRes.ok) {
        setFeedback(feedback, "Usuario eliminado");
        await loadUsers();
      } else {
        const err = await delRes.json().catch(() => ({}));
        setFeedback(feedback, err.detail || "Error al eliminar usuario", true);
      }
    });

    btnGroup.appendChild(editBtn);
    btnGroup.appendChild(delBtn);
    li.appendChild(info);
    li.appendChild(btnGroup);
    usersList.appendChild(li);
  }
}

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value;

  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (res.ok) {
    const data = await res.json();
    setToken(data.access_token);
    currentUser = data.user;
    loginForm.reset();
    setFeedback(loginFeedback, "");
    resetUserForm();
    showLoggedInView();
    await loadUsers();
  } else {
    const err = await res.json().catch(() => ({}));
    setFeedback(loginFeedback, err.detail || "Credenciales inválidas", true);
  }
});

logoutBtn.addEventListener("click", () => {
  clearSession();
  showLoggedOutView();
  setFeedback(loginFeedback, "Sesión cerrada");
});

cancelEditBtn.addEventListener("click", () => {
  resetUserForm();
  setFeedback(feedback, "");
});

userForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const editId = editUserIdInput.value;
  const email = emailInput.value.trim();
  const full_name = fullNameInput.value.trim();
  const role = roleSelect.value;
  const password = passwordInput.value;

  if (editId) {
    const payload = { email, full_name, role };
    if (password) payload.password = password;
    const res = await apiFetch(`/api/users/${editId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      resetUserForm();
      setFeedback(feedback, "Usuario actualizado correctamente");
      await loadUsers();
    } else {
      const err = await res.json().catch(() => ({}));
      setFeedback(feedback, err.detail || "Error al actualizar usuario", true);
    }
  } else {
    const username = usernameInput.value.trim();
    if (!password || password.length < 6) {
      setFeedback(feedback, "La contraseña debe tener al menos 6 caracteres", true);
      return;
    }
    const res = await apiFetch("/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, full_name, role, password }),
    });
    if (res.ok) {
      resetUserForm();
      setFeedback(feedback, "Usuario creado correctamente");
      await loadUsers();
    } else {
      const err = await res.json().catch(() => ({}));
      setFeedback(feedback, err.detail || "Error al crear usuario", true);
    }
  }
});

simulateErrorBtn.addEventListener("click", async () => {
  const res = await fetch("/api/simulate-error");
  if (!res.ok) {
    setFeedback(feedback, `Error simulado HTTP ${res.status}`, true);
  }
});

async function bootstrap() {
  await checkHealth();
  const token = getToken();
  if (!token) {
    showLoggedOutView();
    return;
  }
  const meRes = await apiFetch("/api/auth/me");
  if (meRes.ok) {
    const data = await meRes.json();
    currentUser = data.user;
    resetUserForm();
    showLoggedInView();
    await loadUsers();
  } else {
    clearSession();
    showLoggedOutView();
  }
}

bootstrap();
