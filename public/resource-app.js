const DIRS=[[1,0,-1],[1,-1,0],[0,-1,1],[-1,0,1],[-1,1,0],[0,1,-1]];
const HEX_W=2,HEX_H=(2/Math.sqrt(3))*2;
const KINDS=["ore","wood","grain","water"];
const COL={ore:["#fbbf24","#b45309","#78350f"],wood:["#34d399","#047857","#064e3b"],grain:["#fde68a","#ca8a04","#854d0e"],water:["#38bdf8","#0369a1","#0c4a6e"],camp:["#e5e7eb","#6b7280","#374151"],mill:["#c4b5fd","#7c3aed","#4c1d95"]};
const COST={camp:4,mill:7},SELL={camp:2,mill:4};
const G={R:4,hexPx:18,view:1,tilt:48,yaw:18,panX:0,panY:0,tool:"camp",god:false,tiles:new Map(),stock:12,bag:{ore:0,wood:0,grain:0,water:0},msg:"place camps on clusters",seed:1};
function cells(R){const o=[];for(let q=-R;q<=R;q++){const a=Math.max(-R,-q-R),b=Math.min(R,-q+R);for(let r=a;r<=b;r++)o.push({q,r,s:-q-r});}return o;}
function key(c){return c.q+","+c.r+","+c.s;}
function at(q,r,s){return G.tiles.get([q,r,s??-q-r].join(","));}
function nbs(c){return DIRS.map(d=>at(c.q+d[0],c.r+d[1],c.s+d[2])).filter(Boolean);}
function offset(c){return {col:c.q+Math.floor(c.r/2),row:c.r};}
function world(c){const o=offset(c),sc=G.hexPx/2,w=HEX_W*sc,h=HEX_H*sc;return {x:o.col*w+(Math.abs(o.row)%2)*w*0.5,z:o.row*h*0.75};}
function hexPts(x,z,rad){const p=[];for(let i=0;i<6;i++){const a=Math.PI/180*(60*i-30);p.push([x+rad*Math.cos(a),z+rad*Math.sin(a)]);}return p;}
function rnd(n){G.seed=(G.seed*1664525+1013904223)>>>0;return (G.seed%n);}
function cluster(t){return nbs(t).filter(n=>n.res===t.res).length;}
function yieldOf(t){const k=cluster(t);const bld=t.bld==="mill"?2.2:t.bld==="camp"?1:0;return bld?+(t.rich*(1+k*0.45)*bld).toFixed(2):0;}
function boot(){G.seed=1;G.stock=G.god?999:12;G.bag={ore:0,wood:0,grain:0,water:0};G.msg="place camps on clusters";G.tiles=new Map();for(const c of cells(G.R)){G.tiles.set(key(c),{...c,res:KINDS[rnd(4)],rich:1+rnd(3),bld:null});}paint();}
function place(t){if(!t)return;if(G.tool==="sell"){if(t.bld){if(!G.god)G.stock+=SELL[t.bld]||0;t.bld=null;}paint();return;}const cost=COST[G.tool]||0;if(t.bld)return;if(!G.god&&G.stock<cost){G.msg="no stock";paint();return;}t.bld=G.tool;if(!G.god)G.stock-=cost;G.msg=G.god?"GOD":"";paint();}
function harvest(){let gained=0;for(const t of G.tiles.values()){const y=yieldOf(t);if(!y)continue;G.bag[t.res]+=y;gained+=y;}G.stock+=Math.floor(gained*0.35);G.msg="+"+gained.toFixed(1)+" clustered";paint();}
function colorFor(t){if(t.bld==="mill")return COL.mill;if(t.bld==="camp")return COL.camp;return COL[t.res];}
function paint(){const sc=G.hexPx/2,rad=HEX_H*sc*0.48;const pts=[...G.tiles.values()].map(t=>world(t));const xs=pts.map(p=>p.x),zs=pts.map(p=>p.z),pad=rad*3;const minx=Math.min(...xs)-pad,maxx=Math.max(...xs)+pad,minz=Math.min(...zs)-pad,maxz=Math.max(...zs)+pad+rad;const tiles=[...G.tiles.values()].sort((a,b)=>a.r-b.r||a.q-b.q);let svg=`<svg viewBox="${minx} ${minz} ${maxx-minx} ${maxz-minz}" width="100%" height="100%">`;for(const t of tiles){const {x,z}=world(t);const lift=rad*(0.28+(t.bld?0.22:0)+cluster(t)*0.04);const [top,L,R]=colorFor(t);const p=hexPts(x,z,rad),p2=hexPts(x,z+lift,rad);svg+=`<polygon points="${p[4][0]},${p[4][1]} ${p[5][0]},${p[5][1]} ${p2[5][0]},${p2[5][1]} ${p2[4][0]},${p2[4][1]}" fill="${L}"/>`;svg+=`<polygon points="${p[5][0]},${p[5][1]} ${p[0][0]},${p[0][1]} ${p2[0][0]},${p2[0][1]} ${p2[5][0]},${p2[5][1]}" fill="${R}"/>`;svg+=`<polygon data-k="${key(t)}" points="${p2.map(v=>v.join(",")).join(" ")}" fill="${top}" stroke="rgba(52,211,153,.25)" stroke-width="1"/>`;const y=yieldOf(t);const label=t.bld?y.toFixed(1):(t.res[0].toUpperCase()+t.rich);svg+=`<text x="${x}" y="${z+lift+3}" text-anchor="middle" font-size="${Math.max(7,rad*0.45)}" fill="#0b1220" font-family="system-ui">${label}</text>`;}svg+="</svg>";document.getElementById("board").innerHTML=svg;document.getElementById("g").textContent=G.god?"∞":Math.floor(G.stock);for(const k of KINDS)document.getElementById(k).textContent=G.bag[k].toFixed(1);document.getElementById("s").textContent=G.msg;}
function applyCam(){document.getElementById("board").style.transform=`translate(${G.panX}px,${G.panY}px) rotateX(${G.tilt}deg) rotateZ(${G.yaw}deg) scale(${G.view})`;}
(function(){const c=document.getElementById("bg"),ctx=c.getContext("2d");const rs=()=>{c.width=innerWidth;c.height=innerHeight;};rs();addEventListener("resize",rs);const hs=26,s3=Math.sqrt(3);(function draw(t){t*=.001;ctx.clearRect(0,0,c.width,c.height);const cols=c.width/(hs*s3)+2,rows=c.height/(hs*1.5)+2,cx=c.width/2,cy=c.height/2;for(let row=-1;row<rows;row++)for(let col=-1;col<cols;col++){const off=row%2?hs*s3*.5:0,x=col*hs*s3+off,y=row*hs*1.5,dist=Math.hypot(x-cx,y-cy),wave=Math.sin(t*.8-dist*.008)*.5+.5,hue=140+(t*12+dist*.1)%40;ctx.beginPath();for(let i=0;i<6;i++){const a=Math.PI/3*i+Math.PI/6,hx=x+(hs-2)*Math.cos(a),hy=y+(hs-2)*Math.sin(a);i?ctx.lineTo(hx,hy):ctx.moveTo(hx,hy);}ctx.closePath();ctx.strokeStyle=`hsla(${hue},50%,${12+wave*8}%,${.1+wave*.08})`;ctx.stroke();}requestAnimationFrame(draw);})(0);})();
document.querySelectorAll("[data-tool]").forEach(b=>b.onclick=()=>{G.tool=b.dataset.tool;document.querySelectorAll("[data-tool]").forEach(x=>x.classList.toggle("on",x===b));});
document.getElementById("tick").onclick=harvest;document.getElementById("new").onclick=boot;
document.getElementById("god").onclick=()=>{G.god=!G.god;document.getElementById("god").classList.toggle("god",G.god);if(G.god){G.stock=999;G.msg="GOD";}paint();};
document.getElementById("resetcam").onclick=()=>{G.yaw=18;G.tilt=48;G.view=1;G.panX=0;G.panY=0;document.getElementById("tilt").value=48;document.getElementById("tv").textContent="48°";document.getElementById("viewz").value=100;document.getElementById("vv").textContent="100%";applyCam();};
document.getElementById("r").oninput=e=>{G.R=+e.target.value;document.getElementById("rv").textContent=G.R;boot();};
document.getElementById("hex").oninput=e=>{G.hexPx=+e.target.value;document.getElementById("hv").textContent=G.hexPx;paint();};
document.getElementById("viewz").oninput=e=>{G.view=(+e.target.value)/100;document.getElementById("vv").textContent=e.target.value+"%";applyCam();};
document.getElementById("tilt").oninput=e=>{G.tilt=+e.target.value;document.getElementById("tv").textContent=G.tilt+"°";applyCam();};
const view=document.getElementById("view");let drag=null;
view.addEventListener("pointerdown",e=>{if(e.target.closest("[data-k]"))return;drag={x:e.clientX,y:e.clientY,yaw:G.yaw,tilt:G.tilt,panX:G.panX,panY:G.panY,moved:false,shift:e.shiftKey||e.button===1};view.classList.add("drag");view.setPointerCapture(e.pointerId);});
view.addEventListener("pointermove",e=>{if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.hypot(dx,dy)>4)drag.moved=true;if(drag.shift){G.panX=drag.panX+dx;G.panY=drag.panY+dy;}else{G.yaw=drag.yaw+dx*0.35;G.tilt=Math.max(0,Math.min(75,drag.tilt-dy*0.25));document.getElementById("tilt").value=G.tilt;document.getElementById("tv").textContent=Math.round(G.tilt)+"°";}applyCam();});
view.addEventListener("pointerup",e=>{view.classList.remove("drag");const hex=e.target.closest("[data-k]");if(hex&&(!drag||!drag.moved))place(G.tiles.get(hex.getAttribute("data-k")));drag=null;});
view.addEventListener("wheel",e=>{e.preventDefault();G.view=Math.max(0.35,Math.min(2.2,G.view*(1-e.deltaY*0.001)));document.getElementById("viewz").value=Math.round(G.view*100);document.getElementById("vv").textContent=Math.round(G.view*100)+"%";applyCam();},{passive:false});
addEventListener("keydown",e=>{if(e.key==="g"||e.key==="G")document.getElementById("god").click();if(e.key===" "){e.preventDefault();harvest();}});
boot();applyCam();
