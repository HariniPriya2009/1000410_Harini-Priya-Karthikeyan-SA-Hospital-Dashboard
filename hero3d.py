"""3D hero for the Summary page: Jabby the syringe mascot, floating pills, crosses and a DNA helix.

The scene runs inside an iframe (st.components.v1.html), so it cannot slow down the rest of the app.
- Three.js is loaded from jsdelivr, with cdnjs as a backup. If both fail, or WebGL is off, a flat SVG is shown.
- It pauses when scrolled out of view or when the tab is hidden.
- Pixel ratio is capped at 1.5 and drops to 1 if the frame rate falls under 30 fps.
"""
from __future__ import annotations

import json

THREE_PRIMARY = "https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"
THREE_BACKUP = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"

_HTML = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:transparent;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#0E2A47;overflow:hidden}
#wrap{position:relative;height:100%;overflow:hidden;background:linear-gradient(120deg,#FFFFFF 0%,#EEF6FF 42%,#E2F6EE 100%)}
.blob{position:absolute;border-radius:50%;will-change:transform}
.b1{width:440px;height:440px;left:-130px;top:-170px;background:radial-gradient(circle,rgba(30,111,217,.22),transparent 65%);animation:d1 12s ease-in-out infinite alternate}
.b2{width:560px;height:560px;right:-150px;bottom:-240px;background:radial-gradient(circle,rgba(29,185,138,.28),transparent 65%);animation:d2 14s ease-in-out infinite alternate}
.b3{width:280px;height:280px;left:42%;top:-100px;background:radial-gradient(circle,rgba(207,206,93,.34),transparent 65%);animation:d1 16s ease-in-out infinite alternate-reverse}
.b4{width:300px;height:300px;left:-90px;bottom:-130px;background:radial-gradient(circle,rgba(229,56,79,.13),transparent 65%);animation:d2 18s ease-in-out infinite alternate}
@keyframes d1{from{transform:translate3d(0,0,0)}to{transform:translate3d(60px,26px,0)}}
@keyframes d2{from{transform:translate3d(0,0,0)}to{transform:translate3d(-56px,-30px,0)}}
.grid{position:absolute;inset:0;background-image:radial-gradient(rgba(30,111,217,.17) 1.2px,transparent 1.5px);background-size:26px 26px;-webkit-mask-image:linear-gradient(90deg,#000,transparent 65%);mask-image:linear-gradient(90deg,#000,transparent 65%)}
#copy{position:absolute;left:44px;top:0;bottom:0;width:54%;display:flex;flex-direction:column;justify-content:center;z-index:2}
.eyebrow{display:inline-flex;gap:8px;align-items:center;font-size:12px;font-weight:800;letter-spacing:.18em;color:#0B4F9C;background:rgba(30,111,217,.10);padding:7px 13px;border-radius:999px;width:fit-content;animation:up .7s both}
.eyebrow i{width:8px;height:8px;border-radius:50%;background:#E5384F;animation:blip 1.4s infinite}
@keyframes blip{0%,100%{box-shadow:0 0 0 0 rgba(229,56,79,.55)}70%{box-shadow:0 0 0 8px rgba(229,56,79,0)}}
h1{font-size:clamp(28px,4vw,52px);line-height:1.05;font-weight:900;margin:16px 0 10px;letter-spacing:-.02em;background:linear-gradient(100deg,#0B4F9C,#1E6FD9 55%,#1DB98A);-webkit-background-clip:text;background-clip:text;color:transparent;animation:up .7s .08s both}
p.sub{font-size:clamp(13px,1.3vw,17px);color:#4A6580;max-width:540px;line-height:1.5;animation:up .7s .16s both}
svg.ecg{width:250px;height:42px;margin:12px 0 2px;animation:up .7s .22s both}
svg.ecg path{fill:none;stroke:#E5384F;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:300;animation:ecg 3s linear infinite}
@keyframes ecg{from{stroke-dashoffset:600}to{stroke-dashoffset:0}}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:14px;max-width:660px}
.stat{position:relative;overflow:hidden;background:#fff;border:1px solid #DDEBF5;border-radius:16px;padding:11px 12px 10px 15px;box-shadow:0 8px 20px rgba(14,42,71,.06);animation:up .7s both}
.stat::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--c)}
.stat b{display:block;font-size:clamp(15px,1.7vw,24px);font-weight:900;white-space:nowrap}
.stat span{font-size:10px;letter-spacing:.08em;font-weight:700;color:#5F7690;text-transform:uppercase}
@keyframes up{from{opacity:0;transform:translate3d(0,14px,0)}to{opacity:1;transform:none}}
#stage{position:absolute;right:0;top:0;bottom:0;width:48%;z-index:1;cursor:pointer}
canvas{width:100%;height:100%;display:block;outline:none}
#bubble{position:absolute;left:3%;top:5%;transform:none;max-width:210px;background:#fff;border:1px solid #DDEBF5;border-radius:16px;padding:10px 13px;font-size:13px;line-height:1.4;font-weight:600;box-shadow:0 10px 26px rgba(14,42,71,.12);pointer-events:none;animation:pop .5s cubic-bezier(.2,1.4,.4,1) both}
#bubble::after{content:"";position:absolute;left:46px;bottom:-7px;width:12px;height:12px;background:#fff;border-right:1px solid #DDEBF5;border-bottom:1px solid #DDEBF5;transform:rotate(45deg)}
@keyframes pop{from{opacity:0;transform:scale(.85)}to{opacity:1;transform:scale(1)}}
#fb{display:none;position:absolute;inset:0;align-items:center;justify-content:center}
#fb svg{width:46%;max-width:210px;animation:fl 3.6s ease-in-out infinite}
@keyframes fl{0%,100%{transform:translateY(0) rotate(-6deg)}50%{transform:translateY(-12px) rotate(4deg)}}
.nogl #c{display:none}.nogl #fb{display:flex}
@media (max-width:760px){
 #copy{left:20px;right:20px;width:auto;top:14px;bottom:auto;justify-content:flex-start}
 h1{margin:10px 0 6px}svg.ecg,p.sub{display:none}
 .stats{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
 #stage{width:100%;top:auto;height:50%}
 #bubble{top:2%;left:6%}
}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
</style></head><body>
<div id="wrap">
 <div class="blob b1"></div><div class="blob b2"></div><div class="blob b3"></div><div class="blob b4"></div><div class="grid"></div>
 <div id="copy">
  <div class="eyebrow"><i></i>MEDISCOPE HEALTH ANALYTICS</div>
  <h1>Hospital Inpatient<br>Discharges Dashboard</h1>
  <p class="sub">See where stays run long, where charges climb and how every county and hospital compares.</p>
  <svg class="ecg" viewBox="0 0 250 42"><path d="M0 22 H70 L80 22 L90 6 L102 38 L113 2 L124 22 H170 L178 22 L186 14 L194 28 L202 22 H250"/></svg>
  <div class="stats" id="stats"></div>
 </div>
 <div id="stage">
  <canvas id="c" aria-label="3D syringe mascot"></canvas>
  <div id="bubble">Hi, I'm Jabby! Click me.</div>
  <div id="fb"><svg viewBox="0 0 120 240" xmlns="http://www.w3.org/2000/svg"><g transform="rotate(14 60 120)">
   <rect x="44" y="6" width="32" height="10" rx="5" fill="#E5384F"/><rect x="56" y="14" width="8" height="50" fill="#CFE3F7"/>
   <rect x="28" y="60" width="64" height="8" rx="4" fill="#EAF4FF" stroke="#B9D4EE"/>
   <rect x="34" y="66" width="52" height="112" rx="10" fill="#F4FAFF" stroke="#B9D4EE" stroke-width="3"/>
   <rect x="39" y="104" width="42" height="68" rx="7" fill="#1DB98A"/><rect x="39" y="92" width="42" height="14" fill="#0B4F9C"/>
   <circle cx="50" cy="128" r="5" fill="#fff"/><circle cx="70" cy="128" r="5" fill="#fff"/><circle cx="51" cy="129" r="2.4" fill="#0E2A47"/><circle cx="71" cy="129" r="2.4" fill="#0E2A47"/>
   <path d="M52 143 q8 8 16 0" stroke="#7A1A2B" stroke-width="3" fill="none" stroke-linecap="round"/>
   <path d="M50 178 L70 178 L64 196 L56 196 Z" fill="#0B4F9C"/><rect x="58.5" y="196" width="3" height="40" fill="#C9D6E3"/></g></svg></div>
 </div>
</div>
<script>
const DATA=__DATA__;
const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
const COLORS=['#1E6FD9','#1DB98A','#E5384F','#C6CB45'];
(function stats(){
 const box=document.getElementById('stats');
 DATA.stats.forEach((s,i)=>{
  const d=document.createElement('div');d.className='stat';d.style.setProperty('--c',COLORS[i%4]);d.style.animationDelay=(.25+i*.1)+'s';
  d.innerHTML='<b>0</b><span>'+s.label+'</span>';box.appendChild(d);
  const b=d.querySelector('b'),f=v=>(s.prefix||'')+new Intl.NumberFormat('en-US',{minimumFractionDigits:s.decimals,maximumFractionDigits:s.decimals}).format(v)+(s.suffix||'');
  if(reduce){b.textContent=f(s.value);return;}
  const t0=performance.now()+350+i*120,dur=1500;
  (function tick(n){const p=Math.min(Math.max((n-t0)/dur,0),1),e=1-Math.pow(1-p,3);b.textContent=f(s.value*e);if(p<1)requestAnimationFrame(tick);})(performance.now());
 });
})();
const bubble=document.getElementById('bubble');let msgI=0;
function say(t){bubble.style.animation='none';bubble.offsetHeight;bubble.textContent=t;bubble.style.animation='';}
function nextMsg(){const m=DATA.facts;if(!m.length)return;msgI=(msgI+1)%m.length;say(m[msgI]);}
function boot(){
 if(!window.THREE){document.body.classList.add('nogl');return;}
 if(window.__booted)return;window.__booted=true;
 const stage=document.getElementById('stage'),canvas=document.getElementById('c');
 let renderer;
 try{renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true,powerPreference:'high-performance'});}
 catch(e){document.body.classList.add('nogl');return;}
 let pr=Math.min(window.devicePixelRatio||1,1.5);renderer.setPixelRatio(pr);renderer.setClearColor(0x000000,0);
 const scene=new THREE.Scene();
 const camera=new THREE.PerspectiveCamera(30,1,.1,60);camera.position.set(0,0,12);
 scene.add(new THREE.HemisphereLight(0xffffff,0xbfd9f2,.8));
 const key=new THREE.DirectionalLight(0xffffff,.8);key.position.set(4,6,7);scene.add(key);
 const gl=new THREE.PointLight(0x1DB98A,.7,22);gl.position.set(-5,-2,5);scene.add(gl);
 const bl=new THREE.PointLight(0x1E6FD9,.6,22);bl.position.set(5,-3,4);scene.add(bl);
 const M=(c,o)=>new THREE.MeshStandardMaterial(Object.assign({color:c,roughness:.45,metalness:.05},o||{}));

 /* ---------- Jabby the syringe ---------- */
 const jabby=new THREE.Group(),body=new THREE.Group();jabby.add(body);
 const R=.62;
 const glass=new THREE.Mesh(new THREE.CylinderGeometry(R,R,2.6,40),new THREE.MeshPhysicalMaterial({color:0xdff1ff,transparent:true,opacity:.30,roughness:.05,metalness:0,clearcoat:1,clearcoatRoughness:.05,depthWrite:false}));
 glass.renderOrder=3;body.add(glass);
 const liquid=new THREE.Mesh(new THREE.CylinderGeometry(.54,.54,1.75,32),M(0x22C79A,{roughness:.25,emissive:0x0b7a5a,emissiveIntensity:.18}));liquid.position.y=-.325;body.add(liquid);
 const flange=new THREE.Mesh(new THREE.CylinderGeometry(R,R,.1,40),M(0xEAF4FF,{roughness:.4}));flange.scale.set(1.5,1,.55);flange.position.y=1.32;body.add(flange);
 const tip=new THREE.Mesh(new THREE.CylinderGeometry(.34,.12,.45,24),M(0xEAF4FF,{roughness:.3}));tip.position.y=-1.525;body.add(tip);
 const hub=new THREE.Mesh(new THREE.CylinderGeometry(.2,.2,.3,20),M(0x1E6FD9,{roughness:.3}));hub.position.y=-1.85;body.add(hub);
 const needle=new THREE.Mesh(new THREE.CylinderGeometry(.035,.018,1.4,10),M(0xD8E3EE,{metalness:.9,roughness:.2}));needle.position.y=-2.75;body.add(needle);
 const plunger=new THREE.Group();body.add(plunger);
 const head=new THREE.Mesh(new THREE.CylinderGeometry(.56,.56,.28,32),M(0x0B4F9C,{roughness:.55}));head.position.y=.7;plunger.add(head);
 [0.62,0.78].forEach(y=>{const r=new THREE.Mesh(new THREE.TorusGeometry(.56,.025,8,32),M(0x083F7D));r.rotation.x=Math.PI/2;r.position.y=y;plunger.add(r);});
 const rodA=new THREE.Mesh(new THREE.BoxGeometry(.34,1.4,.07),M(0xCFE3F7,{roughness:.4})),rodB=new THREE.Mesh(new THREE.BoxGeometry(.07,1.4,.34),M(0xCFE3F7,{roughness:.4}));
 rodA.position.y=rodB.position.y=1.52;plunger.add(rodA,rodB);
 const pad=new THREE.Mesh(new THREE.CylinderGeometry(.55,.55,.13,40),M(0xE5384F,{roughness:.35}));pad.position.y=2.26;plunger.add(pad);
 function onBarrel(m,x,y,off){const a=Math.asin(x/R);m.position.set(x,y,Math.cos(a)*R+off);m.rotation.y=a;return m;}
 const markMat=M(0x1E6FD9);for(let i=0;i<11;i++){const m=new THREE.Mesh(new THREE.BoxGeometry(i%2?.1:.17,.022,.03),markMat);onBarrel(m,.47,-1.1+i*.21,0);body.add(m);}
 /* face */
 const eyes=[],pupils=[];
 [-1,1].forEach(s=>{const g=new THREE.Group();
  const w=new THREE.Mesh(new THREE.SphereGeometry(.14,20,14),M(0xffffff,{roughness:.25}));w.scale.set(1,1.2,.45);g.add(w);
  const p=new THREE.Mesh(new THREE.SphereGeometry(.075,14,10),M(0x0E2A47,{roughness:.2}));p.position.set(0,-.01,.045);p.scale.z=.6;g.add(p);pupils.push(p);
  const h=new THREE.Mesh(new THREE.SphereGeometry(.02,8,6),new THREE.MeshBasicMaterial({color:0xffffff}));h.position.set(.025,.03,.075);g.add(h);
  onBarrel(g,s*.21,.2,.0);body.add(g);eyes.push(g);});
 const mouth=new THREE.Mesh(new THREE.TorusGeometry(.15,.026,8,20,Math.PI),new THREE.MeshBasicMaterial({color:0x7A1A2B}));mouth.rotation.z=Math.PI;onBarrel(mouth,0,-.1,.0);mouth.rotation.z=Math.PI;body.add(mouth);
 const cheekMat=new THREE.MeshBasicMaterial({color:0xFF8FA3,transparent:true,opacity:.55});const cheeks=[];
 [-1,1].forEach(s=>{const c=new THREE.Mesh(new THREE.CircleGeometry(.075,16),cheekMat);onBarrel(c,s*.36,-.04,.01);body.add(c);cheeks.push(c);});
 /* arms */
 function arm(side){const g=new THREE.Group();
  const u=new THREE.Mesh(new THREE.CylinderGeometry(.065,.065,.55,12),M(0xEAF4FF,{roughness:.5}));u.rotation.z=Math.PI/2;u.position.x=.28;
  const band=new THREE.Mesh(new THREE.TorusGeometry(.075,.025,8,16),M(0xE5384F));band.rotation.y=Math.PI/2;band.position.x=.5;
  const hd=new THREE.Mesh(new THREE.SphereGeometry(.12,16,12),M(0xffffff,{roughness:.4}));hd.position.x=.62;
  g.add(u,band,hd);g.position.set(side*.64,-.05,.05);g.scale.x=side;return g;}
 const armR=arm(1),armL=arm(-1);body.add(armR,armL);
 /* bubbles in the liquid + droplet */
 const bubMat=new THREE.MeshBasicMaterial({color:0xffffff,transparent:true,opacity:.55});
 const bubs=[];for(let i=0;i<7;i++){const m=new THREE.Mesh(new THREE.SphereGeometry(.03+Math.random()*.03,8,6),bubMat);const a=Math.random()*6.28,r=Math.random()*.38;m.userData={a,r,ph:Math.random(),sp:.12+Math.random()*.12};body.add(m);bubs.push(m);}
 const dropMat=new THREE.MeshBasicMaterial({color:0x1DB98A,transparent:true,opacity:1});const drop=new THREE.Mesh(new THREE.SphereGeometry(.07,10,8),dropMat);drop.scale.set(.7,1.1,.7);body.add(drop);
 body.position.y=.56;jabby.scale.setScalar(.94);jabby.rotation.z=-.28;scene.add(jabby);

 /* ---------- satellites ---------- */
 const sats=[];
 function pill(c1,c2,s){const g=new THREE.Group(),r=.2,L=.34,m1=M(c1,{roughness:.3}),m2=M(c2,{roughness:.3});
  const a=new THREE.Mesh(new THREE.CylinderGeometry(r,r,L,20),m1);a.position.y=L/2;
  const ca=new THREE.Mesh(new THREE.SphereGeometry(r,20,12,0,Math.PI*2,0,Math.PI/2),m1);ca.position.y=L;
  const b=new THREE.Mesh(new THREE.CylinderGeometry(r,r,L,20),m2);b.position.y=-L/2;
  const cb=new THREE.Mesh(new THREE.SphereGeometry(r,20,12,0,Math.PI*2,Math.PI/2,Math.PI/2),m2);cb.position.y=-L;
  g.add(a,ca,b,cb);g.scale.setScalar(s);return g;}
 function cross(c,s){const g=new THREE.Group(),m=M(c,{roughness:.35});g.add(new THREE.Mesh(new THREE.BoxGeometry(.5,.16,.16),m),new THREE.Mesh(new THREE.BoxGeometry(.16,.5,.16),m));g.scale.setScalar(s);return g;}
 function sat(o,x,y,z,sp,ph,sx,sy,sz){o.position.set(x,y,z);scene.add(o);sats.push({o,x,y,z,sp,ph,sx,sy,sz});}
 sat(pill(0xE5384F,0xffffff,1.1),-3.5,-.3,.4,1.0,0,.2,.4,.1);
 sat(pill(0x1E6FD9,0xffffff,.95),-3.0,-1.9,.6,.8,2,.3,.2,.4);
 sat(pill(0x1DB98A,0xffffff,.9),2.3,2.4,-.3,1.2,4,.4,.3,.2);
 sat(pill(0xCFCE5D,0x79C1B9,.8),2.5,-2.4,.5,.9,1,.2,.5,.3);
 sat(cross(0xE5384F,1),-4.1,1.3,0,1.1,3,0,.5,.3);
 sat(cross(0x1DB98A,.8),1.9,3.0,-.6,.9,5,.3,.4,0);
 sat(cross(0x1E6FD9,.7),-1.7,-2.9,.3,1.3,2,.2,.3,.5);
 sat(cross(0xCFCE5D,.6),4.4,-.4,-.4,1.0,0,.4,.2,.3);
 /* DNA helix */
 const helix=new THREE.Group();helix.position.set(3.9,.1,-.6);helix.rotation.z=.12;
 (function(){const N=26,HR=.45,sph=new THREE.SphereGeometry(.085,12,10),inst=new THREE.InstancedMesh(sph,M(0xffffff,{roughness:.35}),N*2),rg=new THREE.CylinderGeometry(.02,.02,HR*2,6),rungs=new THREE.InstancedMesh(rg,M(0xBFD8EE),N),d=new THREE.Object3D(),c=new THREE.Color();
  for(let i=0;i<N;i++){const a=i*.5,y=(i-N/2)*.2,x=Math.cos(a)*HR,z=Math.sin(a)*HR;
   d.rotation.set(0,0,0);d.position.set(x,y,z);d.updateMatrix();inst.setMatrixAt(2*i,d.matrix);inst.setColorAt(2*i,c.set(0x1E6FD9));
   d.position.set(-x,y,-z);d.updateMatrix();inst.setMatrixAt(2*i+1,d.matrix);inst.setColorAt(2*i+1,c.set(0x1DB98A));
   d.position.set(0,y,0);d.rotation.set(0,-a,Math.PI/2);d.updateMatrix();rungs.setMatrixAt(i,d.matrix);}
  inst.instanceMatrix.needsUpdate=true;inst.instanceColor.needsUpdate=true;rungs.instanceMatrix.needsUpdate=true;helix.add(inst,rungs);})();
 scene.add(helix);
 /* orbit ring */
 const ring=new THREE.Group();ring.add(new THREE.Mesh(new THREE.TorusGeometry(3.0,.012,8,120),new THREE.MeshBasicMaterial({color:0x1DB98A,transparent:true,opacity:.5})));
 const orb=new THREE.Mesh(new THREE.SphereGeometry(.09,12,10),new THREE.MeshBasicMaterial({color:0xE5384F}));ring.add(orb);ring.rotation.set(1.15,.2,0);scene.add(ring);
 /* particles */
 const cv=document.createElement('canvas');cv.width=cv.height=64;const cx=cv.getContext('2d'),gr=cx.createRadialGradient(32,32,0,32,32,32);gr.addColorStop(0,'rgba(255,255,255,1)');gr.addColorStop(1,'rgba(255,255,255,0)');cx.fillStyle=gr;cx.fillRect(0,0,64,64);
 const PN=140,pp=new Float32Array(PN*3),pc=new Float32Array(PN*3),pal=[0x1E6FD9,0x1DB98A,0xCFCE5D,0xE5384F,0x79C1B9],tc=new THREE.Color();
 for(let i=0;i<PN;i++){pp[i*3]=(Math.random()-.5)*12;pp[i*3+1]=(Math.random()-.5)*6.6;pp[i*3+2]=(Math.random()-.5)*5;tc.set(pal[i%5]);pc[i*3]=tc.r;pc[i*3+1]=tc.g;pc[i*3+2]=tc.b;}
 const pg=new THREE.BufferGeometry();pg.setAttribute('position',new THREE.BufferAttribute(pp,3));pg.setAttribute('color',new THREE.BufferAttribute(pc,3));
 const points=new THREE.Points(pg,new THREE.PointsMaterial({size:.12,map:new THREE.CanvasTexture(cv),transparent:true,depthWrite:false,vertexColors:true,opacity:.75}));scene.add(points);

 /* ---------- interaction ---------- */
 const ptr={x:0,y:0,tx:0,ty:0};let spinT=0,nextBlink=2,blink=0;
 addEventListener('pointermove',e=>{const r=stage.getBoundingClientRect();ptr.tx=Math.max(-1.4,Math.min(1.4,((e.clientX-r.left)/r.width-.5)*2));ptr.ty=Math.max(-1.2,Math.min(1.2,((e.clientY-r.top)/r.height-.5)*2));},{passive:true});
 addEventListener('pointerleave',()=>{ptr.tx=ptr.ty=0;});
 stage.addEventListener('pointerdown',()=>{if(spinT===0){spinT=.0001;nextMsg();}});

 function size(){const w=stage.clientWidth,h=stage.clientHeight;if(!w||!h)return;renderer.setSize(w,h,false);camera.aspect=w/h;camera.position.z=camera.aspect<1.35?12+(1.35-camera.aspect)*7:12;camera.updateProjectionMatrix();renderer.render(scene,camera);}
 new ResizeObserver(size).observe(stage);size();

 /* ---------- loop ---------- */
 let running=false,last=0,t=0,frames=0,fpsT=0,lowRuns=0,raf=0;
 const ease=x=>x<.5?2*x*x:1-Math.pow(-2*x+2,2)/2;
 function update(dt){
  t+=dt;ptr.x+=(ptr.tx-ptr.x)*Math.min(1,dt*5);ptr.y+=(ptr.ty-ptr.y)*Math.min(1,dt*5);
  let spin=0,hop=0;if(spinT>0){spinT+=dt/.95;if(spinT>=1){spinT=0;}else{spin=ease(spinT)*Math.PI*2;hop=Math.sin(spinT*Math.PI)*.7;}}
  jabby.position.y=Math.sin(t*1.4)*.12+hop;jabby.rotation.y=Math.sin(t*.6)*.22+ptr.x*.45+spin;jabby.rotation.x=ptr.y*.14;
  plunger.position.y=Math.sin(t*1.2)*.07;
  armR.rotation.z=.85+Math.sin(t*(spinT>0?12:6.5))*.38;armL.rotation.z=-.55+Math.sin(t*1.6)*.08;
  pupils.forEach(p=>{p.position.x=ptr.x*.03;p.position.y=-.01-ptr.y*.025;});
  nextBlink-=dt;if(nextBlink<=0){blink=.14;nextBlink=2.4+Math.random()*2.6;}
  if(blink>0){blink-=dt;const k=blink>.07?(blink-.07)/.07:(.07-blink)/.07+.0;const sy=Math.max(.08,Math.min(1,blink>.07?k:1-blink/.07));eyes.forEach(e=>e.scale.y=sy);}else eyes.forEach(e=>e.scale.y=1);
  cheekMat.opacity=.5+Math.sin(t*2)*.1+(spinT>0?.25:0);
  bubs.forEach(b=>{const u=b.userData,p=(t*u.sp+u.ph)%1;b.position.set(Math.cos(u.a+t*.4)*u.r,-1.15+p*1.35,Math.sin(u.a+t*.4)*u.r*.6);});
  const dp=(t%2.6)/2.6;drop.position.set(0,-3.42-dp*dp*.9,0);dropMat.opacity=dp<.12?0:1-dp*dp;drop.scale.set(.7*(1-dp*.4),1.1*(1-dp*.3),.7*(1-dp*.4));
  sats.forEach(s=>{const o=s.o;o.position.y=s.y+Math.sin(t*s.sp+s.ph)*.2;o.position.x=s.x+Math.cos(t*s.sp*.6+s.ph)*.08;o.rotation.x+=dt*s.sx;o.rotation.y+=dt*s.sy;o.rotation.z+=dt*s.sz;});
  helix.rotation.y+=dt*.7;
  ring.rotation.z+=dt*.25;orb.position.set(Math.cos(t*.9)*3.0,Math.sin(t*.9)*3.0,0);
  points.rotation.y=t*.02;points.position.y=Math.sin(t*.3)*.1;
 }
 function frame(now){
  if(!running)return;raf=requestAnimationFrame(frame);
  const dt=Math.min((now-last)/1000,.05);last=now;update(dt);renderer.render(scene,camera);
  frames++;fpsT+=dt;
  if(fpsT>=2){const fps=frames/fpsT;frames=0;fpsT=0;
   if(fps<30){lowRuns++;if(pr>1){pr=1;renderer.setPixelRatio(1);size();}else if(lowRuns>=2){points.visible=false;}}else lowRuns=0;}
 }
 function start(){if(running||reduce)return;running=true;last=performance.now();raf=requestAnimationFrame(frame);}
 function stop(){running=false;cancelAnimationFrame(raf);}
 let inView=true,tabOn=!document.hidden;
 function sync(){(inView&&tabOn)?start():stop();}
 new IntersectionObserver(es=>{inView=es[0].isIntersecting;sync();},{threshold:.01}).observe(stage);
 document.addEventListener('visibilitychange',()=>{tabOn=!document.hidden;sync();});
 canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();stop();document.body.classList.add('nogl');});
 canvas.addEventListener('webglcontextrestored',()=>{document.body.classList.remove('nogl');sync();});
 update(.016);renderer.render(scene,camera);sync();
}
setInterval(()=>{if(DATA.facts.length&&!document.hidden&&!window.__held)nextMsg();},9000);
</script>
<script src="__PRIMARY__" onload="boot()" onerror="this.onerror=null;var s=document.createElement('script');s.src='__BACKUP__';s.onload=boot;s.onerror=function(){document.body.classList.add('nogl')};document.head.appendChild(s)"></script>
</body></html>"""


def hero_html(data: dict) -> str:
    """Return the hero document. `data` holds the stat cards and the speech-bubble facts."""
    payload = json.dumps(data).replace("</", "<\\/")
    return _HTML.replace("__DATA__", payload).replace("__PRIMARY__", THREE_PRIMARY).replace("__BACKUP__", THREE_BACKUP)
