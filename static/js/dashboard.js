let allTasks = [];
let activeFilter = "all";
let currentUserId = null;

document.addEventListener("DOMContentLoaded", () => {
  fetchCurrentUser();
  fetchTasks();
  fetchAnalytics();
  setupEventListeners();
  setupWebSocket();
});

async function fetchCurrentUser() {
  const res = await fetch("/api/tasks");
  if (res.status === 401) { window.location.href = "/login"; }
}

function setupWebSocket() {
  const socket = io({ transports: ["polling", "websocket"] });

  socket.on("connect", () => {
    console.log("Socket connected:", socket.id);
    document.getElementById("live-badge").style.color = "#16a34a";
  });

  socket.on("disconnect", () => {
    document.getElementById("live-badge").style.color = "#9ca3af";
  });

  socket.on("new_task", (task) => {
    console.log("New task received via socket:", task);
    if (!allTasks.find(t => t.id === task.id)) {
      allTasks.unshift(task);
      renderTasks();
      fetchAnalytics();
    }
  });

  socket.on("task_changed", (updated) => {
    console.log("Task updated via socket:", updated);
    allTasks = allTasks.map(t => t.id === updated.id ? updated : t);
    renderTasks();
    fetchAnalytics();
  });

  socket.on("task_removed", ({ id }) => {
    console.log("Task removed via socket:", id);
    allTasks = allTasks.filter(t => t.id !== id);
    renderTasks();
    fetchAnalytics();
  });
}

async function fetchTasks() {
  try {
    const res = await fetch("/api/tasks");
    if (res.status === 401) { window.location.href = "/login"; return; }
    allTasks = await res.json();
    renderTasks();
  } catch(e) { console.error("fetchTasks error:", e); }
}

async function fetchAnalytics() {
  try {
    const res = await fetch("/api/analytics");
    if (!res.ok) return;
    const d = await res.json();
    document.getElementById("stat-total").textContent = d.total;
    document.getElementById("stat-done").textContent = d.completed;
    document.getElementById("stat-pending").textContent = d.pending;
    document.getElementById("stat-pct").textContent = d.completion_pct + "%";
    document.getElementById("progress-fill").style.width = d.completion_pct + "%";
  } catch(e) { console.error("fetchAnalytics error:", e); }
}

function renderTasks() {
  const c = document.getElementById("task-list");
  const list = activeFilter === "all" ? allTasks : allTasks.filter(t => t.status === activeFilter);
  if (!list.length) {
    c.innerHTML = '<div class="empty-state"><div class="icon">📭</div><p>No tasks yet. Add one!</p></div>';
    return;
  }
  c.innerHTML = list.map(t => {
    const done = t.status === "completed";
    const d = new Date(t.created_at).toLocaleDateString("en-IN", {day:"numeric",month:"short",year:"numeric"});
    const title = t.title.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
    const desc  = (t.description||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
    return `<div class="task-card">
      <button class="check-btn ${done?"is-done":""}" onclick="toggleComplete(${t.id},'${t.status}')"></button>
      <div class="task-body">
        <p class="task-title ${done?"strikethrough":""}">${title}</p>
        ${desc ? `<p class="task-desc">${desc}</p>` : ""}
        <div class="task-meta">
          <span class="badge ${t.priority}">${t.priority}</span>
          <span class="badge ${t.status}">${t.status.replace("_"," ")}</span>
          <span class="task-date">${d}</span>
        </div>
      </div>
      <div class="task-actions">
        <button class="action-btn" onclick="openEditModal(${t.id})">✏️</button>
        <button class="action-btn" onclick="removeTask(${t.id})">🗑️</button>
      </div>
    </div>`;
  }).join("");
}

async function addTask() {
  const title    = document.getElementById("task-title").value.trim();
  const desc     = document.getElementById("task-desc").value.trim();
  const priority = document.getElementById("task-priority").value;
  const status   = document.getElementById("task-status").value;

  if (!title) { showFormMsg("Title is required","error"); return; }

  const btn = document.getElementById("add-btn");
  btn.textContent = "Adding...";
  btn.disabled = true;

  try {
    const res = await fetch("/api/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description: desc, priority, status })
    });

    const data = await res.json();
    console.log("Add task response:", res.status, data);

    if (res.status === 401) { window.location.href = "/login"; return; }

    if (res.ok) {
      if (!allTasks.find(t => t.id === data.id)) {
        allTasks.unshift(data);
      }
      renderTasks();
      fetchAnalytics();
      document.getElementById("task-title").value = "";
      document.getElementById("task-desc").value  = "";
      showFormMsg("Task added!","success");
      setTimeout(() => {
        document.getElementById("form-msg").className = "form-msg hidden";
      }, 2000);
    } else {
      showFormMsg(data.error || "Failed to add task","error");
    }
  } catch(e) {
    console.error("addTask error:", e);
    showFormMsg("Network error — try again","error");
  } finally {
    btn.textContent = "+ Add Task";
    btn.disabled = false;
  }
}

async function toggleComplete(id, currentStatus) {
  const newStatus = currentStatus === "completed" ? "pending" : "completed";
  try {
    const res = await fetch(`/api/tasks/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    if (res.ok) {
      const updated = await res.json();
      allTasks = allTasks.map(t => t.id === id ? updated : t);
      renderTasks();
      fetchAnalytics();
    }
  } catch(e) { console.error(e); }
}

function openEditModal(id) {
  const task = allTasks.find(t => t.id === id);
  if (!task) return;
  document.getElementById("edit-id").value       = task.id;
  document.getElementById("edit-title").value    = task.title;
  document.getElementById("edit-desc").value     = task.description || "";
  document.getElementById("edit-priority").value = task.priority;
  document.getElementById("edit-status").value   = task.status;
  document.getElementById("edit-modal").classList.remove("hidden");
}

async function saveEdit() {
  const id       = document.getElementById("edit-id").value;
  const title    = document.getElementById("edit-title").value.trim();
  const desc     = document.getElementById("edit-desc").value.trim();
  const priority = document.getElementById("edit-priority").value;
  const status   = document.getElementById("edit-status").value;
  if (!title) { alert("Title is required"); return; }
  try {
    const res  = await fetch(`/api/tasks/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description: desc, priority, status })
    });
    const data = await res.json();
    if (res.ok) {
      allTasks = allTasks.map(t => t.id === parseInt(id) ? data : t);
      renderTasks();
      fetchAnalytics();
      closeEditModal();
    } else {
      alert(data.error || "Update failed");
    }
  } catch(e) { alert("Network error"); }
}

function closeEditModal() {
  document.getElementById("edit-modal").classList.add("hidden");
}

async function removeTask(id) {
  if (!confirm("Delete this task?")) return;
  try {
    const res = await fetch(`/api/tasks/${id}`, { method: "DELETE" });
    if (res.ok) {
      allTasks = allTasks.filter(t => t.id !== id);
      renderTasks();
      fetchAnalytics();
    }
  } catch(e) { console.error(e); }
}

function setupEventListeners() {
  document.getElementById("add-btn").addEventListener("click", addTask);
  document.getElementById("save-edit").addEventListener("click", saveEdit);
  document.getElementById("cancel-edit").addEventListener("click", closeEditModal);
  document.getElementById("logout-btn").addEventListener("click", async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  });
  document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeFilter = btn.dataset.f;
      renderTasks();
    });
  });
  document.getElementById("edit-modal").addEventListener("click", function(e) {
    if (e.target === this) closeEditModal();
  });
}

function showFormMsg(msg, type) {
  const el = document.getElementById("form-msg");
  el.textContent = msg;
  el.className = `form-msg ${type}`;
}
