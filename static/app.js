import { mountCore } from "./core.js?v=5.7";
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
let devicesDirty = false;
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
    robot: "Robot",
  }[name];
  if (name === "robot" && authorized) action(refreshRobot);
}
function controls() {
  if (galaxySources) syncGalaxySourceControls(galaxySources);
  for (const button of document.querySelectorAll("button[data-avatar]"))
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
  const selected = state.session?.platform && state.session.platform !== "opencode" ? {vision:true} : models.find((m) => m.name === state.session?.model);
  $("ask-view").disabled =
    !authorized ||
    busy ||
    d?.locked ||
    !d?.camera ||
    !selected?.vision ||
    !!state.active_turn;
  $("vision-capability").textContent = selected?.vision
    ? (state.session?.platform && state.session.platform !== "opencode" ? "One camera frame is sent to your native platform. Its configured model determines image support." : "Your selected model supports images. Ask about this view sends one camera frame to that same model.")
    : "Your selected model does not support images. Camera gaze still works. Select an installed vision model to ask about the view.";
  for (const id of ["save-devices", "refresh-devices", "save-desktop-actions"])
    $(id).disabled = !authorized || busy;
  $("save-permissions").disabled = !authorized || busy || !state.session;
  const native = state.session?.platform && state.session.platform !== "opencode";
  $("permission-mode").disabled = native;
  $("status-commands").disabled = native || $("permission-mode").value === "chat";
  $("native-access-note").hidden = !native;
  $("opencode-policy-note").hidden = !!native;
  $("save-permissions").disabled = native || !authorized || busy || !state.session;
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
function platformName(id) { return platforms.find(p => p.id === id)?.name || id || "OpenCode"; }
function targetChanged() {
  const target = platforms.find((p) => p.id === $("platform").value);
  $("platform-note").textContent =
    target?.reason || "Local Ollama models installed on this computer.";
  const native = target?.id !== "opencode";
  const old = $("model").value;
  $("model").replaceChildren(...(native ? [new Option("Use native configured model", "native")] : models.map(m=>new Option(m.name,m.name))));
  if (!native && models.some(m=>m.name===old)) $("model").value=old;
  $("model").disabled = native || !target?.available;
  document.querySelector('label[for="model"]').textContent = native ? "Native model" : "Installed local model";
  $("model-note").textContent = native ? "Uses this platform’s own model, provider, authentication and tools. Configure them in its native application." : "Select an installed Ollama model.";
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
          message.role === "user" ? "You" : "Avalon · " + platformName(state.session?.platform),
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
    detail.textContent = `${platformName(session.platform)} / ${session.model} · ${new Date(session.created * 1000).toLocaleDateString()}`;
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
    $("constellation-settings").hidden = a.avatar !== "constellation";
    $("avatar-fallback").src = "/static/avatars/" + a.avatar + ".png";
    $("avatar-fallback").alt = a.avatar + " still avatar";
    for (const button of document.querySelectorAll("button[data-avatar]"))
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
    ? `${platformName(state.session.platform)} / ${state.session.model}`
    : "No model connected";
  $("footer-target").textContent = state.session
    ? `${platformName(state.session.platform)} / ${state.session.model}`
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
      $("platform").value = state.session.platform || "opencode";
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
            : d.focus === "motion" ? "Following camera movement" : "Camera on · waiting for movement"
          : "No devices active";
  $("audio-level").value = d.level;
  $("voice-owner-status").textContent = d.voice_owner ? "Session voice matched. Sleep or reset to change owner." : "No session voice yet. Say the listener phrase with a command.";
  $("speech-status").textContent = d.speech_error || (d.audio_busy ? (d.speaking ? "Playing through selected output…" : "Generating local speech…") : d.speech_latency_ms != null ? `Last voice started in ${d.speech_latency_ms} ms after text was ready.` : "No voice playback yet.");
  $("preview-voice").disabled = !authorized || busy || d.locked || !!state.active_turn || d.audio_busy;
  $("reset-voice-owner").disabled = !authorized || busy || !d.awake;
  if (!devicesDirty && !document.querySelector("#device-form:focus-within")) {
    $("audio-input").value = d.settings.input;
    $("audio-output").value = d.settings.output;
    $("camera-device").value = d.settings.camera;
    $("spoken-replies").checked = d.settings.spoken_replies;
    $("listener-phrase").value = d.settings.listener_phrase;
    $("voice-engine").value = d.settings.voice_engine;
    $("voice-style").value = d.settings.voice_style;
    $("voice-pitch").value = d.settings.voice_pitch;
    $("voice-speed").value = d.settings.voice_speed;
    $("speaker-lock").checked = d.settings.speaker_lock;
    $("followup-replies").checked = d.settings.followup_replies;
    renderVoiceValues();
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
$("device-form").addEventListener("input", () => { devicesDirty = true; });
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
        voice_engine: $("voice-engine").value,
        voice_style: $("voice-style").value,
        voice_pitch: Number($("voice-pitch").value),
        voice_speed: Number($("voice-speed").value),
        speaker_lock: $("speaker-lock").checked,
        followup_replies: $("followup-replies").checked,
      }),
    );
    devicesDirty = false;
    renderMedia();
    notice("Devices saved. Capture is off until you enable it.", "success");
  });
});
for (const [id, operation] of [
  ["record", "record"],
  ["send-recording", "send_recording"],
  ["mute", "mute"],
  ["read-reply", "read_reply"],
  ["camera-on", "camera_on"],
  ["preview-voice", "preview_voice"],
  ["reset-voice-owner", "reset_owner"],
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
    if(data.appearance?.avatar==="constellation"){ $("constellation-settings").hidden=false; await refreshGalaxy(); }
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

for (const button of document.querySelectorAll("button[data-avatar]"))
  button.addEventListener("click", () =>
    action(async () => {
      apply(await api("/api/appearance", { avatar: button.dataset.avatar }));
      $("constellation-settings").hidden=button.dataset.avatar!=="constellation";
      if(button.dataset.avatar==="constellation")await refreshGalaxy();
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

function renderVoiceValues() {
  $("pitch-value").textContent = `${Number($("voice-pitch").value) > 0 ? "+" : ""}${$("voice-pitch").value} semitones`;
  $("speed-value").textContent = `${Number($("voice-speed").value).toFixed(2)}×`;
}
for (const id of ["voice-pitch", "voice-speed"]) $(id).addEventListener("input", renderVoiceValues);


async function refreshRobot() {
  const robot=await api('/api/robot');
  $('robot-status').textContent=robot.running ? 'Native LampOS services are running. Speech stays local.' : 'Native services are stopped. Start them to use music and Harness.';
  if(robot.volume!=null && !document.querySelector('#volume-form:focus-within')){$('robot-volume').value=robot.volume;$('robot-volume-value').textContent=robot.volume+'%';}
  const h=robot.harness;
  $('harness-status').textContent=h.connected ? `Connected to ${h.machine_name || 'your Harness computer'}` : h.paired ? 'Paired · waiting for the Harness computer' : 'Not paired';
  $('harness-pair').disabled=!robot.running || h.paired;
  $('harness-agents').disabled=!h.connected;
  $('music-status').textContent=robot.music?.playing ? `Playing ${robot.music.title || robot.music.query || 'music'}` : 'Music is stopped.';
}
$('robot-refresh').addEventListener('click',()=>action(refreshRobot));
$('robot-start').addEventListener('click',()=>action(async()=>{await api('/api/robot',{action:'start'});await refreshRobot();}));
$('harness-pair').addEventListener('click',()=>action(async()=>{
  const pair=await api('/api/robot',{action:'pair'});
  $('harness-code').hidden=false;$('harness-code').textContent=`Pairing code: ${pair.code}. Enter it in Harness within 60 seconds.`;
  setTimeout(()=>{$('harness-code').hidden=true;$('harness-code').textContent='';},60000);
}));
$('harness-agents').addEventListener('click',()=>action(async()=>{
  const data=await api('/api/robot',{action:'agents'});const list=$('harness-agent-list');list.replaceChildren();
  for(const agent of data.agents || []) {const item=document.createElement('li');item.textContent=(agent.name || agent.agentId)+' — '+(agent.state || agent.status || 'state not reported');list.append(item);}
  if(!data.agents?.length){const item=document.createElement('li');item.textContent='No agents are currently available in Harness.';list.append(item);}
}));
$('music-form').addEventListener('submit',event=>{event.preventDefault();action(async()=>{await api('/api/robot',{action:'music_play',query:$('music-query').value});$('music-status').textContent='Music requested. Resolving the selected track…';});});
$('music-stop').addEventListener('click',()=>action(async()=>{await api('/api/robot',{action:'music_stop'});await refreshRobot();}));
$('robot-volume').addEventListener('input',()=>{$('robot-volume-value').textContent=$('robot-volume').value+'%';});
$('volume-form').addEventListener('submit',event=>{event.preventDefault();action(async()=>{const result=await api('/api/robot',{action:'volume',volume:Number($('robot-volume').value)});notice(`Selected speaker volume: ${result.volume}%`,'success');});});

$('harness-open').addEventListener('click',()=>action(()=>api('/api/robot',{action:'open_harness'})));

const galaxyFields={paused:['Pause galaxy motion','checkbox'],foreground:['Show custom foreground wallpaper','checkbox'],rotation_speed:['Galaxy rotation speed','number',0,5],glow:['Glow','number',0,1],rays:['Light rays','number',0,1],density:['Dust density','number',0,1],links:['Show links','checkbox'],labels:['Show labels','checkbox'],agent_mode:['Agent motion','select'],solar_rotation:['Rotate solar systems','checkbox'],solar_rotation_speed:['Solar rotation speed','number',0,10],solar_clockwise:['Clockwise solar rotation','checkbox'],write_lights:['Show write activity lights','checkbox'],black_hole_name:['Shared worker name','text']};
async function refreshGalaxy(){
 const data=await api('/api/constellation'),form=$('galaxy-form');form.replaceChildren();
 for(const [key,[title,type,min,max]] of Object.entries(galaxyFields)){
  const label=document.createElement('label');label.htmlFor='galaxy-'+key;label.textContent=title;
  const field=document.createElement(type==='select'?'select':'input');field.id='galaxy-'+key;field.name=key;
  if(type==='select')for(const name of ['orbiting','asteroid','satellite']){const option=document.createElement('option');option.value=name;option.textContent=name;field.append(option);}
  else field.type=type;
  if(type==='checkbox'){field.checked=data.settings[key];label.prepend(field);label.className='checkbox-label';form.append(label);}
  else {field.value=data.settings[key];if(type==='number'){field.min=min;field.max=max;field.step='.01';}if(type==='text')field.maxLength=32;const group=document.createElement('div');group.append(label,field);form.append(group);}
 }
 const save=document.createElement('button');save.type='submit';save.className='primary';save.textContent='Apply galaxy settings';form.append(save);
 $('galaxy-status').textContent=data.scene?'Using the Avalon memory scene.':'No Avalon memory scene yet. The procedural galaxy still animates.';
 await refreshGalaxySources();
}
$('galaxy-form').addEventListener('submit',event=>{event.preventDefault();action(async()=>{const data={};for(const [key,[,type]] of Object.entries(galaxyFields)){const field=$('galaxy-'+key);data[key]=type==='checkbox'?field.checked:type==='number'?Number(field.value):field.value;}await api('/api/constellation',data);notice('Avalon galaxy settings saved.','success');});});

let galaxySources=null, galaxySourcesDirty=false, galaxySourcesTimer=null, galaxyRootSequence=0;
function syncGalaxySourceControls(data) {
  $('galaxy-reload').disabled=!authorized||busy;
  $('galaxy-source-save').disabled=!authorized||busy||!data.settings.roots.length;
  $('galaxy-scan').disabled=!authorized||busy||data.busy;
  const full=$('galaxy-root-list').children.length>=12;
  $('galaxy-root-add').disabled=!authorized||busy||full||!data.collector_available;
  $('galaxy-root-browse').disabled=!authorized||busy||full||!data.collector_available;
}
function galaxySourceNotice(data) {
  $('galaxy-source-status').textContent=(data.busy?'Refreshing… ':'')+data.notice;
  syncGalaxySourceControls(data);
}
function galaxyRootRow(root={label:'',path:''}) {
  const list=$('galaxy-root-list');if(list.children.length>=12){notice('Choose at most 12 folders.');return;}
  const row=document.createElement('div');row.className='galaxy-root-row';const id=++galaxyRootSequence;
  for(const [key,title] of [['label','System name'],['path','Absolute folder path']]){
    const group=document.createElement('div'),label=document.createElement('label'),field=document.createElement('input');
    label.htmlFor=`galaxy-root-${id}-${key}`;label.textContent=title;field.id=label.htmlFor;field.dataset.rootField=key;field.value=root[key];field.required=true;
    if(key==='label')field.maxLength=80;else field.placeholder='/path/to/your/folder';
    group.append(label,field);row.append(group);
  }
  const remove=document.createElement('button');remove.type='button';remove.className='quiet';remove.textContent='Remove';remove.setAttribute('aria-label','Remove '+(root.label||'this folder')+' from the galaxy');
  remove.addEventListener('click',()=>{row.remove();galaxySourcesDirty=true;galaxySourceNotice(galaxySources);});row.append(remove);list.append(row);
}
function renderGalaxySources(data) {
  galaxySources=data;galaxySourcesDirty=false;$('galaxy-sources-form').hidden=false;
  $('galaxy-agents-auto').checked=data.settings.display_agents===null;
  $('galaxy-current-agents').replaceChildren();$('galaxy-historical-agents').replaceChildren();
  for(const item of data.agents){
    const label=document.createElement('label');label.className='galaxy-agent-option';
    const check=document.createElement('input');check.type='checkbox';check.value=item.id;check.checked=item.selected;check.dataset.agentIdentity='';check.dataset.current=String(item.current);
    check.addEventListener('change',()=>{$('galaxy-agents-auto').checked=false;galaxySourcesDirty=true;});
    const text=document.createElement('span'),title=document.createElement('span'),detail=document.createElement('small');
    title.textContent=item.name+' · '+item.id;detail.textContent=(item.current?'Configured locally':'Historical only')+' · '+item.sources.join('; ');text.append(title,detail);label.append(check,text);
    $(item.current?'galaxy-current-agents':'galaxy-historical-agents').append(label);
  }
  if(!data.agents.some(x=>x.current)){const empty=document.createElement('p');empty.className='field-note';empty.textContent='No current named identities found. Refresh discovery or explicitly select a historical identity below.';$('galaxy-current-agents').append(empty);}
  $('galaxy-history-title').textContent=`Historical identities (${data.agents.filter(x=>!x.current).length})`;
  $('galaxy-root-list').replaceChildren();for(const root of data.settings.roots)galaxyRootRow(root);
  $('galaxy-max-files').value=data.settings.max_files;$('galaxy-max-directories').value=data.settings.max_directories;$('galaxy-show-memory').checked=data.settings.show_memory;
  galaxySourceNotice(data);
}
function watchGalaxySources(data) {
  clearTimeout(galaxySourcesTimer);
  if(data.busy)galaxySourcesTimer=setTimeout(async()=>{
    try {const next=await api('/api/constellation/sources');if(!galaxySourcesDirty)renderGalaxySources(next);else galaxySourceNotice(next);watchGalaxySources(next);}
    catch(error){$('galaxy-source-status').textContent=error.message;}
  },1000);
}
async function refreshGalaxySources(){const data=await api('/api/constellation/sources');renderGalaxySources(data);watchGalaxySources(data);}
$('galaxy-agents-auto').addEventListener('change',()=>{galaxySourcesDirty=true;if($('galaxy-agents-auto').checked)for(const field of document.querySelectorAll('[data-agent-identity]'))field.checked=field.dataset.current==='true';});
$('galaxy-agents-current').addEventListener('click',()=>{$('galaxy-agents-auto').checked=false;for(const field of document.querySelectorAll('[data-agent-identity]'))field.checked=field.dataset.current==='true';galaxySourcesDirty=true;});
$('galaxy-agents-none').addEventListener('click',()=>{$('galaxy-agents-auto').checked=false;for(const field of document.querySelectorAll('[data-agent-identity]'))field.checked=false;galaxySourcesDirty=true;});
$('galaxy-root-add').addEventListener('click',()=>{galaxyRootRow();galaxySourcesDirty=true;galaxySourceNotice(galaxySources);});
$('galaxy-root-browse').addEventListener('click',()=>action(async()=>{const result=await api('/api/constellation/folder',{});if(result.path){galaxyRootRow({label:result.path.split('/').filter(Boolean).at(-1)||'Root',path:result.path});galaxySourcesDirty=true;galaxySourceNotice(galaxySources);}}));
$('galaxy-sources-form').addEventListener('input',()=>{galaxySourcesDirty=true;});
$('galaxy-reload').addEventListener('click',()=>action(refreshGalaxySources));
$('galaxy-scan').addEventListener('click',()=>action(async()=>{const data=await api('/api/constellation/sources',{action:'refresh'});galaxySourceNotice({...data,busy:true});watchGalaxySources({...data,busy:true});}));
$('galaxy-sources-form').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
  const roots=Array.from($('galaxy-root-list').children,row=>Object.fromEntries(Array.from(row.querySelectorAll('[data-root-field]'),field=>[field.dataset.rootField,field.value])));
  const selected=$('galaxy-agents-auto').checked?null:Array.from(document.querySelectorAll('[data-agent-identity]:checked'),field=>field.value);
  const data=await api('/api/constellation/sources',{action:'save',revision:galaxySources.revision,settings:{roots,display_agents:selected,max_files:Number($('galaxy-max-files').value),max_directories:Number($('galaxy-max-directories').value),show_memory:$('galaxy-show-memory').checked}});
  renderGalaxySources(data);watchGalaxySources({...data,busy:true});notice('Avalon agent and folder selection saved.','success');
});});
