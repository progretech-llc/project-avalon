import { mountCore } from "./core.js?v=4.2";
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
  showAvatarFallback();
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
  listening: "Listening",
  speaking: "Speaking",
  approval: "Awaiting approval",
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
  listening: "I’m listening.",
  speaking: "A voice for the thought.",
  approval: "Your decision comes first.",
};
function showAvatarFallback() {
  $("presence-canvas").hidden = true;
  $("avatar-fallback").hidden = false;
  notice(
    "GPU preview unavailable. Showing a still avatar; chat and connection controls still work.",
  );
}
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
    appearance: "Appearance",
    devices: "Devices",
    permissions: "Permissions",
  }[name];
}
function controls() {
  for (const button of document.querySelectorAll("[data-avatar]"))
    button.disabled = !authorized || busy;
  $("save-appearance").disabled = !authorized || busy;
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
  $("stop-all").disabled = !authorized || busy;
  $("approve-action").disabled = !authorized || busy || !!state.devices?.locked;
  $("deny-action").disabled = !authorized || busy;
  const d = state.devices;
  const hasCapture = d?.recording || d?.transcribing || d?.recording_ready;
  $("record").disabled =
    !authorized ||
    busy ||
    !d?.speech_ready ||
    d.locked ||
    !!state.active_turn ||
    hasCapture ||
    !state.session ||
    ["disconnected", "cancelled", "failed", "switching"].includes(
      state.runtime_status || state.status,
    );
  $("send-recording").hidden = !hasCapture;
  $("send-recording").disabled =
    !authorized || busy || d?.locked || d?.transcribing;
  $("mute").disabled =
    !authorized || busy || !(hasCapture || d?.speaking || d?.audio_busy || d?.awake);
  $("read-reply").disabled =
    !authorized ||
    busy ||
    !d?.speech_ready ||
    d.locked ||
    !!state.active_turn ||
    hasCapture ||
    !state.messages.some(
      (m) => m.role === "assistant" && m.status === "complete",
    );
  $("camera-on").disabled =
    !authorized ||
    busy ||
    d?.locked ||
    !!d?.camera ||
    d?.camera_starting ||
    !d?.settings.camera;
  $("camera-off").disabled =
    !authorized || busy || !(d?.camera || d?.camera_starting);
  const selected = models.find((m) => m.name === state.session?.model);
  $("ask-view").disabled =
    !authorized ||
    busy ||
    d?.locked ||
    !d?.camera ||
    !selected?.vision ||
    !!state.active_turn;
  $("vision-capability").textContent = selected?.vision
    ? "Your selected model supports images. Ask about this view sends one camera frame to that same model."
    : "Your selected model does not support images. Camera gaze still works. Select an installed vision model to ask about the view.";
  for (const id of ["save-devices", "refresh-devices", "save-desktop-actions"])
    $(id).disabled = !authorized || busy;
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
  if (data.appearance) {
    const a = data.appearance;
    $("avatar-fallback").src = "/static/avatars/" + a.avatar + ".png";
    $("avatar-fallback").alt = a.avatar + " still avatar";
    for (const button of document.querySelectorAll("[data-avatar]"))
      button.setAttribute(
        "aria-pressed",
        String(button.dataset.avatar === a.avatar),
      );
    if (!document.querySelector("#appearance-form:focus-within")) {
      $("render-quality").value = a.quality;
      $("render-fps").value = String(a.fps);
      $("render-motion").value = a.motion;
      $("idle-saver").checked = a.idle_saver !== false;
    }
  }
  document.body.dataset.status = state.status;
  setCore(state.status, state.appearance, state.sensors);
  renderMedia();
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
  $("approval-panel").hidden = !state.pending_action;
  $("approval-path").textContent = state.pending_action?.path || "";
  if (!document.querySelector("#desktop-action-form:focus-within"))
    $("allow-workspace-open").checked = !!state.desktop_actions;
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
  setTimeout(
    poll,
    state.active_turn ||
      state.devices?.camera ||
      state.devices?.recording ||
      state.devices?.speaking
      ? 180
      : 700,
  );
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
function renderMedia() {
  const d = state.devices;
  if (!d) return;
  const mic = d.awake ? (d.listener_ready ? "Listener on" : "Listener starting…") : d.recording ? "Microphone recording" : "Microphone off";
  $("wake-presence").textContent = d.awake ? "Go to sleep" : "Wake up";
  $("wake-presence").disabled = !authorized || busy || d.locked;
  const camera = d.camera
    ? "Camera on"
    : d.camera_starting
      ? "Camera opening…"
      : "Camera off";
  $("media-footer").textContent =
    `${mic} · ${camera}${d.speaking ? " · Speaking" : ""}`;
  $("device-status").textContent = d.locked
    ? "Ubuntu is locked. Unlock it to use devices. Capture will stay off until you enable it."
    : d.notice || `${mic} · ${camera}`;
  $("sensor-state").textContent = d.transcribing
    ? "Transcribing locally…"
    : d.recording
      ? "Recording · up to 15 seconds"
      : d.speaking
        ? "Speaking"
        : d.camera
          ? d.face
            ? "Camera tracking a face"
            : "Camera on · waiting for a face"
          : "No devices active";
  $("audio-level").value = d.level;
  if (!document.querySelector("#device-form:focus-within")) {
    $("audio-input").value = d.settings.input;
    $("audio-output").value = d.settings.output;
    $("camera-device").value = d.settings.camera;
    $("spoken-replies").checked = d.settings.spoken_replies;
    $("listener-phrase").value = d.settings.listener_phrase;
  }
}
async function refreshDevices() {
  const inventory = await api("/api/devices");
  for (const [id, key, label, empty] of [
    ["audio-input", "inputs", "Follow Ubuntu default input", "default"],
    ["audio-output", "outputs", "Follow Ubuntu default output", "default"],
    ["camera-device", "cameras", "Choose a camera", ""],
  ]) {
    const select = $(id),
      saved =
        state.devices?.settings[
          { inputs: "input", outputs: "output", cameras: "camera" }[key]
        ] || empty;
    select.replaceChildren(
      new Option(label, empty),
      ...inventory[key].map((d) => new Option(d.name, d.id)),
    );
    if (![...select.options].some((o) => o.value === saved))
      select.add(
        new Option("Saved device unavailable — choose another", saved),
      );
    select.value = saved;
  }
  renderMedia();
}
$("refresh-devices").addEventListener("click", () => action(refreshDevices));
$("device-form").addEventListener("submit", (event) => {
  event.preventDefault();
  action(async () => {
    apply(
      await api("/api/devices", {
        input: $("audio-input").value,
        output: $("audio-output").value,
        camera: $("camera-device").value,
        spoken_replies: $("spoken-replies").checked,
        listener_phrase: $("listener-phrase").value,
      }),
    );
    notice("Devices saved. Capture is off until you enable it.", "success");
  });
});
for (const [id, operation] of [
  ["record", "record"],
  ["send-recording", "send_recording"],
  ["mute", "mute"],
  ["read-reply", "read_reply"],
  ["camera-on", "camera_on"],
  ["camera-off", "camera_off"],
])
  $(id).addEventListener("click", () =>
    action(async () => {
      apply(await api("/api/media", { action: operation }));
    }),
  );
$("stop-all").addEventListener("click", () =>
  action(async () => {
    apply(await api("/api/stop", {}));
  }),
);
$("wake-presence").addEventListener("click", () => action(async () => {
  apply(await api("/api/media", {action: state.devices?.awake ? "sleep" : "wake"}));
}));
$("ask-view").addEventListener("click", () =>
  action(async () => {
    await api("/api/chat", {
      text: "Describe what you can see in this camera image.",
      vision: true,
    });
    apply(await api("/api/state"));
    page("presence");
  }),
);
$("desktop-action-form").addEventListener("submit", (event) => {
  event.preventDefault();
  action(async () =>
    apply(
      await api("/api/desktop-actions", {
        enabled: $("allow-workspace-open").checked,
      }),
    ),
  );
});
for (const [id, approve] of [
  ["approve-action", true],
  ["deny-action", false],
])
  $(id).addEventListener("click", () =>
    action(async () =>
      apply(
        await api("/api/approval", { id: state.pending_action?.id, approve }),
      ),
    ),
  );
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
    await refreshDevices();
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

for (const button of document.querySelectorAll("[data-avatar]"))
  button.addEventListener("click", () =>
    action(async () => {
      apply(await api("/api/appearance", { avatar: button.dataset.avatar }));
      notice(
        "Avatar selected. Your model and session are unchanged.",
        "success",
      );
    }),
  );
$("appearance-form").addEventListener("submit", (event) => {
  event.preventDefault();
  action(async () => {
    apply(
      await api("/api/appearance", {
        quality: $("render-quality").value,
        fps: Number($("render-fps").value),
        motion: $("render-motion").value,
        idle_saver: $("idle-saver").checked,
      }),
    );
    notice("Appearance applied.", "success");
  });
});
$("presence-canvas").addEventListener("avatar-error", showAvatarFallback);
$("presence-canvas").addEventListener("avatar-ready", () => {
  $("presence-canvas").hidden = false;
  $("avatar-fallback").hidden = true;
  if ($("notice").textContent.startsWith("GPU preview unavailable")) notice("");
});
