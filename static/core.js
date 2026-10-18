// The same original volume shader runs in GNOME/Cogl and the control center.
const vertex = `attribute vec2 a_position;varying vec2 uv;void main(){uv=a_position*.5+.5;gl_Position=vec4(a_position,0.,1.);}`;
const states = {
  disconnected: 0,
  idle: 1,
  working: 2,
  writing: 3,
  executing: 4,
  completed: 5,
  failed: 6,
  cancelled: 7,
  switching: 8,
  listening: 9,
  speaking: 10,
  approval: 11,
};
const avatars = { ethereal: 0, sentinel: 1, mascot: 2, abstract: 3 };
let sharedSource;
export function mountCore(canvas) {
  const gl = canvas.getContext("webgl", {
    alpha: false,
    antialias: false,
    powerPreference: "low-power",
  });
  if (!gl) throw Error("GPU preview is unavailable");
  let program,
    frame,
    dirty = true,
    last = 0,
    status = 0,
    appearance = {
      avatar: "ethereal",
      quality: "balanced",
      fps: 30,
      motion: "system",
      idle_saver: true,
    },
    frames = 0,
    sensors = { gaze: [0, 0], level: 0 };
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const observer = new IntersectionObserver((entries) => {
    visible = entries[0]?.isIntersecting;
    dirty = true;
  });
  let visible = true;
  observer.observe(canvas);
  function compile(type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const message = gl.getShaderInfoLog(shader);
      gl.deleteShader(shader);
      throw Error(message);
    }
    return shader;
  }
  function initialize(source) {
    program = gl.createProgram();
    const vs = compile(gl.VERTEX_SHADER, vertex),
      fs = compile(
        gl.FRAGMENT_SHADER,
        `precision highp float;varying vec2 uv;uniform sampler2D u_portrait;vec4 avPortrait(vec2 p){return texture2D(u_portrait,vec2(p.x,1.0-p.y));}uniform float u_time,u_aspect,u_state,u_avatar,u_quality;${source}\nvoid main(){gl_FragColor=vec4(avalon(uv,u_aspect,u_time,u_state,u_avatar,u_quality),1.);}`,
      );
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS))
      throw Error("Avatar program could not link");
    gl.useProgram(program);
    const texture = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, portrait);
    gl.uniform1i(gl.getUniformLocation(program, "u_portrait"), 0);
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]),
      gl.STATIC_DRAW,
    );
    const p = gl.getAttribLocation(program, "a_position");
    gl.enableVertexAttribArray(p);
    gl.vertexAttribPointer(p, 2, gl.FLOAT, false, 0, 0);
    locations = Object.fromEntries(
      [
        "time",
        "aspect",
        "state",
        "avatar",
        "quality",
        "gaze_x",
        "gaze_y",
        "level",
      ].map((k) => [k, gl.getUniformLocation(program, "u_" + k)]),
    );
    dirty = true;
    delete canvas.dataset.error;
    canvas.dispatchEvent(new CustomEvent("avatar-ready"));
  }
  let locations;
  function draw(now) {
    frame = requestAnimationFrame(draw);
    if (!program || document.hidden || !visible) return;
    const still =
      appearance.motion === "reduced" ||
      (appearance.motion === "system" && reduced.matches);
    const box = canvas.getBoundingClientRect();
    const scales = { economy: 0.65, balanced: 1, high: 1.5 };
    const ratio = Math.min(devicePixelRatio || 1, scales[appearance.quality]);
    const w = Math.max(1, Math.round(box.width * ratio)),
      h = Math.max(1, Math.round(box.height * ratio));
    if (w !== canvas.width || h !== canvas.height) {
      canvas.width = w;
      canvas.height = h;
      gl.viewport(0, 0, w, h);
      dirty = true;
    }
    const fps =
      appearance.idle_saver && status <= 1
        ? Math.min(15, appearance.fps)
        : appearance.fps;
    if ((still && !dirty) || (!dirty && now - last < 1000 / fps - 1)) return;
    gl.uniform1f(locations.time, still ? 0 : now / 1000);
    gl.uniform1f(locations.aspect, w / h);
    gl.uniform1f(locations.state, status);
    gl.uniform1f(locations.avatar, avatars[appearance.avatar] ?? 0);
    gl.uniform1f(
      locations.quality,
      ["economy", "balanced", "high"].indexOf(appearance.quality),
    );
    gl.uniform1f(locations.gaze_x, still ? 0 : sensors.gaze[0]);
    gl.uniform1f(locations.gaze_y, still ? 0 : sensors.gaze[1]);
    gl.uniform1f(locations.level, still ? 0 : sensors.level);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    last = now;
    dirty = false;
    frames++;
    canvas.dataset.frames = frames;
    canvas.dataset.state = Object.keys(states)[status];
    canvas.dataset.avatar = appearance.avatar;
  }
  function failed(error) {
    canvas.dataset.error = "unavailable";
    canvas.setAttribute(
      "aria-label",
      "Avatar preview unavailable. Connection status remains below.",
    );
    canvas.dispatchEvent(
      new CustomEvent("avatar-error", { detail: error.message }),
    );
  }
  sharedSource ??= fetch("/static/presence.glsl?v=4.4").then((r) => {
    if (!r.ok) throw Error("Avatar shader is unavailable");
    return r.text();
  });
  const portrait = new Image();
  const portraitReady = new Promise((resolve, reject) => {
    portrait.onload = resolve;
    portrait.onerror = () => reject(Error("Progre artwork is unavailable"));
    portrait.src = "/static/art/progre.png?v=4.4";
  });
  Promise.all([sharedSource, portraitReady]).then(([source]) => initialize(source)).catch(failed);
  frame = requestAnimationFrame(draw);
  reduced.addEventListener("change", () => {
    dirty = true;
  });
  canvas.addEventListener("webglcontextlost", (event) => {
    event.preventDefault();
    program = null;
    failed(Error("GPU preview lost. Restoring…"));
  });
  canvas.addEventListener("webglcontextrestored", () =>
    sharedSource.then(initialize).catch(failed),
  );
  return (value, settings, input) => {
    if (input && JSON.stringify(input) !== JSON.stringify(sensors)) {
      sensors = input;
      if (!(
        appearance.motion === "reduced" ||
        (appearance.motion === "system" && reduced.matches)
      ))
        dirty = true;
    }
    const next = states[value] ?? 0;
    if (next !== status) {
      status = next;
      dirty = true;
    }
    if (
      settings &&
      Object.entries(settings).some(([key, value]) => appearance[key] !== value)
    ) {
      appearance = { ...appearance, ...settings };
      canvas.setAttribute(
        "aria-label",
        "Live " + appearance.avatar + " avatar preview",
      );
      dirty = true;
    }
  };
}
