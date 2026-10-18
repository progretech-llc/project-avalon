// Canvas backend for the scoped original Cairo galaxy scene.
const rgba=(r,g,b,a=1)=>`rgba(${r*255},${g*255},${b*255},${a})`;
class Gradient {
  constructor(kind,args){this.kind=kind;this.args=args;this.stops=[];}
  addColorStopRGBA(stop,...color){this.stops.push([stop,rgba(...color)]);}
  apply(ctx){const g=ctx[this.kind](...this.args);for(const [p,c] of this.stops)g.addColorStop(p,c);return g;}
}
export class Context {
  constructor(surface){this.c=surface.canvas.getContext('2d');this.fontSize=11;this.weight='normal';this.surface=null;}
  setSourceRGB(...color){this.setSourceRGBA(...color,1);}
  setSourceRGBA(...color){this.surface=null;this.c.fillStyle=this.c.strokeStyle=rgba(...color);}
  setSource(g){this.surface=null;this.c.fillStyle=this.c.strokeStyle=g.apply(this.c);}
  setSourceSurface(surface,x,y){this.surface={image:surface.canvas??surface.image,x,y};}
  paint(){if(this.surface)this.c.drawImage(this.surface.image,this.surface.x,this.surface.y);else this.c.fillRect(0,0,this.c.canvas.width,this.c.canvas.height);}
  arc(...args){this.c.arc(...args);}
  fill(){this.c.fill();this.c.beginPath();}
  stroke(){this.c.stroke();this.c.beginPath();}
  newPath(){this.c.beginPath();}
  rectangle(...args){this.c.rect(...args);}
  moveTo(x,y){this.position=[x,y];this.c.moveTo(x,y);}
  lineTo(...args){this.c.lineTo(...args);}
  setLineWidth(value){this.c.lineWidth=value;}
  save(){this.c.save();}
  restore(){this.c.restore();}
  translate(...args){this.c.translate(...args);}
  scale(...args){this.c.scale(...args);}
  selectFontFace(name,slant,weight){this.weight=weight;this.setFontSize(this.fontSize);}
  setFontSize(size){this.fontSize=size;this.c.font=`${this.weight} ${size}px sans-serif`;}
  textExtents(text){return this.c.measureText(text);}
  showText(text){this.c.fillText(text,...this.position);this.c.beginPath();}
  $dispose(){}
}
class ImageSurface {
 constructor(format,width,height){this.canvas=document.createElement('canvas');this.canvas.width=width;this.canvas.height=height;}
 getWidth(){return this.canvas?.width??this.image.width;}
 getHeight(){return this.canvas?.height??this.image.height;}
}
export default {Context,ImageSurface,RadialGradient:class extends Gradient{constructor(...args){super('createRadialGradient',args);}},LinearGradient:class extends Gradient{constructor(...args){super('createLinearGradient',args);}},Format:{ARGB32:0},FontSlant:{NORMAL:0},FontWeight:{BOLD:'bold',NORMAL:'normal'}};
