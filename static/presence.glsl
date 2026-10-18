// Original Avalon volume renderer. Shared verbatim by WebGL and GNOME/Cogl.
uniform float u_gaze_x,u_gaze_y,u_level;
float avHash(vec3 p) { p=fract(p*0.1031); p+=dot(p,p.yzx+33.33); return fract((p.x+p.y)*p.z); }
float avNoise(vec3 p) {
    vec3 i=floor(p),f=fract(p); f=f*f*(3.0-2.0*f);
    return mix(mix(mix(avHash(i),avHash(i+vec3(1,0,0)),f.x),mix(avHash(i+vec3(0,1,0)),avHash(i+vec3(1,1,0)),f.x),f.y),mix(mix(avHash(i+vec3(0,0,1)),avHash(i+vec3(1,0,1)),f.x),mix(avHash(i+vec3(0,1,1)),avHash(i+vec3(1,1,1)),f.x),f.y),f.z);
}
mat2 avRotate(float a) { float s=sin(a),c=cos(a); return mat2(c,-s,s,c); }
float avSmooth(float a,float b,float k) { float h=clamp(0.5+0.5*(b-a)/k,0.0,1.0);return mix(b,a,h)-k*h*(1.0-h); }
float avEllipsoid(vec3 p,vec3 r) { float k0=length(p/r),k1=length(p/(r*r));return k0*(k0-1.0)/max(k1,0.0001); }
float avCapsule(vec3 p,vec3 a,vec3 b,float r) { vec3 q=p-a,v=b-a;return length(q-v*clamp(dot(q,v)/dot(v,v),0.0,1.0))-r; }
float avBox(vec3 p,vec3 bounds) { vec3 q=abs(p)-bounds;return length(max(q,0.0))+min(max(q.x,max(q.y,q.z)),0.0); }
float avBody(vec3 p,float avatar,float t) {
    if(avatar>2.5) {
        p.xz=avRotate(0.3*t+u_gaze_x*.3)*p.xz;
        float a=length(vec2(length(p.xz)-0.58,p.y))-0.04;
        p.xy=avRotate(0.94)*p.xy;
        float b=length(vec2(length(p.xy)-0.59,p.z))-0.028;
        return min(min(a,b),length(p)-0.20);
    }
    float breathe=sin(t*1.15)*0.012;
    if(avatar>1.5) {
        p.y+=0.20;
        vec3 h=p-vec3(0,0.34,0);h.xz=avRotate(sin(t*0.47)*0.13+u_gaze_x*.28)*h.xz;
        float head=avEllipsoid(h,vec3(0.56,0.46,0.40));
        float body=avEllipsoid(p-vec3(0,-0.37,0),vec3(0.37+breathe,0.43,0.30));
        float ears=avEllipsoid(vec3(abs(p.x)-0.59,p.y-0.32,p.z),vec3(0.13,0.30,0.24));
        float arms=avCapsule(p,vec3(sign(p.x)*0.38,-0.31,0),vec3(sign(p.x)*0.56,-0.66,0.07),0.12);
        float feet=avEllipsoid(vec3(abs(p.x)-0.22,p.y+0.81,p.z-0.08),vec3(0.19,0.13,0.25));
        float antenna=avCapsule(p,vec3(0,0.76,0),vec3(0.08,1.00,0),0.025);
        return min(min(min(avSmooth(head,body,0.08),ears),min(arms,feet)),min(antenna,length(p-vec3(0.08,1,0))-0.07));
    }
    if(avatar>0.5) {
        // Projecting tapered cowl, recessed mask and constructed armor silhouette.
        vec3 h=p-vec3(0,0.97,-0.03);h.xz=avRotate(sin(t*.31)*.06+u_gaze_x*.28)*h.xz;
        float taper=.40-.16*smoothstep(0.0,.53,h.y);
        float hood=avEllipsoid(h,vec3(taper,.53,.33));
        float opening=avEllipsoid(h-vec3(0,-.025,.27),vec3(.275,.37,.36));
        hood=max(hood,-opening);
        float mask=avEllipsoid(h-vec3(0,-.02,-.015),vec3(.20,.29,.085));
        vec3 shoulder=vec3(abs(p.x)-.55,p.y-.30,p.z+.035);shoulder.xy=avRotate(.34)*shoulder.xy;
        float mantle=avBox(shoulder,vec3(.32,.115,.26))-.025;
        float torso=avEllipsoid(p-vec3(0,-.40,0),vec3(.35,.87,.23));
        float waist=avBox(p-vec3(0,-1.14,0),vec3(.26,.45,.17))-.035;
        float chest=avBox(vec3(abs(p.x)-.18,p.y-.09,p.z-.17),vec3(.145,.23,.10))-.035;
        vec3 arm=vec3(abs(p.x)-.65,p.y+.24,p.z);arm.xy=avRotate(-.15)*arm.xy;
        float upperArm=avBox(arm,vec3(.105,.34,.15))-.025;
        float gauntlet=avBox(vec3(abs(p.x)-.75,p.y+.80,p.z-.06),vec3(.13,.27,.15))-.025;
        float hand=avEllipsoid(vec3(abs(p.x)-.76,p.y+1.14,p.z-.09),vec3(.09,.15,.07));
        vec3 plate=p-vec3(0,-.64,.225);plate.y=mod(plate.y+.12,.24)-.12;
        float ribs=max(avBox(plate,vec3(.265,.052,.045))-.008,max(p.y+.27,-1.04-p.y));
        float body=avSmooth(torso,waist,.08);body=avSmooth(body,mantle,.06);
        body=min(body,chest);body=min(body,ribs);body=avSmooth(body,upperArm,.055);body=avSmooth(body,gauntlet,.045);
        body=avSmooth(body,hand,.04);body=avSmooth(body,hood,.055);
        return min(body,mask);
    }
    vec3 head=p-vec3(0,0.94,0);head.xz=avRotate(sin(t*0.31)*0.10+u_gaze_x*.28)*head.xz;head.yz=avRotate(0.025*sin(t*.45)+u_gaze_y*.15)*head.yz;
    float skull=avEllipsoid(head,vec3(0.26,0.36,0.24));
    float jaw=avEllipsoid(head-vec3(0,-0.17,0.035),vec3(0.195,0.20,0.205));
    float face=avSmooth(skull,jaw,0.06);
    float bridge=avEllipsoid(head-vec3(0,-0.015,0.218),vec3(0.028,0.09,0.038));
    face=avSmooth(face,bridge,0.055);
    float neck=avCapsule(p,vec3(0,0.43,0),vec3(0,0.71,0),0.125);
    float torso=avEllipsoid(p-vec3(0,-0.35,0),vec3(0.40+breathe,0.87,0.235));
    float chest=avEllipsoid(vec3(abs(p.x)-0.20,p.y-0.15,p.z-0.075),vec3(0.255+breathe,0.26,0.20));
    float shoulders=avEllipsoid(vec3(abs(p.x)-0.48,p.y-0.23,p.z+0.025),vec3(0.22,0.22,0.22));
    float arms=avCapsule(p,vec3(sign(p.x)*0.54,0.16,-0.025),vec3(sign(p.x)*0.72,-0.43,0.02),0.145);
    float forearms=avCapsule(p,vec3(sign(p.x)*0.72,-0.43,0.02),vec3(sign(p.x)*(0.75+0.025*sin(t*.7)),-0.99,0.12),0.105);
    float hands=avEllipsoid(vec3(abs(p.x)-0.77,p.y+1.12,p.z-0.13),vec3(0.10,0.17,0.07));
    float waist=avEllipsoid(p-vec3(0,-0.84,0),vec3(0.28,0.50,0.22));
    float hips=avEllipsoid(p-vec3(0,-1.36,0),vec3(0.36,0.40,0.25));
    float body=avSmooth(torso,waist,0.12);body=avSmooth(body,hips,0.12);body=avSmooth(body,chest,0.15);body=avSmooth(body,shoulders,0.18);body=avSmooth(body,neck,0.10);
    body=avSmooth(body,arms,0.13);body=avSmooth(body,forearms,0.10);body=avSmooth(body,hands,0.065);body=avSmooth(body,face,0.06);
    return body;
}
vec3 avNormal(vec3 p,float a,float t,float d) {
    vec2 e=vec2(0.002,0.0);
    return normalize(vec3(avBody(p+e.xyy,a,t)-d,avBody(p+e.yxy,a,t)-d,avBody(p+e.yyx,a,t)-d));
}
vec3 avalon(vec2 uv,float aspect,float time,float state,float avatar,float quality) {
    float active=step(1.5,state)*step(state,4.5);
    float t=time*(1.0+active*0.42);
    vec2 screen=(uv-0.5)*vec2(aspect,1.0);
    vec2 p=screen*3.05;
    vec3 cold=vec3(0.12,0.76,0.88),warm=vec3(1.0,0.49,0.11);
    if(avatar>0.5&&avatar<1.5){cold=vec3(0.47,0.14,1.0);warm=vec3(1.0,0.24,0.78);}
    if(avatar>1.5&&avatar<2.5){cold=vec3(0.08,0.79,0.61);warm=vec3(1.0,0.66,0.15);}
    if(avatar>2.5){cold=vec3(0.26,0.20,0.95);warm=vec3(0.71,0.34,1.0);}
    vec3 statusColor=cold;
    if(state>4.5&&state<5.5)statusColor=vec3(0.12,1.0,0.48);
    if(state>5.5&&state<6.5)statusColor=vec3(1.0,0.18,0.09);
    if(state>7.5&&state<8.5)statusColor=vec3(0.75,0.27,1.0);
    if(state>8.5&&state<9.5)statusColor=vec3(.10,.65,1.0);
    if(state>9.5&&state<10.5)statusColor=warm;
    if(state>10.5)statusColor=vec3(1.0,.65,.10);
    float connected=state<0.5?0.40:1.0;
    vec3 color=vec3(0.012,0.019,0.038);
    float cloud=avNoise(vec3(screen*3.0,t*0.025));
    color+=vec3(0.055,0.018,0.10)*pow(cloud,2.0)*exp(-0.6*length(p));
    // Flowing filaments occupy actual depth behind the body, not an image loop.
    for(int j=0;j<4;j++) {
        float f=float(j),y=0.30*sin(p.x*1.7+t*(0.22+f*.03)+f*1.8)+0.12*sin(p.x*3.0-t*.4+f)-0.20;
        float filament=exp(-125.0*abs(p.y-y-f*.12));
        float spread=exp(-0.6*abs(p.x));
        color+=mix(cold,warm,0.5+0.5*sin(p.x*1.3+f))*filament*spread*(0.22+active*.18);
    }
    vec2 cell=floor(screen*vec2(440.0));
    float star=avHash(vec3(cell,0.3));
    color+=step(0.9975,star)*vec3(0.18,0.34,0.48)*(0.4+0.6*sin(star*110.0+t*0.35));
    vec3 ro=vec3(0,0.04,4.5),rd=normalize(vec3(p,-4.4));
    float distance=2.8,hit=0.0,glow=0.0,surfaceD=0.0;vec3 pos=ro;
    if(abs(p.x)<1.08&&abs(p.y)<1.55)for(int i=0;i<72;i++) {
        if(float(i)>(quality<0.5?35.0:quality<1.5?51.0:71.0))break;
        pos=ro+rd*distance;
        float d=avBody(pos,avatar,t);
        glow+=exp(-30.0*abs(d))*0.014;
        if(d<0.0018){hit=1.0;surfaceD=d;break;}
        distance+=d*0.85;
        if(distance>6.4)break;
    }
    color+=mix(cold,warm,0.5+0.5*sin(p.x*2.0))*glow*0.30;
    if(hit>0.5) {
        vec3 n=avNormal(pos,avatar,t,surfaceD);
        float edge=pow(1.0-max(0.0,dot(n,-rd)),2.0);
        float light=max(0.0,dot(n,normalize(vec3(-1,0.4,0.7))));
        float rim=max(0.0,dot(n,normalize(vec3(1,0.3,-0.1))));
        float grain=avHash(floor(pos*vec3(245,245,245)));
        float dust=pow(grain,11.0);
        float field=sin(pos.y*26.0+t*1.9+sin(pos.x*19.0+t)*0.9+sin(pos.z*23.0));
        float circuits=pow(max(0.0,field),16.0);
        color=mix(color,cold*0.045,0.91);
        color+=(cold*(0.15+light*.35)+warm*rim*.5)*dust*(3.4+active*.9);
        color+=mix(cold,warm,light)*edge*(1.0+grain*.7);
        color+=statusColor*circuits*(0.20+active*.22);
        float branches=abs(sin(pos.y*8.0+sin(pos.x*12.0+t*.5)+pos.z*8.0));
        color+=mix(warm,cold,0.5+0.5*pos.x)*exp(-80.0*branches)*(.30+edge*.5);
        if(avatar>2.5)color+=warm*(.13+edge*.7)+statusColor*circuits*.7;
        if(avatar>0.5&&avatar<1.5) {
            color+=cold*(.035+light*.10)+warm*pow(max(0.0,dot(reflect(rd,n),normalize(vec3(-.4,.8,1)))),20.0)*.25;
            float recessed=step(.62,pos.y)*step(pos.y,1.30)*step(abs(pos.x),.235)*step(pos.z,.13);
            color=mix(color,vec3(.004,.002,.012),recessed*.97);
        }
        vec3 core=pos-vec3(0,avatar>1.5?-0.64:0.02,0.28);
        float heart=exp(-15.0*length(core));
        color+=mix(warm,statusColor,step(4.5,state)*0.6)*heart*(2.8+0.7*sin(t*2.0)+u_level*4.0);
        if(avatar>1.5&&avatar<2.5) {
            // Rounded visor and original friendly face, attached to moving head.
            vec3 h=pos-vec3(0,0.14,0);h.xz=avRotate(sin(t*.47)*.13+u_gaze_x*.28)*h.xz;
            float visor=step(abs(h.x),.41)*step(abs(h.y),.22)*step(.29,h.z);
            float metallic=pow(max(0.0,dot(reflect(rd,n),normalize(vec3(-.4,.8,1)))),24.0);
            vec3 ceramic=cold*(.12+light*.55+rim*.16)+vec3(.65,.88,.84)*metallic*.65;
            if(abs(pos.x)>.48&&pos.y>-.2)ceramic=warm*(.23+light*.60+metallic);
            color=mix(color,ceramic,.90);
            color=mix(color,vec3(.008,.03,.035)+vec3(.06,.13,.13)*metallic,visor*.98);
            float eyes=length(vec2(abs(h.x)-.20,h.y-.025));
            float eye=exp(-110.0*abs(eyes-.075));
            float blink=step(0.06,abs(sin(t*.32+1.2)));
            color+=warm*eye*visor*blink*2.0;
            float smile=abs(length(vec2(h.x,h.y+.005))-.13);
            color+=warm*exp(-100.0*smile)*step(h.y,-.025)*visor;
            color+=warm*pow(max(0.0,dot(n,normalize(vec3(-1,1,1)))),18.0)*.7;
        }
        color*=connected;
    }
    float coreY=avatar>2.5?0.0:avatar>1.5?-0.64:0.02;
    float coreGlow=exp(-23.0*length(p-vec2(0,coreY)));
    color+=mix(warm,statusColor,step(4.5,state)*0.6)*coreGlow*(0.8+0.2*sin(t*2.0)+u_level*2.0)*connected;
    if(state>10.5)color+=statusColor*.12*exp(-1.5*length(p));
    return 1.0-exp(-color*1.24);
}
