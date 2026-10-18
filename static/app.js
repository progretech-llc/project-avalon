import { mountCore } from "./core.js";
const $ = (id) => document.getElementById(id);
let csrf = "",
  authorized = false,
  busy = false,
  models = [],
  platforms = [],
  lastSession = null;
let state = {
  revision: -1,
  status: "disconnected",
  active_turn: null,
  session: null,
  messages: [],
  sessions: [],
  events: [],
};
let setCore = () => {};
try {
  setCore = mountCore($("presence-canvas"));
} catch {
  /* Status text remains available without GPU preview. */
}
const labels = {
  disconnected: "Disconnected",
  idle: "Connected",
  working: "Working",
  writing: "Writing",
  executing: "Executing",
  completed: "Completed",
  failed: "Needs attention",
  cancelled: "Stopped",
  switching: "Switching",
};
const headings = {
  disconnected: "Ready when you are.",
  idle: "Here. And ready.",
  working: "Following the thought.",
  writing: "Making a change.",
  executing: "Putting it to work.",
  completed: "A thought, delivered.",
  failed: "Something needs attention.",
  cancelled: "A moment of quiet.",
  switching: "Changing the connection.",
};
function notice(text, kind = "error") {
  const element = $("notice");
  element.hidden = !text;
  element.dataset.kind = kind;
  element.textContent = text;
}
async function api(path, data) {
  const options = { headers: {} };
  if (data !== undefined) {
    options.method = "POST";
    options.headers = {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrf,
    };
    options.body = JSON.stringify(data);
  }
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok)
    throw Error(
      result.error || "The local service could not complete this request.",
    );
  return result;
}
function page(name) {
  for (const view of document.querySelectorAll("[data-view]"))
    view.hidden = view.dataset.view !== name;
  for (const button of document.querySelectorAll("[data-page]")) {
    const active = button.dataset.page === name;
    button.classList.toggle("selected", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  }
  $("page-title").textContent = {
    presence: "Presence",
    sessions: "Sessions",
    permissions: "Permissions",
  }[name];
}
function controls() {
  const target = platforms.find((p) => p.id === $("platform").value);
  $("connect").disabled =
    !authorized || busy || !target?.available || !$("model").value;
  $("connect").textContent =
    state.status === "disconnected" ||
    state.status === "cancelled" ||
    state.status === "failed"
      ? "Connect"
      : "Switch model";
  $("disconnect").disabled =
    !authorized || busy || ["disconnected", "cancelled"].includes(state.status);
  $("send").disabled =
    !authorized ||
    busy ||
    !!state.active_turn ||
    !state.session ||
    ["disconnected", "cancelled", "failed", "switching"].includes(state.status);
  $("stop").disabled = !authorized || busy || !state.active_turn;
  $("save-permissions").disabled = !authorized || busy || !state.session;
  $("status-commands").disabled = $("permission-mode").value === "chat";
  if ($("status-commands").disabled) $("status-commands").checked = false;
  $("refresh-models").disabled = busy || !authorized;
  $("wallpaper-mode").disabled = !authorized || busy;
  $("new-session").disabled =
    !authorized || busy || !$("model").value || !target?.available;
}
function updateModelNote() {
  const model = models.find((m) => m.name === $("model").value);
  $("model-note").textContent = model
    ? `${(model.size / 1024 ** 3).toFixed(1)} GB installed · ${model.tools ? "Tool support" : "Conversation only"}${model.vision ? " · Vision capable" : ""}`
    : "No compatible model is installed. Nothing will be downloaded automatically.";
  controls();
}
function targetChanged() {
  const target = platforms.find((p) => p.id === $("platform").value);
  $("platform-note").textContent =
    target?.reason || "Local Ollama models installed on this computer.";
  $("model").disabled = !target?.available;
  controls();
}
function renderMessages(messages) {
  const container = $("messages");
  const nearBottom =
    container.scrollHeight - container.scrollTop - container.clientHeight < 100;
  if (!messages.length) {
    if (!container.querySelector(".empty-chat")) {
      container.replaceChildren();
      const empty = document.createElement("div");
      empty.className = "empty-chat";
      const h = document.createElement("h3");
      h.textContent = "Make room for a thought.";
      const p = document.createElement("p");
      p.textContent =
        "Connect a local model, then start a conversation. Your selected model gives this presence its voice in chat.";
      empty.append(h, p);
      container.append(empty);
    }
    return;
  }
  container.querySelector(".empty-chat")?.remove();
  const wanted = new Set(messages.map((m) => String(m.id)));
  for (const child of [...container.children])
    if (!wanted.has(child.dataset.id)) child.remove();
  for (const message of messages) {
    let article = container.querySelector(`[data-id="${message.id}"]`);
    if (!article) {
      article = document.createElement("article");
      article.className = "message";
      article.dataset.id = message.id;
      article.dataset.role = message.role;
      const header = document.createElement("header");
      header.append(
        document.createTextNode(
          message.role === "user" ? "You" : "Avalon · OpenCode",
        ),
        document.createElement("span"),
      );
      article.append(header, document.createElement("p"));
      container.append(article);
    }
    article.dataset.status = message.status;
    article.querySelector("header span").textContent =
      message.status === "complete"
        ? ""
        : {
            streaming: "Responding",
            cancelled: "Cancelled",
            interrupted: "Interrupted",
            failed: "Incomplete",
          }[message.status] || message.status;
    const text = article.querySelector("p");
    if (text.textContent !== message.text) text.textContent = message.text;
  }
  if (nearBottom) container.scrollTop = container.scrollHeight;
}
function renderSessions() {
  const container = $("session-list");
  container.replaceChildren();
  if (!state.sessions.length) {
    const p = document.createElement("p");
    p.textContent = "Connect a model to create your first conversation.";
    container.append(p);
    return;
  }
  for (const session of state.sessions) {
    const row = document.createElement("div");
    row.className = "session-row";
    const info = document.createElement("div");
    const title = document.createElement("h3");
    title.textContent = session.title;
    const detail = document.createElement("p");
    detail.textContent = `OpenCode / ${session.model} · ${new Date(session.created * 1000).toLocaleDateString()}`;
    info.append(title, detail);
    row.append(info);
    if (session.id === state.session?.id) {
      const badge = document.createElement("span");
      badge.className = "current-tag";
      badge.textContent = "Current";
      row.append(badge);
    } else {
      const button = document.createElement("button");
      button.textContent = "Resume";
      button.addEventListener("click", () =>
        action(async () => {
          apply(
            await api("/api/select", {
              session_id: session.id,
              cancel_current: true,
            }),
            true,
          );
          page("presence");
        }),
      );
      row.append(button);
    }
    container.append(row);
  }
}
function renderEvents() {
  const list = $("activity-list");
  list.replaceChildren();
  for (const event of state.events.slice(0, 12)) {
    const row = document.createElement("li");
    const label = document.createElement("span");
    label.textContent = event.label;
    const time = document.createElement("time");
    time.dateTime = new Date(event.created * 1000).toISOString();
    time.textContent = new Date(event.created * 1000).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
    row.append(label, time);
    list.append(row);
  }
}
function apply(data, force = false) {
  state = { ...state, ...data };
  if (data.csrf) csrf = data.csrf;
  document.body.dataset.status = state.status;
  setCore(state.status);
  $("connection-label").textContent = labels[state.status] || "Unknown";
  $("body-state").textContent =
    headings[state.status] || "Check the connection.";
  $("body-detail").textContent = state.detail;
  $("session-title").textContent = state.session?.title || "A new conversation";
  $("active-model").textContent = state.session
    ? `OpenCode / ${state.session.model}`
    : "No model connected";
  $("footer-target").textContent = state.session
    ? `OpenCode / ${state.session.model}`
    : "OpenCode + Ollama";
  $("turn-status").textContent = state.active_turn
    ? state.detail
    : "No active turn";
  if (data.wallpaper) $("wallpaper-mode").value = data.wallpaper.mode;
  if (force || lastSession !== state.session?.id) {
    lastSession = state.session?.id;
    if (state.session) {
      if (models.some((m) => m.name === state.session.model))
        $("model").value = state.session.model;
      $("platform").value = "opencode";
      $("permission-mode").value = state.session.mode;
      $("permission-title").value = state.session.title;
      $("status-commands").checked = !!state.session.commands;
      $("workspace-path").textContent = "Workspace: " + state.session.workspace;
    }
    updateModelNote();
    targetChanged();
  }
  if (data.messages) renderMessages(data.messages);
  if (data.sessions) renderSessions();
  if (data.events) renderEvents();
  controls();
}
async function action(callback) {
  if (busy) return;
  busy = true;
  controls();
  notice("");
  try {
    await callback();
  } catch (error) {
    notice(error.message);
  } finally {
    busy = false;
    controls();
  }
}
async function refreshModels(refresh = false) {
  const data = await api("/api/models" + (refresh ? "?refresh=1" : ""));
  models = data.models;
  platforms = data.platforms;
  const preferred =
    $("model").value ||
    state.session?.model ||
    models.find(
      (m) =>
        m.tools &&
        m.name.includes("coder") &&
        !m.name.startsWith("experiment-"),
    )?.name ||
    models.find((m) => m.tools)?.name ||
    models[0]?.name;
  $("platform").replaceChildren(
    ...platforms.map((p) => {
      const o = document.createElement("option");
      o.value = p.id;
      o.textContent = p.name + (p.available ? "" : " — connection blocked");
      return o;
    }),
  );
  $("model").replaceChildren(
    ...models.map((m) => {
      const o = document.createElement("option");
      o.value = m.name;
      o.textContent = m.name;
      return o;
    }),
  );
  if (!models.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No installed completion models";
    $("model").append(option);
  } else $("model").value = preferred;
  updateModelNote();
  targetChanged();
}
async function poll() {
  if (authorized) {
    try {
      apply(await api("/api/state?revision=" + state.revision));
      $("access-note").hidden = true;
    } catch (error) {
      notice(error.message);
    }
  }
  setTimeout(poll, 700);
}
for (const button of document.querySelectorAll("[data-page]"))
  button.addEventListener("click", () => page(button.dataset.page));
$("platform").addEventListener("change", targetChanged);
$("model").addEventListener("change", updateModelNote);
$("permission-mode").addEventListener("change", controls);
$("refresh-models").addEventListener("click", () =>
  action(() => refreshModels(true)),
);
$("connect").addEventListener("click", () =>
  action(async () => {
    const same = state.session?.model === $("model").value;
    const data = same
      ? {
          session_id: state.session.id,
          platform: $("platform").value,
          cancel_current: true,
        }
      : {
          platform: $("platform").value,
          model: $("model").value,
          cancel_current: true,
        };
    apply(await api("/api/select", data), true);
  }),
);
$("disconnect").addEventListener("click", () =>
  action(async () => apply(await api("/api/disconnect", {}))),
);
$("stop").addEventListener("click", () =>
  action(async () => apply(await api("/api/stop", {}))),
);
$("wallpaper-mode").addEventListener("change", () =>
  action(async () => {
    const result = await api("/api/wallpaper", {
      mode: $("wallpaper-mode").value,
    });
    $("wallpaper-mode").value = result.wallpaper.mode;
    if (result.wallpaper.mode !== result.requested)
      notice(
        "GNOME is applying the wallpaper change. If it does not appear, log out/in to load the installed extension.",
      );
  }),
);
$("chat-form").addEventListener("submit", (event) => {
  event.preventDefault();
  if ($("send").disabled || !$("message").value.trim()) return;
  const text = $("message").value;
  action(async () => {
    await api("/api/chat", { text });
    $("message").value = "";
    apply(await api("/api/state"));
  });
});
$("message").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    $("chat-form").requestSubmit();
  }
});
$("new-session").addEventListener("click", () => {
  $("new-session-form").hidden = false;
  $("new-title").focus();
});
$("cancel-new").addEventListener("click", () => {
  $("new-session-form").hidden = true;
});
$("new-session-form").addEventListener("submit", (event) => {
  event.preventDefault();
  action(async () => {
    apply(
      await api("/api/select", {
        model: $("model").value,
        title: $("new-title").value,
        workspace: $("new-workspace").value || null,
        cancel_current: true,
      }),
      true,
    );
    $("new-session-form").hidden = true;
  });
});
$("permission-form").addEventListener("submit", (event) => {
  event.preventDefault();
  if (!state.session) return;
  action(async () => {
    apply(
      await api("/api/select", {
        session_id: state.session.id,
        title: $("permission-title").value,
        mode: $("permission-mode").value,
        commands: $("status-commands").checked,
        cancel_current: true,
      }),
      true,
    );
    notice(
      "Workspace access applied. The connection has restarted.",
      "success",
    );
  });
});
async function initialize() {
  const fragment = new URLSearchParams(location.hash.slice(1)),
    entry = fragment.get("entry");
  if (entry) {
    history.replaceState(null, "", location.pathname);
    try {
      csrf = (await api("/api/auth", { token: entry })).csrf;
    } catch (error) {
      notice(error.message);
    }
  }
  try {
    const data = await api("/api/state");
    authorized = true;
    apply(data);
    await refreshModels();
    apply(data, true);
    $("access-note").hidden = true;
  } catch (error) {
    $("access-note").textContent = error.message;
  }
  controls();
  poll();
  if ("serviceWorker" in navigator) {
    try {
      await navigator.serviceWorker.register("/sw.js");
    } catch {
      $("access-note").hidden = false;
      $("access-note").textContent =
        "Offline support is unavailable. The connected control center still works.";
    }
  }
}
initialize();
