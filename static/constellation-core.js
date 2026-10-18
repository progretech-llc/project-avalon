import {DEFAULT_SETTINGS,advancePhase,renderGalaxy} from './galaxy.js';
import {Context} from './cairo-canvas.js';
export function mountConstellation(canvas) {
 let active=false, scene=null, foreground=null, settings={...DEFAULT_SETTINGS}, appearance={}, sensors={gaze:[0,0],level:0}, status='', phase=.22, systemPhase=0, clock=0,last=0,nextFetch=0,cache={};
 const cr=new Context({canvas});
 async function refresh(){
  try {const response=await fetch('/api/constellation');if(!response.ok)return;const data=await response.json();settings={...DEFAULT_SETTINGS,...data.settings};scene=data.scene;
   if(data.foreground&&!foreground){const image=new Image();image.src='/api/constellation/foreground';await image.decode();foreground={image,getWidth:()=>image.width,getHeight:()=>image.height};}
  } catch { /* Native renderer and explicit scene status remain available. */ }
 }
 function draw(now){requestAnimationFrame(draw);if(!active||document.hidden||!canvas.getClientRects().length){last=now;return;}
  if(now>nextFetch){nextFetch=now+2000;refresh();}
  const still=appearance.motion==='reduced'||(appearance.motion==='system'&&matchMedia('(prefers-reduced-motion: reduce)').matches);
  const fps=appearance.idle_saver&&['idle','disconnected'].includes(status)?15:(appearance.fps??30);if(now-last<1000/fps)return;
  const dt=Math.min(.2,(now-last)/1000);last=now;
  const box=canvas.getBoundingClientRect(),w=Math.max(1,Math.round(box.width)),h=Math.max(1,Math.round(box.height));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;cache={};}
  if(!still&&!settings.paused){phase=advancePhase(phase,dt,settings.rotation_speed);systemPhase=advancePhase(systemPhase,dt,settings.solar_rotation_speed*(settings.solar_clockwise?-1:1));clock+=dt;}
  const level=status==='speaking'&&!still?sensors.level:0;
  renderGalaxy(cr,w,h,scene,{...settings,avalon_preview:true,density:settings.density*(appearance.quality==="economy"?.6:1),avalon_base_glow:settings.glow,glow:settings.glow*(1+level*.8),rays:settings.rays+level*.65,avalon_gaze:still?[0,0]:sensors.gaze},phase,clock,foreground,null,systemPhase,cache);
  canvas.dataset.avatar='constellation';canvas.dataset.frames=String(Number(canvas.dataset.frames??0)+1);
 }
 requestAnimationFrame(draw);
 return (value,options,input)=>{active=options.avatar==='constellation';appearance=options;status=value;sensors=input??sensors;canvas.hidden=!active;};
}
