// The control center uses the same verified activity states as the wallpaper.
const vertex = `attribute vec2 a_position;varying vec2 uv;void main(){uv=a_position*0.5+0.5;gl_Position=vec4(a_position,0.,1.);}`;
const fragment = `precision highp float;varying vec2 uv;uniform float time;uniform float aspect;uniform float state;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
void main(){vec2 p=(uv-.5)*vec2(aspect,1.);p.y-=.06;float radius=length(p);float active=step(1.5,state)*step(state,4.5);float t=time*(1.+active*1.7);float breath=.22+.008*sin(t*.8);float ring=exp(-120.*abs(radius-breath));float halo=exp(-8.*radius);float angle=atan(p.y,p.x);float flow=.55+.45*sin(angle*4.-t*.7+radius*14.);vec3 color=vec3(.024,.039,.065);vec3 accent=vec3(.06,.58,.72);if(state>4.5&&state<5.5)accent=vec3(.1,.8,.42);if(state>5.5&&state<6.5)accent=vec3(.9,.2,.12);if(state>7.5)accent=vec3(.65,.35,.85);color+=accent*ring*(.7+flow)*(state<.5?.35:1.);color+=vec3(.16,.10,.34)*halo;color+=vec3(1.,.64,.19)*exp(-38.*radius)*(.8+.2*sin(t));vec2 grid=floor(uv*vec2(150.*aspect,150.));color+=step(.996,hash(grid))*vec3(.15,.29,.4)*(.5+.5*sin(t+hash(grid)*6.28));gl_FragColor=vec4(color,1.);}`;
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
};
export function mountCore(canvas) {
  const gl = canvas.getContext("webgl", { alpha: false, antialias: false });
  if (!gl) {
    canvas.setAttribute(
      "aria-label",
      "Energy-core preview unavailable; use the connection status below",
    );
    return () => {};
  }
  function shader(type, source) {
    const value = gl.createShader(type);
    gl.shaderSource(value, source);
    gl.compileShader(value);
    if (!gl.getShaderParameter(value, gl.COMPILE_STATUS))
      throw Error("Preview shader could not compile");
    return value;
  }
  const program = gl.createProgram();
  gl.attachShader(program, shader(gl.VERTEX_SHADER, vertex));
  gl.attachShader(program, shader(gl.FRAGMENT_SHADER, fragment));
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return () => {};
  gl.useProgram(program);
  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(
    gl.ARRAY_BUFFER,
    new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]),
    gl.STATIC_DRAW,
  );
  const position = gl.getAttribLocation(program, "a_position");
  gl.enableVertexAttribArray(position);
  gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
  const uTime = gl.getUniformLocation(program, "time"),
    uAspect = gl.getUniformLocation(program, "aspect"),
    uState = gl.getUniformLocation(program, "state");
  let status = 0,
    last = 0,
    frame;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  function draw(now) {
    frame = requestAnimationFrame(draw);
    if (document.hidden || now - last < (reduced.matches ? 1000 : 33)) return;
    last = now;
    const box = canvas.getBoundingClientRect(),
      ratio = Math.min(devicePixelRatio || 1, 1.5);
    const w = Math.max(1, Math.round(box.width * ratio)),
      h = Math.max(1, Math.round(box.height * ratio));
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
      gl.viewport(0, 0, w, h);
    }
    gl.uniform1f(uTime, reduced.matches ? 0 : now / 1000);
    gl.uniform1f(uAspect, w / h);
    gl.uniform1f(uState, status);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
  }
  frame = requestAnimationFrame(draw);
  canvas.addEventListener("webglcontextlost", (event) => {
    event.preventDefault();
    cancelAnimationFrame(frame);
  });
  return (value) => {
    status = states[value] ?? 0;
  };
}
