const healthBadge = document.getElementById("health-badge");
const itemForm = document.getElementById("item-form");
const itemsList = document.getElementById("items-list");
const itemsCount = document.getElementById("items-count");
const feedback = document.getElementById("feedback");
const simulateErrorBtn = document.getElementById("simulate-error-btn");

function setFeedback(message, isError = false) {
  feedback.textContent = message;
  feedback.classList.toggle("error", isError);
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

async function loadItems() {
  const res = await fetch("/api/items");
  const data = await res.json();
  const items = data.items || [];
  itemsCount.textContent = `${items.length} elemento${items.length === 1 ? "" : "s"}`;
  itemsList.innerHTML = "";

  for (const item of items) {
    const li = document.createElement("li");
    li.className = "item-row";
    li.dataset.testid = `item-row-${item.id}`;

    const info = document.createElement("div");
    const title = document.createElement("div");
    title.className = "item-title";
    title.textContent = item.title;

    const meta = document.createElement("div");
    meta.className = "item-meta";
    meta.textContent = `${item.status}${item.description ? " · " + item.description : ""}`;

    info.appendChild(title);
    info.appendChild(meta);

    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "delete-btn";
    delBtn.textContent = "Eliminar";
    delBtn.dataset.testid = `delete-btn-${item.id}`;
    delBtn.addEventListener("click", async () => {
      const delRes = await fetch(`/api/items/${item.id}`, { method: "DELETE" });
      if (delRes.ok) {
        setFeedback("Elemento eliminado");
        await loadItems();
      } else {
        setFeedback("Error al eliminar elemento", true);
      }
    });

    li.appendChild(info);
    li.appendChild(delBtn);
    itemsList.appendChild(li);
  }
}

itemForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = document.getElementById("title").value.trim();
  const description = document.getElementById("description").value.trim();
  const status = document.getElementById("status").value;

  if (!title) {
    setFeedback("El título es obligatorio", true);
    return;
  }

  const res = await fetch("/api/items", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, description, status }),
  });

  if (res.ok) {
    itemForm.reset();
    setFeedback("Elemento creado correctamente");
    await loadItems();
  } else {
    setFeedback("Error al crear el elemento", true);
  }
});

simulateErrorBtn.addEventListener("click", async () => {
  const res = await fetch("/api/simulate-error");
  if (!res.ok) {
    setFeedback(`Error simulado HTTP ${res.status}`, true);
  }
});

checkHealth();
loadItems();
