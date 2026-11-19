"""One persistent 3D hospital world for the whole dashboard (Three.js r128).

The world lives in a full-screen, click-through iframe behind the page. Each page leaves a transparent
"scene window" (#scene-window) and the world draws itself inside that rectangle, so it scrolls with the page.
The page name is read from a hidden marker (#page-marker); when it changes the camera flies to the next scene:

  Summary           hospital exterior (ambulance, helipad, entrance)
  Patient Analysis  scanner room (CT gantry, patient bed, hologram)
  Cost Analysis     reception and billing counter
  Hospital Analysis rotating globe with hospital pins (drag to spin)
  Data Quality      clean interior corridor with patient rooms

Performance: one renderer, scenes outside the camera range are hidden, rendering pauses when the window is
off screen or the tab is hidden, pixel ratio is capped, and quality drops automatically if fps falls under 30.
If WebGL or the CDN is blocked, the window shows a plain gradient and the dashboard works as normal.
"""
from __future__ import annotations

import json

THREE_PRIMARY = "https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"
THREE_BACKUP = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"
EARTH_TEXTURE = "https://cdn.jsdelivr.net/gh/mrdoob/three.js@r128/examples/textures/planets/earth_atmos_2048.jpg"

# approximate centres of New York State counties (lat, lon) for the globe pins
COUNTY_LATLON = {
    "New York": (40.78, -73.97), "Manhattan": (40.78, -73.97), "Kings": (40.65, -73.95), "Queens": (40.73, -73.80),
    "Bronx": (40.85, -73.87), "Richmond": (40.58, -74.15), "Nassau": (40.73, -73.59), "Suffolk": (40.92, -72.67),
    "Westchester": (41.12, -73.79), "Rockland": (41.15, -74.02), "Orange": (41.40, -74.31), "Dutchess": (41.76, -73.74),
    "Albany": (42.65, -73.76), "Rensselaer": (42.71, -73.51), "Schenectady": (42.82, -73.94), "Saratoga": (43.11, -73.86),
    "Erie": (42.88, -78.88), "Niagara": (43.17, -78.69), "Monroe": (43.16, -77.61), "Onondaga": (43.05, -76.15),
    "Broome": (42.16, -75.82), "Oneida": (43.24, -75.44), "Clinton": (44.70, -73.45), "Columbia": (42.25, -73.63),
    "Ulster": (41.93, -74.26), "Jefferson": (44.00, -75.91), "Tompkins": (42.45, -76.47), "Chautauqua": (42.30, -79.40),
}

_HTML = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:transparent;overflow:hidden;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif}
#stage{position:absolute;display:none;overflow:hidden;border-radius:24px;left:0;top:0;width:10px;height:10px;background:#EAF4FF}
.sky{position:absolute;inset:0;opacity:0;transition:opacity 1.1s ease}.sky.on{opacity:1}
#s0{background:linear-gradient(#7FBFFF 0%,#BFE0FF 48%,#F2FAFF 100%)}
#s1{background:linear-gradient(#D7E8F8,#F4F9FC)}
#s2{background:linear-gradient(#DDF1E8,#F8FCFA)}
#s3{background:radial-gradient(circle at 62% 48%,#CFE4FF 0%,#E3F4EE 55%,#F7FCFE 100%)}
#s4{background:linear-gradient(#DDF6EC,#F3FBF9)}
canvas{position:absolute;inset:0;width:100%;height:100%;display:block;outline:none}
#streaks{position:absolute;inset:-20%;pointer-events:none;opacity:0;background:repeating-conic-gradient(from 0deg at 50% 50%,rgba(255,255,255,0) 0 3deg,rgba(255,255,255,.75) 3.3deg 3.7deg,rgba(255,255,255,0) 4deg 7deg);-webkit-mask-image:radial-gradient(circle,transparent 18%,#000 75%);mask-image:radial-gradient(circle,transparent 18%,#000 75%)}
#flash{position:absolute;inset:0;pointer-events:none;opacity:0;background:radial-gradient(circle,rgba(255,255,255,.0) 20%,rgba(255,255,255,.85) 100%)}
#bubble{position:absolute;right:3%;top:10px;max-width:250px;background:#fff;border:1px solid #DDEBF5;border-radius:16px;padding:10px 13px;font-size:13px;line-height:1.4;font-weight:600;color:#0E2A47;box-shadow:0 10px 26px rgba(14,42,71,.14);pointer-events:none;animation:pop .45s cubic-bezier(.2,1.4,.4,1) both;z-index:3}
#bubble::after{content:"";position:absolute;right:46px;bottom:-7px;width:12px;height:12px;background:#fff;border-right:1px solid #DDEBF5;border-bottom:1px solid #DDEBF5;transform:rotate(45deg)}
@keyframes pop{from{opacity:0;transform:translateY(8px) scale(.9)}to{opacity:1;transform:none}}
#load{position:absolute;left:18px;bottom:14px;font-size:12px;font-weight:700;color:#0B4F9C;letter-spacing:.12em;opacity:.8;z-index:3;transition:opacity .6s}
.nogl canvas,.nogl #bubble{display:none}
@media (max-width:640px){#bubble{max-width:170px;font-size:12px;padding:8px 10px}}
</style></head><body>
<div id="stage">
 <div class="sky on" id="s0"></div><div class="sky" id="s1"></div><div class="sky" id="s2"></div><div class="sky" id="s3"></div><div class="sky" id="s4"></div>
 <canvas id="c" aria-label="3D hospital scene"></canvas>
 <div id="streaks"></div><div id="flash"></div>
 <div id="bubble">Hi, I'm Jabby! Click me.</div>
 <div id="load">LOADING THE HOSPITAL</div>
</div>
<script>
const DATA=__DATA__;
const PAGES=['Summary','Patient Analysis','Cost Analysis','Hospital Analysis','Data Quality'];
const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
const $=id=>document.getElementById(id);
let pd=null;try{pd=window.parent.document;void pd.body;}catch(e){pd=null;}
let tipI=0,pageI=0;
function tipsFor(i){return (DATA.tips[PAGES[i]]||[]).concat(i===0?DATA.facts:[]);}
function say(t){const b=$('bubble');b.style.animation='none';b.offsetHeight;b.textContent=t;b.style.animation='';}
function nextTip(){const l=tipsFor(pageI);if(!l.length)return;tipI=(tipI+1)%l.length;say(l[tipI]);}
function boot(){
 if(!window.THREE){document.body.classList.add('nogl');$('load').style.display='none';return;}
 if(window.__booted)return;window.__booted=true;
 const stage=$('stage'),canvas=$('c');
 let renderer;try{renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true,powerPreference:'high-performance'});}
 catch(e){document.body.classList.add('nogl');$('load').style.display='none';return;}
 let pr=Math.min(devicePixelRatio||1,1.5);renderer.setPixelRatio(pr);renderer.setClearColor(0x000000,0);
 const scene=new THREE.Scene();scene.fog=new THREE.Fog(0xEAF4FF,70,230);
 const camera=new THREE.PerspectiveCamera(44,2,.1,260);scene.add(camera);
 scene.add(new THREE.HemisphereLight(0xffffff,0xbfd9f2,.62));scene.add(new THREE.AmbientLight(0xffffff,.3));
 const sun=new THREE.DirectionalLight(0xffffff,.6);sun.position.set(30,50,40);scene.add(sun);
 /* ---------- helpers ---------- */
 const M=(c,o)=>new THREE.MeshStandardMaterial(Object.assign({color:c,roughness:.55,metalness:.05},o||{}));
 const MB=(c,o)=>new THREE.MeshBasicMaterial(Object.assign({color:c},o||{}));
 function box(p,w,h,d,m,x,y,z){const o=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),m);o.position.set(x||0,y||0,z||0);p.add(o);return o;}
 function cyl(p,rt,rb,h,m,x,y,z,seg){const o=new THREE.Mesh(new THREE.CylinderGeometry(rt,rb,h,seg||20),m);o.position.set(x||0,y||0,z||0);p.add(o);return o;}
 function sph(p,r,m,x,y,z){const o=new THREE.Mesh(new THREE.SphereGeometry(r,20,14),m);o.position.set(x||0,y||0,z||0);p.add(o);return o;}
 function plane(p,w,h,m,x,y,z,rx){const o=new THREE.Mesh(new THREE.PlaneGeometry(w,h),m);o.position.set(x||0,y||0,z||0);if(rx)o.rotation.x=rx;p.add(o);return o;}
 function ctex(w,h,fn){const c=document.createElement('canvas');c.width=w;c.height=h;const x=c.getContext('2d');fn(x,w,h);const t=new THREE.CanvasTexture(c);t.anisotropy=4;return {t,c,x,w,h};}
 function rr(x,a,b,w,h,r){x.beginPath();x.moveTo(a+r,b);x.arcTo(a+w,b,a+w,b+h,r);x.arcTo(a+w,b+h,a,b+h,r);x.arcTo(a,b+h,a,b,r);x.arcTo(a,b,a+w,b,r);x.closePath();}
 function floor(p,w,d,c,y){const f=plane(p,w,d,M(c,{roughness:.25,metalness:.1}),0,y||0,0,-Math.PI/2);return f;}
 function label(text,w,h,bg,fg,size){return ctex(w,h,(x,W,H)=>{x.fillStyle=bg;rr(x,0,0,W,H,H*.2);x.fill();x.fillStyle=fg;x.font='800 '+(size||H*.5)+'px Segoe UI,Arial';x.textAlign='center';x.textBaseline='middle';x.fillText(text,W/2,H/2+2);});}
 function person(skin,suit){const g=new THREE.Group(),sm=M(skin,{roughness:.6}),um=M(suit,{roughness:.6});
  cyl(g,.16,.14,1.1,um,-.2,-.55,0,12);cyl(g,.16,.14,1.1,um,.2,-.55,0,12);
  cyl(g,.34,.4,1.0,um,0,.5,0,18);sph(g,.3,sm,0,1.3,0);
  const mk=s=>{const a=new THREE.Group();a.position.set(s*.5,.9,0);cyl(a,.09,.08,.8,um,0,-.4,0,10);sph(a,.1,sm,0,-.82,0);g.add(a);return a;};
  const aL=mk(-1),aR=mk(1);return {g,aL,aR};}
 const SETS=[];let cur=null;
 function newSet(x){const g=new THREE.Group();g.position.x=x;scene.add(g);const s={g,x,tick:null};SETS.push(s);return s;}
 function ceilLights(p,n,w,d,y,z0,dz){for(let i=0;i<n;i++)box(p,w,.12,d,MB(0xffffff),0,y,z0+i*dz);}

 /* ================= 0. HOSPITAL EXTERIOR ================= */
 (function(){const S=newSet(0),g=S.g;
  const lawn=plane(g,170,130,M(0x8ED3A2,{roughness:1}),0,0,-10,-Math.PI/2);
  plane(g,30,11,M(0xEAF1F7,{roughness:.8}),0,.03,8.5,-Math.PI/2);
  plane(g,170,6,M(0x5B6B7E,{roughness:.9}),0,.04,17,-Math.PI/2);
  for(let i=0;i<22;i++)box(g,2,.02,.25,MB(0xffffff),-42+i*4,.06,17);
  function facade(cols,rows,w,h){return ctex(512,Math.round(512*h/w),(x,W,H)=>{x.fillStyle='#F7FBFF';x.fillRect(0,0,W,H);const mx=W*.05,my=H*.06,cw=(W-2*mx)/cols,ch=(H-2*my)/rows;
    for(let r=0;r<rows;r++)for(let c=0;c<cols;c++){const a=mx+c*cw+cw*.12,b=my+r*ch+ch*.14,ww=cw*.76,hh=ch*.72,gr=x.createLinearGradient(a,b,a,b+hh);gr.addColorStop(0,'#B5D8F8');gr.addColorStop(1,'#5F9FE4');x.fillStyle=gr;rr(x,a,b,ww,hh,6);x.fill();x.fillStyle='rgba(255,255,255,.28)';x.beginPath();x.moveTo(a,b+hh*.7);x.lineTo(a+ww*.55,b);x.lineTo(a+ww*.8,b);x.lineTo(a+ww*.1,b+hh);x.fill();x.strokeStyle='rgba(255,255,255,.9)';x.lineWidth=3;x.beginPath();x.moveTo(a+ww/2,b);x.lineTo(a+ww/2,b+hh);x.stroke();}});}
  function wing(w,h,d,x,y,cols,rows){const m=M(0xF7FBFF,{roughness:.5});box(g,w,h,d,m,x,y,0);const f=facade(cols,rows,w,h);plane(g,w,h,M(0xffffff,{map:f.t,roughness:.35,metalness:.1}),x,y,d/2+.02);box(g,w+.4,.4,d+.4,M(0x1E6FD9),x,y+h/2+.2,0);}
  wing(11,7,5.5,-10,3.5,6,3);wing(11,7,5.5,10,3.5,6,3);wing(7.4,11.5,6,0,5.75,4,5);
  /* red cross sign */
  const cr=new THREE.Group();cr.position.set(0,13.8,1);const rm=M(0xE5384F,{emissive:0xE5384F,emissiveIntensity:.55,roughness:.4});box(cr,3.2,1,.8,rm);box(cr,1,3.2,.8,rm);g.add(cr);
  /* sign + canopy + doors */
  const sg=label('MEDISCOPE HOSPITAL',1024,160,'#0B4F9C','#FFFFFF',90);plane(g,7,1.1,MB(0xffffff,{map:sg.t}),0,4.6,3.06);
  box(g,8,.3,3.2,M(0xFFFFFF),0,3.4,4.5);box(g,8,.12,3.25,M(0x1DB98A),0,3.22,4.5);
  [-3.6,3.6].forEach(x=>cyl(g,.18,.18,3.3,M(0xDDE8F2),x,1.65,5.8,12));
  const gm=M(0x9CD0F5,{transparent:true,opacity:.45,roughness:.1,metalness:.2});const dL=box(g,1.6,2.8,.08,gm,-.85,1.5,3.1),dR=box(g,1.6,2.8,.08,gm,.85,1.5,3.1);box(g,3.5,.15,.15,M(0x0B4F9C),0,2.95,3.12);
  /* helipad */
  cyl(g,2.1,2.1,.14,M(0x4B5D73),-10,7.1,0,40);const hp=ctex(256,256,(x,W)=>{x.clearRect(0,0,W,W);x.strokeStyle='#CFCE5D';x.lineWidth=14;x.beginPath();x.arc(128,128,108,0,7);x.stroke();x.fillStyle='#CFCE5D';x.font='900 150px Arial';x.textAlign='center';x.textBaseline='middle';x.fillText('H',128,138);});
  plane(g,4,4,MB(0xffffff,{map:hp.t,transparent:true}),-10,7.2,0,-Math.PI/2);const beacon=sph(g,.14,MB(0xE5384F),-7.9,7.4,2.2);
  /* trees, lamps */
  const trees=[];function tree(x,z,s){const t=new THREE.Group();t.position.set(x,0,z);t.scale.setScalar(s);cyl(t,.18,.22,1.3,M(0x8B6B4A),0,.65,0,8);const c1=new THREE.Mesh(new THREE.ConeGeometry(1.2,2.6,10),M(0x3FAE7C,{roughness:.8}));c1.position.y=2.3;const c2=new THREE.Mesh(new THREE.ConeGeometry(.9,2,10),M(0x5BC896,{roughness:.8}));c2.position.y=3.4;t.add(c1,c2);g.add(t);trees.push({t,ph:Math.random()*6});}
  [[-24,2],[-28,10],[-21,12],[24,2],[28,9],[21,12],[-34,4],[34,5],[-18,-12],[-8,-14],[8,-14],[18,-12],[-26,-6],[27,-7]].forEach((p,i)=>tree(p[0],p[1],.9+(i%4)*.18));
  for(let i=0;i<6;i++){const x=-12.5+i*5;cyl(g,.07,.09,3,M(0x6C7D90),x,1.5,12.8,8);sph(g,.2,MB(0xFFF2B0),x,3.1,12.8);}
  /* ambulance */
  const amb=new THREE.Group();box(amb,3.2,1.4,1.5,M(0xFFFFFF),0,.95,0);box(amb,1.2,1,1.45,M(0xF0F6FC),1.95,.75,0);box(amb,3.2,.2,1.52,M(0xE5384F),0,.8,0);box(amb,1.2,.45,1.46,M(0x7FB2F0,{transparent:true,opacity:.8}),2.0,1.0,0);
  box(amb,.9,.28,.04,M(0xE5384F),-.2,1.25,.77);box(amb,.28,.9,.04,M(0xE5384F),-.2,1.25,.77);
  [[-1.1,.74],[1.1,.74],[-1.1,-.74],[1.1,-.74],[2.1,.74],[2.1,-.74]].slice(0,4).forEach(p=>{const w=cyl(amb,.38,.38,.25,M(0x2B3A4D),p[0],.38,p[1],16);w.rotation.x=Math.PI/2;});
  const lb1=box(amb,.4,.18,.4,MB(0xE5384F),-.5,1.75,0),lb2=box(amb,.4,.18,.4,MB(0x1E6FD9),.1,1.75,0);amb.position.set(-30,0,15.2);g.add(amb);
  /* clouds + sun */
  const clouds=[];for(let i=0;i<7;i++){const c=new THREE.Group();[[0,0,0,2],[2,.3,0,1.6],[-2,.2,.3,1.5],[.8,1,0,1.5]].forEach(a=>{const s=sph(c,a[3],MB(0xffffff,{transparent:true,opacity:.92}),a[0],a[1],a[2]);s.scale.y=.6;});c.position.set(-60+i*20,16+(i%3)*4,-30-(i%2)*10);g.add(c);clouds.push(c);}
  const sc=ctex(128,128,(x)=>{const gr=x.createRadialGradient(64,64,0,64,64,64);gr.addColorStop(0,'rgba(255,250,200,1)');gr.addColorStop(.4,'rgba(255,240,160,.5)');gr.addColorStop(1,'rgba(255,240,160,0)');x.fillStyle=gr;x.fillRect(0,0,128,128);});
  const sp=new THREE.Sprite(new THREE.SpriteMaterial({map:sc.t,blending:THREE.AdditiveBlending,depthWrite:false,fog:false}));sp.scale.set(40,40,1);sp.position.set(-30,28,-50);g.add(sp);
  let bl=0;
  S.tick=(t,dt,lowq)=>{amb.position.x=-30+((t*4)%62);amb.children.forEach(c=>{if(c.geometry&&c.geometry.type==='CylinderGeometry')c.rotation.z+=0;});
   bl+=dt;if(bl>.25){bl=0;const a=Math.floor(t*4)%2;lb1.material.color.set(a?0xE5384F:0x551020);lb2.material.color.set(a?0x102a55:0x1E6FD9);}
   beacon.material.color.set((Math.floor(t*2)%2)?0xE5384F:0x6b1a26);cr.rotation.y=Math.sin(t*.8)*.25;cr.position.y=13.8+Math.sin(t*1.6)*.15;
   const o=Math.sin(t*.7)*.5+.5;dL.position.x=-.85-o*.6;dR.position.x=.85+o*.6;
   trees.forEach(a=>a.t.rotation.z=Math.sin(t*.9+a.ph)*.025);clouds.forEach((c,i)=>{c.position.x+=dt*(.5+i*.08);if(c.position.x>70)c.position.x=-70;});};
 })();

 /* ================= 1. SCANNER ROOM ================= */
 (function(){const S=newSet(60),g=S.g;
  floor(g,34,26,0xD3E2EE);plane(g,34,10,M(0xF6FAFD),0,5,-10);plane(g,26,10,M(0xEEF5FA),-17,5,0).rotation.y=Math.PI/2;plane(g,26,10,M(0xEEF5FA),17,5,0).rotation.y=-Math.PI/2;
  plane(g,34,26,M(0xFFFFFF),0,10,0,Math.PI/2);box(g,34,.5,.3,M(0x1DB98A),0,1.2,-9.9);box(g,34,.18,.3,M(0x1E6FD9),0,1.6,-9.9);
  ceilLights(g,3,10,1.2,9.85,-4,5);
  /* big back window with city blur */
  plane(g,12,4,MB(0xCFE6FA),-8,5.5,-9.85);box(g,12.3,.2,.2,M(0xffffff),-8,7.6,-9.8);box(g,12.3,.2,.2,M(0xffffff),-8,3.4,-9.8);box(g,.2,4.2,.2,M(0xffffff),-8,5.5,-9.8);
  /* gantry */
  const gz=-1.5,gan=new THREE.Group();gan.position.set(0,3.1,gz);g.add(gan);
  const ring=new THREE.Mesh(new THREE.TorusGeometry(2.7,.75,28,72),M(0xFFFFFF,{roughness:.2,metalness:.15}));gan.add(ring);
  const bore=new THREE.Mesh(new THREE.CylinderGeometry(2.0,2.0,1.6,48,1,true),M(0x2A4A6B,{side:THREE.BackSide,roughness:.6}));bore.rotation.x=Math.PI/2;gan.add(bore);
  const gl=new THREE.Mesh(new THREE.TorusGeometry(2.05,.07,10,72),MB(0x1DB98A));gl.position.z=.82;gan.add(gl);
  const stripe=new THREE.Mesh(new THREE.TorusGeometry(2.7,.1,10,72),M(0x1E6FD9));stripe.position.z=.78;gan.add(stripe);
  box(g,1.2,2.2,1.6,M(0xE3EDF6),-3.2,1.1,gz);box(g,1.2,2.2,1.6,M(0xE3EDF6),3.2,1.1,gz);
  const dsp=label('SCANNING',512,128,'#0E2A47','#1DB98A',70);plane(gan,2.6,.65,MB(0xffffff,{map:dsp.t}),0,3.2,.9);
  /* bed + patient */
  const bed=new THREE.Group();g.add(bed);box(bed,1.5,.24,7.4,M(0x7FA6CF,{roughness:.4}),0,1.55,0);box(bed,.8,1.2,1.2,M(0xC9D8E6),0,.8,2.4);box(bed,1.7,.12,1.6,M(0xE5384F),0,.6,2.4);
  const pt=person(0xF2C9A5,0x79C1B9);pt.g.rotation.x=-Math.PI/2;pt.g.position.set(0,1.95,.2);bed.add(pt.g);pt.aL.rotation.z=.12;pt.aR.rotation.z=-.12;
  const scan=new THREE.Mesh(new THREE.CircleGeometry(1.95,40),new THREE.MeshBasicMaterial({color:0x1DB98A,transparent:true,opacity:.18,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide}));scan.position.set(0,3.1,gz+.4);g.add(scan);
  /* hologram */
  cyl(g,1.1,1.3,.3,M(0xDCE9F5),-9,.15,3,32);cyl(g,.9,.9,.06,MB(0x1DB98A),-9,.35,3,32);
  const holo=new THREE.Group();holo.position.set(-9,2.3,3);g.add(holo);const hp=person(0x7FD0F0,0x7FD0F0);hp.g.traverse(o=>{if(o.isMesh){o.material=new THREE.MeshBasicMaterial({color:0x1E9BE0,wireframe:true,transparent:true,opacity:.75});}});hp.g.position.y=.6;holo.add(hp.g);
  const hring=new THREE.Mesh(new THREE.TorusGeometry(.9,.03,8,48),MB(0x1DB98A));hring.rotation.x=Math.PI/2;holo.add(hring);
  /* monitors */
  const mons=[];for(let i=0;i<3;i++){const m=new THREE.Group();m.position.set(7.2+i*2.1,2.9,-4.2);m.rotation.y=-.5;box(m,1.9,1.3,.12,M(0x24384D));const sc=ctex(256,160,()=>{});plane(m,1.74,1.14,MB(0xffffff,{map:sc.t}),0,0,.07);box(m,.12,.8,.12,M(0x6C7D90),0,-1.0,0);g.add(m);mons.push(sc);}
  box(g,7,.2,2.4,M(0xDCE6F0),9.4,1.7,-4.2);box(g,6.6,1.6,2,M(0xF6FAFD),9.4,.8,-4.2);
  /* IV stand + equipment */
  cyl(g,.05,.05,3.6,M(0xB8C6D4),-12,1.8,1,8);cyl(g,.5,.5,.08,M(0xB8C6D4),-12,.05,1,16);box(g,.7,.9,.2,M(0xE5384F,{transparent:true,opacity:.75}),-12,3.3,1);
  cyl(g,.04,.04,3.2,MB(0xE5384F),-11.5,1.7,1.25,6).rotation.z=.05;
  const gring=new THREE.Mesh(new THREE.RingGeometry(5.8,6.0,64),MB(0x1DB98A,{side:THREE.DoubleSide,transparent:true,opacity:.6}));gring.rotation.x=-Math.PI/2;gring.position.set(0,.03,.2);g.add(gring);
  let fr=0;
  S.tick=(t,dt,lowq)=>{const k=Math.sin(t*.55);bed.position.z=1.4+k*2.4;scan.material.opacity=.12+Math.abs(Math.sin(t*3))*.18;gl.scale.setScalar(1+Math.sin(t*4)*.015);
   holo.rotation.y=t*.9;hring.position.y=Math.sin(t*1.2)*1.6+.7;pt.aR.rotation.x=Math.sin(t*2)*.03;
   fr++;if(fr%3===0&&!lowq)mons.forEach((m,i)=>{const x=m.x,W=m.w,H=m.h;x.fillStyle='#08151F';x.fillRect(0,0,W,H);
    if(i===0){x.strokeStyle='#1DB98A';x.lineWidth=3;x.beginPath();for(let a=0;a<W;a++){const p=((a+t*120)%90)/90;let y=H*.55;if(p>.35&&p<.4)y-=H*.12;else if(p>.4&&p<.46)y+=H*.38;else if(p>.46&&p<.5)y-=H*.34;else if(p>.5&&p<.52)y+=H*.04;if(a===0)x.moveTo(a,y);else x.lineTo(a,y);}x.stroke();}
    else if(i===1){for(let b=0;b<9;b++){const h=(Math.sin(t*2+b*.8)*.5+.5)*H*.6+10;x.fillStyle=b%2?'#1E9BE0':'#1DB98A';x.fillRect(14+b*26,H-h-10,18,h);}}
    else{x.strokeStyle='#E5384F';x.lineWidth=3;x.beginPath();x.arc(W/2,H/2,40+Math.sin(t*3)*6,0,7);x.stroke();x.fillStyle='#fff';x.font='700 34px Arial';x.textAlign='center';x.fillText(Math.round(72+Math.sin(t*3)*4)+' bpm',W/2,H/2+12);}
    m.t.needsUpdate=true;});};
 })();

 /* ================= 2. RECEPTION / BILLING ================= */
 (function(){const S=newSet(120),g=S.g;
  floor(g,36,26,0xD6E8DF);plane(g,36,10,M(0xF8FCFA),0,5,-10);plane(g,26,10,M(0xEEF6F1),-18,5,0).rotation.y=Math.PI/2;plane(g,26,10,M(0xEEF6F1),18,5,0).rotation.y=-Math.PI/2;plane(g,36,26,M(0xFFFFFF),0,10,0,Math.PI/2);
  box(g,36,.5,.3,M(0x1E6FD9),0,1.1,-9.9);ceilLights(g,3,12,1.2,9.85,-6,5);
  const sg=label('RECEPTION & BILLING',1024,220,'#0B4F9C','#FFFFFF',78);plane(g,12,2.6,MB(0xffffff,{map:sg.t}),0,7.4,-9.8);
  const tk=ctex(256,128,()=>{});const tkp=plane(g,4,2,MB(0xffffff,{map:tk.t}),10.5,6.2,-9.8);
  /* counter */
  const ct=new THREE.Group();g.add(ct);box(ct,12,1.7,1.4,M(0x1E6FD9,{roughness:.35}),0,.85,0);box(ct,12.6,.22,1.9,M(0xFFFFFF,{roughness:.2}),0,1.8,.1);box(ct,12.1,.1,.1,MB(0x1DB98A),0,.18,.72);
  box(ct,3,.25,.9,M(0x1DB98A,{emissive:0x1DB98A,emissiveIntensity:.35}),-3.5,1.95,.2);
  /* receptionist */
  const rp=person(0xF0C4A0,0x1E6FD9);rp.g.position.set(1.8,1.35,-1.7);rp.g.children.slice(0,2).forEach(o=>o.visible=false);g.add(rp.g);
  const hair=new THREE.Mesh(new THREE.SphereGeometry(.33,18,12,0,Math.PI*2,0,Math.PI/1.7),M(0x4A3426));hair.position.set(0,1.36,-.02);rp.g.add(hair);
  const hs=new THREE.Mesh(new THREE.TorusGeometry(.32,.03,8,20,Math.PI),MB(0x0E2A47));hs.position.set(0,1.38,0);rp.g.add(hs);
  rp.aL.rotation.x=-1.1;rp.aR.rotation.x=-1.1;
  /* screens */
  const inv=ctex(256,160,()=>{});const mn=new THREE.Group();mn.position.set(.3,2.9,-1.2);box(mn,2.2,1.4,.1,M(0x24384D));plane(mn,2.04,1.24,MB(0xffffff,{map:inv.t}),0,0,.06);box(mn,.2,.8,.12,M(0x6C7D90),0,-1,0);g.add(mn);
  box(g,.9,.5,.6,M(0x24384D),-2.4,2.17,.2);box(g,.7,.04,.4,MB(0x1DB98A),-2.4,2.45,.2);
  /* floating coin + invoices */
  const coinTex=ctex(128,128,(x)=>{x.fillStyle='#E7E36B';x.fillRect(0,0,128,128);x.strokeStyle='#A3A72A';x.lineWidth=8;x.beginPath();x.arc(64,64,52,0,7);x.stroke();x.fillStyle='#8C8F1E';x.font='900 80px Arial';x.textAlign='center';x.textBaseline='middle';x.fillText('$',64,70);});
  const coin=new THREE.Mesh(new THREE.CylinderGeometry(1.2,1.2,.22,40),[M(0xCFCE5D,{metalness:.5,roughness:.3}),MB(0xffffff,{map:coinTex.t}),MB(0xffffff,{map:coinTex.t})]);coin.position.set(-6,4.2,2);coin.rotation.x=Math.PI/2.4;g.add(coin);
  const cs=[];for(let i=0;i<5;i++){const c=cyl(g,.7,.7,.16,M(0xCFCE5D,{metalness:.5,roughness:.3}),-9.5,.1+i*.17,3.5,28);}
  const invs=[];for(let i=0;i<4;i++){const t=ctex(256,340,(x,W,H)=>{x.fillStyle='#fff';x.fillRect(0,0,W,H);x.fillStyle='#0B4F9C';x.fillRect(0,0,W,50);x.fillStyle='#fff';x.font='800 28px Arial';x.fillText('INVOICE',14,35);x.fillStyle='#C8D6E6';for(let l=0;l<9;l++)x.fillRect(16,76+l*26,l%3===2?120:210,10);x.strokeStyle='#1DB98A';x.lineWidth=8;x.beginPath();x.moveTo(170,270);x.lineTo(196,296);x.lineTo(236,244);x.stroke();});
   const m=new THREE.Mesh(new THREE.PlaneGeometry(1.5,2),MB(0xffffff,{map:t.t,side:THREE.DoubleSide}));m.position.set(4+i*2.2,4.4+(i%2)*.8,3.4);g.add(m);invs.push({m,ph:i*1.3});}
  /* queue + chairs + plants */
  for(let i=0;i<4;i++){const x=-4+i*3;cyl(g,.06,.06,1.3,M(0x6C7D90),x,.65,6,8);cyl(g,.3,.3,.08,M(0x6C7D90),x,.04,6,14);sph(g,.12,M(0xE5384F),x,1.35,6);}
  for(let i=0;i<3;i++){const r=cyl(g,.03,.03,2.9,M(0xE5384F),-2.5+i*3,1.1,6,6);r.rotation.z=Math.PI/2;}
  for(let i=0;i<5;i++){const x=-15+i*1.9;box(g,1.5,.3,1.4,M(0x79C1B9),x,.7,-7);box(g,1.5,1.0,.2,M(0x5BA9A0),x,1.25,-7.6);box(g,.1,.7,.1,M(0xB8C6D4),x,.35,-7);}
  [-16,16].forEach(x=>{cyl(g,.6,.45,.9,M(0xDCE9F5),x,.45,-8,16);for(let k=0;k<5;k++)sph(g,.55,M(0x3FAE7C,{roughness:.8}),x+(k%2?.35:-.35),1.2+k*.22,-8+(k%3-1)*.2);});
  let fr=3,tok=41,tt=0;
  S.tick=(t,dt,lowq)=>{coin.rotation.z=t*1.4;coin.position.y=4.2+Math.sin(t*1.3)*.25;rp.aR.rotation.x=-1.1+Math.sin(t*9)*.07;rp.aL.rotation.x=-1.1+Math.sin(t*9+2)*.07;rp.g.rotation.y=Math.sin(t*.5)*.15;
   invs.forEach(a=>{a.m.position.y=4.4+Math.sin(t*1.1+a.ph)*.25+(invs.indexOf(a)%2)*.8;a.m.rotation.y=Math.sin(t*.6+a.ph)*.5;});
   tt+=dt;if(tt>3){tt=0;tok++;}
   fr++;if(fr%4===0&&!lowq){const x=tk.x;x.fillStyle='#08151F';x.fillRect(0,0,256,128);x.fillStyle='#CFCE5D';x.font='700 22px Arial';x.textAlign='center';x.fillText('NOW SERVING',128,36);x.fillStyle='#1DB98A';x.font='900 64px Arial';x.fillText(String(tok),128,100);tk.t.needsUpdate=true;
    const y=inv.x;y.fillStyle='#FFFFFF';y.fillRect(0,0,256,160);y.fillStyle='#0B4F9C';y.fillRect(0,0,256,26);y.fillStyle='#fff';y.font='700 16px Arial';y.textAlign='left';y.fillText('BILLING  #'+(2400+tok),8,19);
    for(let l=0;l<6;l++){const w=((l*47+Math.floor(t*40))%110)+60;y.fillStyle=l%2?'#C8D6E6':'#9BB6D3';y.fillRect(10,40+l*18,w,9);y.fillStyle='#1DB98A';y.fillRect(200,40+l*18,40,9);}inv.t.needsUpdate=true;}};
 })();

 /* ================= 3. GLOBE ================= */
 (function(){const S=newSet(180),g=S.g;const R=3.3;
  const gt=ctex(1024,512,(x,W,H)=>{const og=x.createLinearGradient(0,0,0,H);og.addColorStop(0,'#A9D4FA');og.addColorStop(.5,'#7FB8F0');og.addColorStop(1,'#A9D4FA');x.fillStyle=og;x.fillRect(0,0,W,H);
   function land(a,b){return Math.sin(a*2.1+1)*.5+Math.sin(b*3.3+a*.7)*.45+Math.sin(a*5.2-b*2)*.25+Math.sin(b*7+a*3)*.12;}
   for(let j=0;j<H;j+=4)for(let i=0;i<W;i+=4){const lon=i/W*6.283,lat=(j/H-.5)*3.14;const v=land(lon,lat*1.6)-Math.abs(lat)*.35;if(v>.18){x.fillStyle=v>.6?'#9BD59A':'#6FC48F';x.fillRect(i,j,4,4);}}
   x.strokeStyle='rgba(255,255,255,.28)';x.lineWidth=1;for(let i=0;i<=24;i++){x.beginPath();x.moveTo(i*W/24,0);x.lineTo(i*W/24,H);x.stroke();}for(let j=0;j<=12;j++){x.beginPath();x.moveTo(0,j*H/12);x.lineTo(W,j*H/12);x.stroke();}});
  const gm=new THREE.MeshStandardMaterial({map:gt.t,roughness:.65,metalness:.05});
  const globe=new THREE.Group();g.add(globe);const earth=new THREE.Mesh(new THREE.SphereGeometry(R,64,48),gm);globe.add(earth);
  try{const tl=new THREE.TextureLoader();tl.setCrossOrigin('anonymous');tl.load(DATA.earth,tx=>{gm.map=tx;gm.color.set(0xDDEBFF);gm.needsUpdate=true;},undefined,()=>{});}catch(e){}
  const atm=new THREE.Mesh(new THREE.SphereGeometry(R*1.12,48,36),new THREE.ShaderMaterial({transparent:true,side:THREE.BackSide,blending:THREE.AdditiveBlending,depthWrite:false,vertexShader:'varying vec3 vN;void main(){vN=normalize(normalMatrix*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',fragmentShader:'varying vec3 vN;void main(){float i=pow(.72-dot(vN,vec3(0.,0.,1.)),3.);gl_FragColor=vec4(.25,.62,1.,1.)*i;}'}));g.add(atm);
  function ll(lat,lon,r){const p=(90-lat)*Math.PI/180,th=(lon+180)*Math.PI/180;return new THREE.Vector3(-r*Math.sin(p)*Math.cos(th),r*Math.cos(p),r*Math.sin(p)*Math.sin(th));}
  const pulses=[];function pin(lat,lon,h,col,big){const p=ll(lat,lon,R),n=p.clone().normalize();const st=cyl(globe,.012,.012,h,MB(col),0,0,0,6);st.position.copy(n.clone().multiplyScalar(R+h/2));st.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),n);
   const hd=sph(globe,big?.09:.045,MB(col),0,0,0);hd.position.copy(n.clone().multiplyScalar(R+h));const rg=new THREE.Mesh(new THREE.RingGeometry(.06,.085,24),MB(col,{transparent:true,opacity:.8,side:THREE.DoubleSide,depthWrite:false}));rg.position.copy(n.clone().multiplyScalar(R+.01));rg.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),n);globe.add(rg);pulses.push({rg,ph:Math.random()*6,big});return hd.position.clone();}
  const hubs=[[51.5,-0.1],[35.7,139.7],[28.6,77.2],[-33.9,151.2],[-23.5,-46.6],[30,31.2],[55.7,37.6],[37.8,-122.4],[1.35,103.8],[-26.2,28],[19.4,-99.1],[48.9,2.3]];
  const ny=ll(42.9,-75.5,R),nyPos=pin(42.9,-75.5,.55,0xE5384F,true);
  const arcs=[];hubs.forEach((h,i)=>{const hp=pin(h[0],h[1],.28,i%2?0x1DB98A:0x1E6FD9,false);const a=nyPos.clone().normalize(),b=hp.clone().normalize();const pts=[];for(let k=0;k<=40;k++){const f=k/40,v=a.clone().lerp(b,f).normalize().multiplyScalar(R+.15+Math.sin(f*Math.PI)*.6);pts.push(v);}
   const geo=new THREE.BufferGeometry().setFromPoints(pts);const ln=new THREE.Line(geo,new THREE.LineBasicMaterial({color:i%2?0x1DB98A:0x1E6FD9,transparent:true,opacity:.75}));ln.geometry.setDrawRange(0,0);globe.add(ln);arcs.push({ln,ph:i*.7});});
  const maxv=Math.max(1,...DATA.pins.map(p=>p.v));DATA.pins.forEach(p=>pin(p.lat,p.lon,.12+.5*p.v/maxv,0xE5384F,false));
  /* NY label */
  const nl=label('New York State | '+DATA.hospitals+' hospitals',900,110,'#0B4F9C','#FFFFFF',46);const nls=new THREE.Sprite(new THREE.SpriteMaterial({map:nl.t,transparent:true,depthTest:false}));nls.scale.set(4.4,.54,1);nls.position.set(0,R+1.15,0);g.add(nls);
  const orb1=new THREE.Mesh(new THREE.TorusGeometry(R*1.45,.012,8,160),MB(0x1E6FD9,{transparent:true,opacity:.4}));orb1.rotation.set(1.3,.2,0);g.add(orb1);
  const orb2=new THREE.Mesh(new THREE.TorusGeometry(R*1.75,.012,8,160),MB(0x1DB98A,{transparent:true,opacity:.35}));orb2.rotation.set(1.1,-.5,0);g.add(orb2);
  const sat=new THREE.Group();box(sat,.3,.18,.18,M(0xffffff));box(sat,.04,.34,.5,M(0x1E6FD9),-.28,0,0);box(sat,.04,.34,.5,M(0x1E6FD9),.28,0,0);g.add(sat);
  const sp=new Float32Array(180*3);for(let i=0;i<180;i++){const r=9+Math.random()*10,a=Math.random()*6.28,b=Math.acos(2*Math.random()-1);sp[i*3]=r*Math.sin(b)*Math.cos(a);sp[i*3+1]=r*Math.cos(b)*.6;sp[i*3+2]=r*Math.sin(b)*Math.sin(a)-6;}
  const stg=new THREE.BufferGeometry();stg.setAttribute('position',new THREE.BufferAttribute(sp,3));const stars=new THREE.Points(stg,new THREE.PointsMaterial({color:0x1E6FD9,size:.08,transparent:true,opacity:.6}));g.add(stars);
  const focusY=-Math.atan2(ny.x,ny.z),focusX=Math.atan2(ny.y,ny.z);const G={vy:0,vx:0,idle:0};
  globe.rotation.set(focusX*.6,focusY,0);S.globe=G;S.obj=globe;
  S.tick=(t,dt,lowq,drag)=>{if(drag){G.idle=0;}else{G.idle+=dt;}
   if(!drag){globe.rotation.y+=G.vy;globe.rotation.x+=G.vx;G.vy*=.94;G.vx*=.94;if(G.idle>3&&Math.abs(G.vy)<.002)globe.rotation.y+=dt*.28;}
   globe.rotation.x=Math.max(-1.1,Math.min(1.1,globe.rotation.x));
   pulses.forEach(p=>{const k=(t*.8+p.ph)%1;p.rg.scale.setScalar(1+k*(p.big?4:2.6));p.rg.material.opacity=.85*(1-k);});
   arcs.forEach(a=>{const n=Math.floor(((t*.35+a.ph*.2)%1.6)*41);a.ln.geometry.setDrawRange(0,Math.min(41,Math.max(0,n)));});
   orb1.rotation.z=t*.08;orb2.rotation.z=-t*.06;sat.position.set(Math.cos(t*.7)*R*1.45,Math.sin(t*.7)*.2,Math.sin(t*.7)*R*1.45);sat.rotation.y=-t*.7;
   nls.position.y=R+1.15+Math.sin(t*1.2)*.06;};
 })();

 /* ================= 4. CLEAN CORRIDOR ================= */
 (function(){const S=newSet(240),g=S.g;const W=5,LEN=70;
  const fl=plane(g,W*2,LEN,M(0xD3EBE4,{roughness:.12,metalness:.25}),0,0,-LEN/2+16,-Math.PI/2);
  box(g,.25,.03,LEN,MB(0x1DB98A),-2.2,.02,-LEN/2+16);box(g,.25,.03,LEN,MB(0x1E6FD9),2.2,.02,-LEN/2+16);
  for(let i=0;i<12;i++){const c=ctex(128,128,(x)=>{x.fillStyle='rgba(0,0,0,0)';x.strokeStyle='#1DB98A';x.lineWidth=14;x.lineCap='round';x.lineJoin='round';x.beginPath();x.moveTo(24,40);x.lineTo(64,84);x.lineTo(104,40);x.stroke();});plane(g,1.4,1.4,MB(0xffffff,{map:c.t,transparent:true}),0,.04,10-i*5.5,-Math.PI/2);}
  plane(g,W*2,LEN,M(0xE2EEF4),0,6.2,-LEN/2+16,Math.PI/2);
  for(let i=0;i<14;i++){box(g,3.2,.1,1,MB(0xFFFFFF),0,6.1,12-i*5);}
  const wm=M(0xC4E3DC,{roughness:.4});
  const rooms=[];
  for(let side=-1;side<=1;side+=2){for(let k=0;k<8;k++){const z=8-k*8;
    box(g,.4,6.2,4.2,wm,side*W,3.1,z+2.9);box(g,.4,6.2,.4,wm,side*W,3.1,z-.1);box(g,.4,1.4,3,wm,side*W,5.5,z+1.4);
    const rm=new THREE.Group();rm.position.set(side*(W+3),0,z+1.4);g.add(rm);
    box(rm,6,.1,3.6,M(0xD2E8E2),0,.05,0);box(rm,.2,6,3.6,M(0xD6EAE6),side*3,3,0);box(rm,6,6,.2,M(0xD6EAE6),0,3,-1.9);box(rm,6,6,.2,M(0xD6EAE6),0,3,1.9);
    box(rm,2.2,.5,1.2,M(0xDCE9F5),side*-.4,.7,0);box(rm,2.0,.18,1.05,M(0xFFFFFF),side*-.4,1.05,0);box(rm,.5,.14,.8,M(0xF4F9FF),side*-1.3,1.2,0);
    box(rm,.1,.6,1.2,MB(0xCFE6FA),side*2.9,3.8,0);box(rm,.1,.2,.2,MB(0xffffff),side*2.9,5.4,0);
    const lg=new THREE.PointLight(0xdffff0,.0,0);rm.add(lg);
    const c=ctex(256,96,(x,Wd,H)=>{x.fillStyle='#E9FBF3';rr(x,0,0,Wd,H,18);x.fill();x.strokeStyle='#1DB98A';x.lineWidth=5;rr(x,3,3,Wd-6,H-6,16);x.stroke();x.fillStyle='#1DB98A';x.beginPath();x.arc(46,48,24,0,7);x.fill();x.strokeStyle='#fff';x.lineWidth=6;x.lineCap='round';x.beginPath();x.moveTo(35,48);x.lineTo(44,57);x.lineTo(58,38);x.stroke();x.fillStyle='#0E5C45';x.font='800 28px Arial';x.textAlign='left';x.fillText('STERILE',84,58);});
    const pl=plane(g,1.6,.6,MB(0xffffff,{map:c.t}),side*(W-.25),5.6,z+1.4);pl.rotation.y=-side*Math.PI/2;rooms.push(pl);}}
  /* robot */
  const rb=new THREE.Group();cyl(rb,.55,.62,.7,M(0xFFFFFF,{roughness:.25}),0,.45,0,28);const dome=new THREE.Mesh(new THREE.SphereGeometry(.5,24,12,0,Math.PI*2,0,Math.PI/2),M(0x1E6FD9,{roughness:.3}));dome.position.y=.8;rb.add(dome);
  const eye=new THREE.Mesh(new THREE.TorusGeometry(.22,.04,8,24),MB(0x1DB98A));eye.position.set(0,.95,.35);eye.rotation.x=.3;rb.add(eye);
  const cone=new THREE.Mesh(new THREE.ConeGeometry(1.2,2.4,24,1,true),new THREE.MeshBasicMaterial({color:0x7FE7C8,transparent:true,opacity:.14,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide}));cone.position.y=1.5;cone.rotation.x=Math.PI;rb.add(cone);g.add(rb);
  /* end hologram */
  const sh=new THREE.Group();sh.position.set(0,3,-38);g.add(sh);const shield=new THREE.Mesh(new THREE.CylinderGeometry(2.4,2.4,.35,6),M(0x1DB98A,{emissive:0x1DB98A,emissiveIntensity:.5,roughness:.3}));shield.rotation.x=Math.PI/2;sh.add(shield);
  const ck1=box(sh,.5,2.2,.4,MB(0xffffff),.5,.2,.3);ck1.rotation.z=-.6;const ck2=box(sh,.5,1.2,.4,MB(0xffffff),-.7,-.35,.3);ck2.rotation.z=.8;
  const sh2=new THREE.Mesh(new THREE.TorusGeometry(3.2,.05,8,60),MB(0x1E6FD9));sh.add(sh2);
  /* sparkles + bubbles */
  const spk=[];for(let i=0;i<46;i++){const m=new THREE.Mesh(new THREE.OctahedronGeometry(.1,0),MB(i%3?0xFFFFFF:0xCFCE5D));m.position.set((Math.random()-.5)*8,.4+Math.random()*4.6,12-Math.random()*50);g.add(m);spk.push({m,ph:Math.random()*6,sp:1+Math.random()*2});}
  const bubs=[];for(let i=0;i<24;i++){const m=new THREE.Mesh(new THREE.SphereGeometry(.12+Math.random()*.18,14,10),new THREE.MeshBasicMaterial({color:0xBFEFFF,transparent:true,opacity:.28}));m.position.set((Math.random()-.5)*8,Math.random()*5,12-Math.random()*46);g.add(m);bubs.push({m,sp:.2+Math.random()*.4,ph:Math.random()*6});}
  S.tick=(t,dt,lowq)=>{rb.position.set(Math.sin(t*.35)*1.8,0,-6-((t*2.2)%30));rb.rotation.y=Math.sin(t*.35)*.4;shield.rotation.z=t*.8;sh2.rotation.z=-t*.5;sh.position.y=3+Math.sin(t*1.1)*.2;
   spk.forEach(s=>{const k=Math.sin(t*s.sp+s.ph)*.5+.5;s.m.scale.setScalar(.3+k*1.3);s.m.rotation.y+=dt*2;});bubs.forEach(b=>{b.m.position.y+=dt*b.sp;if(b.m.position.y>5.6)b.m.position.y=.2;b.m.position.x+=Math.sin(t+b.ph)*.003;});
   rooms.forEach((r,i)=>{r.material.opacity=1;});};
 })();

 /* ================= guide: Jabby the syringe, parented to the camera ================= */
 const guide=new THREE.Group();camera.add(guide);
 const gb=new THREE.Group();guide.add(gb);const GR=.62;
 gb.add(new THREE.Mesh(new THREE.CylinderGeometry(GR,GR,2.6,32),new THREE.MeshPhysicalMaterial({color:0xdff1ff,transparent:true,opacity:.3,roughness:.05,clearcoat:1,depthWrite:false})));
 cyl(gb,.54,.54,1.75,M(0x22C79A,{roughness:.25,emissive:0x0b7a5a,emissiveIntensity:.18}),0,-.325,0,28);
 const gf=cyl(gb,GR,GR,.1,M(0xEAF4FF),0,1.32,0,32);gf.scale.set(1.5,1,.55);cyl(gb,.34,.12,.45,M(0xEAF4FF),0,-1.525,0,20);cyl(gb,.2,.2,.3,M(0x1E6FD9),0,-1.85,0,16);cyl(gb,.035,.018,1.4,M(0xD8E3EE,{metalness:.9,roughness:.2}),0,-2.75,0,8);
 const gp=new THREE.Group();gb.add(gp);cyl(gp,.56,.56,.28,M(0x0B4F9C),0,.7,0,28);box(gp,.34,1.4,.07,M(0xCFE3F7),0,1.52,0);box(gp,.07,1.4,.34,M(0xCFE3F7),0,1.52,0);cyl(gp,.55,.55,.13,M(0xE5384F),0,2.26,0,32);
 function onB(m,x,y){const a=Math.asin(x/GR);m.position.set(x,y,Math.cos(a)*GR);m.rotation.y=a;return m;}
 const geyes=[],gpup=[];[-1,1].forEach(s=>{const e=new THREE.Group(),w=sph(e,.14,M(0xffffff,{roughness:.25}),0,0,0);w.scale.set(1,1.2,.45);const p=sph(e,.075,M(0x0E2A47),0,-.01,.05);p.scale.z=.6;gpup.push(p);onB(e,s*.21,.2);gb.add(e);geyes.push(e);});
 const gmo=new THREE.Mesh(new THREE.TorusGeometry(.15,.026,8,20,Math.PI),MB(0x7A1A2B));onB(gmo,0,-.1);gmo.rotation.z=Math.PI;gb.add(gmo);
 function garm(s){const a=new THREE.Group();const u=cyl(a,.065,.065,.55,M(0xEAF4FF),.28,0,0,12);u.rotation.z=Math.PI/2;sph(a,.12,M(0xffffff),.62,0,0);a.position.set(s*.64,-.05,.05);a.scale.x=s;gb.add(a);return a;}
 const garR=garm(1),garL=garm(-1);gb.position.y=.56;guide.scale.setScalar(.34);guide.rotation.z=-.22;guide.traverse(o=>{if(o.material){o.material.depthTest=false;o.renderOrder=999;}});

 /* ---------- state: window rect, camera flight, input ---------- */
 const WP=[{p:[16,6,29],l:[0,5.2,0]},{p:[69,4.2,13],l:[60,2.4,-1.5]},{p:[114,3.8,14.5],l:[120,2.2,-3]},{p:[180,.6,9.8],l:[180,.1,0]},{p:[240,2.7,13.5],l:[240,2.5,-22]}];
 const cp=new THREE.Vector3(...WP[0].p),cl=new THREE.Vector3(...WP[0].l);
 let fl=null,fov0=44;const ease=x=>x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;
 function goto(i,snap){if(i===pageI&&!snap&&!fl&&cp.distanceTo(new THREE.Vector3(...WP[i].p))<3)return;pageI=i;tipI=0;const l=tipsFor(i);say(l.length?l[0]:'Hi!');
  document.querySelectorAll('.sky').forEach((s,k)=>s.classList.toggle('on',k===i));
  const A=cp.clone(),AL=cl.clone(),B=new THREE.Vector3(...WP[i].p),BL=new THREE.Vector3(...WP[i].l);
  if(snap||reduce){cp.copy(B);cl.copy(BL);fl=null;return;}
  const C=A.clone().add(B).multiplyScalar(.5);C.y+=Math.min(14,A.distanceTo(B)*.22);fl={A,AL,B,BL,C,t:0,d:2.4};}
 const ptr={x:0,y:0,tx:0,ty:0};let drag=false,lx=0,ly=0,winEl=null;
 function attach(){if(!pd)return;const w=pd.getElementById('scene-window');if(!w||w===winEl)return;winEl=w;w.style.cursor='grab';w.style.touchAction='none';
  w.addEventListener('pointerdown',e=>{drag=true;lx=e.clientX;ly=e.clientY;w.style.cursor='grabbing';try{w.setPointerCapture(e.pointerId);}catch(_){} 
   const r=w.getBoundingClientRect();if(e.clientX>r.right-r.width*.28)nextTip();});
  w.addEventListener('pointermove',e=>{const r=w.getBoundingClientRect();ptr.tx=((e.clientX-r.left)/r.width-.5)*2;ptr.ty=((e.clientY-r.top)/r.height-.5)*2;
   if(drag&&SETS[3].obj&&pageI===3){const dx=e.clientX-lx,dy=e.clientY-ly;SETS[3].obj.rotation.y+=dx*.008;SETS[3].obj.rotation.x+=dy*.006;SETS[3].globe.vy=dx*.0007;SETS[3].globe.vx=dy*.0005;}lx=e.clientX;ly=e.clientY;});
  const up=()=>{drag=false;w.style.cursor='grab';};w.addEventListener('pointerup',up);w.addEventListener('pointercancel',up);w.addEventListener('pointerleave',()=>{ptr.tx=ptr.ty=0;});};
 stage.addEventListener('pointerdown',()=>{});
 let rect={l:0,t:0,w:0,h:0,ok:false},sig='';
 function readWin(){if(!pd){rect={l:20,t:20,w:Math.max(100,innerWidth-40),h:Math.min(320,innerHeight-40),ok:true};return;}
  const w=pd.getElementById('scene-window');if(!w){rect.ok=false;return;}const r=w.getBoundingClientRect();rect={l:r.left,t:r.top,w:r.width,h:r.height,ok:r.width>40&&r.height>40&&r.bottom>0&&r.top<innerHeight};}
 function applyWin(){if(!rect.ok){stage.style.display='none';return;}const s=[rect.l,rect.t,rect.w,rect.h].map(v=>Math.round(v)).join(',');
  stage.style.display='block';stage.style.transform='translate('+Math.round(rect.l)+'px,'+Math.round(rect.t)+'px)';
  if(s.split(',').slice(2).join()!==sig){sig=s.split(',').slice(2).join();stage.style.width=Math.round(rect.w)+'px';stage.style.height=Math.round(rect.h)+'px';
   renderer.setSize(Math.round(rect.w),Math.round(rect.h),false);camera.aspect=rect.w/rect.h;camera.updateProjectionMatrix();layoutGuide();}}
 function layoutGuide(){const d=7,hh=d*Math.tan(camera.fov*Math.PI/360),hw=hh*camera.aspect;guide.position.set(hw*.74,-hh*.3,-d);guide.scale.setScalar(Math.max(.22,Math.min(.42,hh*.12)));}
 /* ---------- loop ---------- */
 let running=false,last=0,t=0,frames=0,fpsT=0,low=0,lowq=false,raf=0,blink=0,nb=2;
 function update(dt){
  t+=dt;ptr.x+=(ptr.tx-ptr.x)*Math.min(1,dt*4);ptr.y+=(ptr.ty-ptr.y)*Math.min(1,dt*4);
  let tp,tl,fov=44,flash=0;
  if(fl){fl.t+=dt/fl.d;const u=Math.min(1,fl.t),e=ease(u),a=1-e;
   tp=new THREE.Vector3().addScaledVector(fl.A,a*a).addScaledVector(fl.C,2*a*e).addScaledVector(fl.B,e*e);tl=fl.AL.clone().lerp(fl.BL,e);
   fov=44+Math.sin(u*Math.PI)*22;flash=Math.sin(u*Math.PI);cp.copy(tp);cl.copy(tl);if(u>=1)fl=null;}
  else{const B=WP[pageI];tp=new THREE.Vector3(B.p[0]+Math.sin(t*.22)*1.3+ptr.x*1.4,B.p[1]+Math.sin(t*.31)*.35-ptr.y*.5,B.p[2]+Math.cos(t*.17)*.9);
   if(pageI===4)tp.z=B.p[2]-((t*.7)%9);tl=new THREE.Vector3(...B.l);cp.lerp(tp,Math.min(1,dt*3));cl.lerp(tl,Math.min(1,dt*3));tp=cp;tl=cl;}
  camera.position.copy(tp);camera.lookAt(tl);if(Math.abs(camera.fov-fov)>.05){camera.fov=fov;camera.updateProjectionMatrix();layoutGuide();}
  $('streaks').style.opacity=(flash*.55).toFixed(3);$('streaks').style.transform='scale('+(1+flash*.35)+') rotate('+(t*10)+'deg)';$('flash').style.opacity=(flash*.5).toFixed(3);
  SETS.forEach((s,i)=>{const d=Math.abs(camera.position.x-s.x);s.g.visible=d<38;if(s.g.visible&&s.tick)s.tick(t,dt,lowq,drag);});
  gb.rotation.y=Math.sin(t*.6)*.25+ptr.x*.4;gb.position.y=.56+Math.sin(t*1.4)*.1;gp.position.y=Math.sin(t*1.2)*.07;garR.rotation.z=.85+Math.sin(t*6.5)*.38;garL.rotation.z=-.55+Math.sin(t*1.6)*.08;
  gpup.forEach(p=>{p.position.x=ptr.x*.03;});nb-=dt;if(nb<=0){blink=.14;nb=2.4+Math.random()*2.6;}if(blink>0){blink-=dt;const sy=Math.max(.08,Math.abs(blink-.07)/.07);geyes.forEach(e=>e.scale.y=Math.min(1,sy));}else geyes.forEach(e=>e.scale.y=1);
 }
 function frame(now){if(!running)return;raf=requestAnimationFrame(frame);const dt=Math.min((now-last)/1000,.05);last=now;
  readWin();applyWin();if(!rect.ok)return;update(dt);renderer.render(scene,camera);
  frames++;fpsT+=dt;if(fpsT>=2){const f=frames/fpsT;frames=0;fpsT=0;if(f<30){low++;if(pr>1){pr=1;renderer.setPixelRatio(1);sig='';}else if(low>=2)lowq=true;}else low=0;}}
 function start(){if(running)return;running=true;last=performance.now();raf=requestAnimationFrame(frame);}function stop(){running=false;cancelAnimationFrame(raf);}
 let tabOn=!document.hidden;document.addEventListener('visibilitychange',()=>{tabOn=!document.hidden;tabOn?start():stop();});
 /* page marker watcher */
 setInterval(()=>{attach();if(!pd)return;const m=pd.getElementById('page-marker');if(!m)return;const i=PAGES.indexOf(m.getAttribute('data-page'));if(i>=0&&i!==pageI)goto(i);},250);
 canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();stop();document.body.classList.add('nogl');});
 canvas.addEventListener('webglcontextrestored',()=>{document.body.classList.remove('nogl');start();});
 window.__world={goto:(i,s)=>goto(i,s),debug:()=>({pageI,cp:cp.toArray(),vis:SETS.map(s=>s.g.visible)})};
 /* first page */
 (function(){const m=pd&&pd.getElementById('page-marker');const i=m?PAGES.indexOf(m.getAttribute('data-page')):0;pageI=Math.max(0,i);cp.set(...WP[pageI].p);cl.set(...WP[pageI].l);document.querySelectorAll('.sky').forEach((s,k)=>s.classList.toggle('on',k===pageI));const l=tipsFor(pageI);say(l.length?l[0]:'Hi!');})();
 readWin();applyWin();update(.016);renderer.render(scene,camera);setTimeout(()=>{$('load').style.opacity=0;},600);start();
}
setInterval(()=>{if(!document.hidden&&window.__booted)nextTip();},11000);
</script>
<script src="__PRIMARY__" onload="boot()" onerror="this.onerror=null;var s=document.createElement('script');s.src='__BACKUP__';s.onload=boot;s.onerror=function(){document.body.classList.add('nogl');document.getElementById('load').style.display='none'};document.head.appendChild(s)"></script>
</body></html>"""


def world_html(data: dict) -> str:
    """Return the world document. `data` holds speech-bubble facts, per-page tips and globe pins."""
    payload = dict(data)
    payload.setdefault("earth", EARTH_TEXTURE)
    text = json.dumps(payload).replace("</", "<\\/")
    return _HTML.replace("__DATA__", text).replace("__PRIMARY__", THREE_PRIMARY).replace("__BACKUP__", THREE_BACKUP)
