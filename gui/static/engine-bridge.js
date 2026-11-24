// Browser adapter: all game state and deductions come from the team's Python engine.
// Mặc định gọi API cùng origin với trang (đúng với mọi cổng khi chạy --port).
// Chỉ khi mở thẳng file (file://) mới dùng cổng mặc định 8001; có thể ghi đè bằng ?api=http://127.0.0.1:PORT
const API_BASE = new URLSearchParams(location.search).get("api")
  || (location.protocol === "file:" ? "http://127.0.0.1:8001" : "");
const api = async (path, body) => {
  let r;
  try { r = await fetch(API_BASE + path, body ? {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)} : {}); }
  catch (_) { throw Error("Chưa kết nối engine. Hãy chạy: python -m src.engine.gui_server"); }
  const type = r.headers.get("content-type") || "";
  if (!type.includes("application/json")) throw Error("API trả về trang HTML. Hãy chạy GUI qua python -m src.engine.gui_server rồi mở đúng địa chỉ in ra trên terminal.");
  const data = await r.json(); if(!r.ok) throw Error(data.error || "Lỗi kết nối engine"); return data;
};
let enginePuzzleIds=[],gameSession=null;
let hintColorGroups={first:new Set(),second:new Set(),people:new Set()},hintScopes=[];
const plainClueText=clueText;
function colorizeHintText(node,k){
  const text=plainClueText(k),colors=Array(text.length).fill(null),rank={"hint-range-one":1,"hint-range-two":2,"hint-character-text":3};
  const mark=(term,cls)=>{if(!term)return;let from=0,lower=text.toLocaleLowerCase(),needle=term.toLocaleLowerCase();while((from=lower.indexOf(needle,from))>=0){for(let i=from;i<from+needle.length;i++)if(!colors[i]||rank[cls]>rank[colors[i]])colors[i]=cls;from+=needle.length;}};
  if(k.left&&k.right){mark(rt(k.left),"hint-range-one");mark(rt(k.right),"hint-range-two");}
  else if(k.region)mark(rt(k.region),"hint-range-one");
  const people=[k.region&&k.region.cell,k.cell,k.a,k.b].filter(c=>c&&P.characters[c]);
  people.forEach(c=>mark(nm(c),"hint-character-text"));
  let start=0;
  while(start<text.length){const cls=colors[start];let end=start+1;while(end<text.length&&colors[end]===cls)end++;const part=text.slice(start,end);
    if(cls){const span=document.createElement("span");span.className=cls;span.textContent=part;node.append(span);}else node.append(document.createTextNode(part));start=end;
  }
}
const legacyDraw=draw;
draw=function(flipped){
  legacyDraw();
  document.querySelectorAll("#board .cell").forEach(card=>{
    const c=card.dataset.c;
    if(!rev[c]||!P.clues[c])return;
    card.classList.add("has-clue");
    const note=document.createElement("span");note.className="inline-clue";colorizeHintText(note,P.clues[c]);
    card.querySelector(".face").append(note);
    card.setAttribute("aria-label",`${c} ${nm(c)}, ${L[rev[c]]}. ${note.textContent}`);
  });
  const stats=$("#stats");
  if(stats)stats.innerHTML=`<span>Bước engine: <b>${steps}</b></span><span>Đã lật: <b>${Object.keys(rev).length}/${cells.length}</b></span>`;
  if(flipped)requestAnimationFrame(()=>{
    const face=document.querySelector(`#board .cell[data-c="${flipped}"] .face`);
    if(face){face.getAnimations().forEach(animation=>animation.cancel());face.animate(
      [{transform:"rotateY(180deg) scale(.9)"},{transform:"none"}],
      {duration:600,easing:"cubic-bezier(.3, 1.3, .5, 1)"}
    );}
  });
};
// ---- 4x4 / 5x5: keep clues readable on small cards ----
// 1) shrink the clue text until it fits its card (marks it .clipped if even the minimum is too big)
// 2) selecting a revealed card shows its full clue in a popup next to it
function fitClues(){
  document.querySelectorAll("#board .inline-clue").forEach(note=>{
    note.style.fontSize="";note.classList.remove("clipped");
    let fs=parseFloat(getComputedStyle(note).fontSize);
    while(fs>8&&note.scrollHeight>note.clientHeight+1){fs-=.5;note.style.fontSize=fs+"px";}
    if(note.clientHeight>0&&note.scrollHeight>note.clientHeight+1)note.classList.add("clipped");
  });
}
function closeCluePop(){const e=document.getElementById("cluePop");if(e)e.remove();}
function showCluePop(){
  closeCluePop();
  if(!sel||!rev[sel]||!P.clues[sel])return;
  const card=document.querySelector(`#board .cell[data-c="${sel}"]`);
  const clipped=card&&card.querySelector(".inline-clue.clipped");
  const hidden=card&&getComputedStyle(card.querySelector(".inline-clue")||card).display==="none";
  if(!card||!(N>=4||clipped||hidden))return;
  const box=document.getElementById("board").closest(".board-box"),br=box.getBoundingClientRect(),cr=card.getBoundingClientRect();
  const pop=document.createElement("div");pop.id="cluePop";pop.className="clue-pop";pop.setAttribute("role","status");
  const title=document.createElement("b");title.textContent=`${nm(sel)} (${sel})`;
  const text=document.createElement("p");text.textContent=plainClueText(P.clues[sel]);
  pop.append(title,text);box.append(pop);
  const pw=pop.offsetWidth,ph=pop.offsetHeight;
  let left=cr.left-br.left+cr.width/2-pw/2;left=Math.max(8,Math.min(left,br.width-pw-8));
  let top=cr.bottom-br.top+8;if(top+ph>br.height-8)top=cr.top-br.top-ph-8;
  pop.style.left=left+"px";pop.style.top=Math.max(8,top)+"px";
}
const drawWithClues=draw;
function makeHintColorGroups(clueIds){
  hintColorGroups={first:new Set(),second:new Set(),people:new Set()};hintScopes=[];
  if(hintCell)hintColorGroups.people.add(hintCell);
  const addScope=r=>{if(!r)return;const group=hintScopes.length===0?hintColorGroups.first:hintColorGroups.second;region(r).forEach(c=>group.add(c));hintScopes.push(r);if(r.kind==="NEIGHBORS")hintColorGroups.people.add(r.cell);};
  (clueIds||[]).forEach(id=>{const k=P.clues[id];if(!k)return;
    if(k.left&&k.right){addScope(k.left);addScope(k.right);}else if(k.region)addScope(k.region);
    [k.cell,k.a,k.b].filter(c=>c&&P.characters[c]).forEach(c=>hintColorGroups.people.add(c));
  });
}
function showHintSummary(h){
  const host=$("#toast");host.textContent="";const pill=document.createElement("span");pill.className="pill warn hint-message";
  pill.append("Gợi ý cho ");const who=document.createElement("strong");who.className="hint-character-text";who.textContent=`${nm(h.cell)} (${h.cell})`;pill.append(who,` là ${L[h.verdict].toLowerCase()}.`);
  hintScopes.slice(0,2).forEach((r,i)=>{
    const scope=document.createElement("strong");scope.className=i===0?"hint-range-one":"hint-range-two";const label=i===0?"Vùng 1":"Vùng 2";
    if(r.kind==="NEIGHBORS"){scope.append(` ${label}: hàng xóm của `);const name=document.createElement("span");name.className="hint-character-text";name.textContent=nm(r.cell);scope.append(name,".");}
    else scope.textContent=` ${label}: ${rt(r)}.`;
    pill.append(scope);
  });host.append(pill);
}
draw=function(flipped){
  drawWithClues(flipped);document.body.dataset.n=N;
  const board=document.getElementById("board"),selectedClue=Boolean(sel&&rev[sel]&&P.clues[sel]),active=Boolean(hl.length&&(hintCell||selectedClue));board.classList.toggle("hint-active",active);
  board.querySelectorAll(".cell").forEach(card=>{
    card.classList.remove("hint-marked","hint-person","hint-target","focus-card","dimmed");card.style.removeProperty("--border-left");card.style.removeProperty("--border-right");
    const c=card.dataset.c,roles=[];
    if(hintColorGroups.people.has(c)){roles.push("#D97706");card.classList.add("hint-person");}
    if(hintColorGroups.first.has(c))roles.push("#FF4D94");
    if(hintColorGroups.second.has(c))roles.push("#26B5D2");
    if(active&&roles.length){card.classList.add("hint-marked");card.style.setProperty("--border-left",roles[0]);card.style.setProperty("--border-right",roles[1]||roles[0]);}
    else if(active&&c===sel&&selectedClue)card.classList.add("focus-card");
    else if(active)card.classList.add("dimmed");
    if(active&&c===hintCell)card.classList.add("hint-target");
  });
  fitClues();showCluePop();
};
let clueFitFrame=0;
window.addEventListener("resize",()=>{cancelAnimationFrame(clueFitFrame);clueFitFrame=requestAnimationFrame(()=>{fitClues();showCluePop();});});
// composedPath(): the clicked card is already re-rendered (detached) when the event reaches document
document.addEventListener("click",e=>{if(!e.composedPath().some(n=>n.id==="board"))closeCluePop();});
document.addEventListener("keydown",e=>{if(e.key==="Escape")closeCluePop();});
$("#clue").closest(".card").hidden=true;
$(".side").append($("#toast"));
function acceptEngineState(p,explicitFlip=null){
  if (!curDate) { curDate=today(); viewMon=monday(curDate); }
  const sameSession=gameSession&&gameSession===p.session;
  const newlyFlipped=sameSession?Object.keys(p.revealed||{}).find(c=>!rev[c]):null;
  const flipped=explicitFlip||newlyFlipped;
  P=p; gameSession=p.session; N=p.size; cells=Object.keys(p.characters); rev={...p.revealed};
  P.initial_revealed=Object.keys(rev); solved=Object.keys(rev).length===cells.length;
  steps=p.steps||0; sat=0; sel=null; hl=flipped&&P.clues[flipped]?clueCells(P.clues[flipped]):[]; hintCell=null;hintScopes=[];hintColorGroups={first:new Set(),second:new Set(),people:new Set()};
  if(flipped&&P.clues[flipped])$("#clue").innerHTML=`<b>Manh mối mới của ${nm(flipped)}:</b> ${clueText(P.clues[flipped])}`;
  draw(flipped||undefined); infoLine();
}
async function startEnginePuzzle(index=0){
  const meta=enginePuzzleIds[index % enginePuzzleIds.length]; if(!meta)return;
  curDate=curDate||today(); viewMon=monday(curDate);
  const p=await api("/api/start",{id:meta.id}); acceptEngineState(p);
  renderWeek();
  $("#dayinfo").textContent=`${meta.id} · ${p.size}×${p.size}`;
}
load=function(p){acceptEngineState(p);};
selectDate=async function(d){if(busy)return;curDate=new Date(d);viewMon=monday(curDate);const i=(curDate.getDay()+6)%7;await startEnginePuzzle(i);};
pick=async function(c){if(busy||paused)return;sel=c;hintCell=null;hl=[];hintScopes=[];hintColorGroups={first:new Set(),second:new Set(),people:new Set()};
 if(rev[c]){$("#clue").innerHTML=`<b>${nm(c)} (${c}):</b> ${clueText(P.clues[c])}`;hl=clueCells(P.clues[c]);if(P.clues[c])makeHintColorGroups([c]);$("#call").innerHTML="";}
 else{$("#clue").textContent="Thẻ này đang úp. Hãy gọi tên nếu bạn chắc chắn.";$("#call").innerHTML=`<button class="btn pink" data-v="CRIMINAL">${IC("ghost")}Tội phạm</button><button class="btn cyan" data-v="INNOCENT">${IC("love")}Vô tội</button>`;$("#call").querySelectorAll("button").forEach(b=>b.onclick=()=>call(c,b.dataset.v));} draw();
};
let submittingVerdict=false;
call=async function(c,v){if(submittingVerdict)return;submittingVerdict=true;$("#call").querySelectorAll("button").forEach(b=>b.disabled=true);try{const out=await api("/api/call",{id:P.id,session:gameSession,cell:c,verdict:v});if(out.status!=="ACCEPTED"){
 if(out.state)acceptEngineState(out.state);
 if(out.status==="INVALID"){
  const state=out.state||await api(`/api/state?id=${encodeURIComponent(P.id)}&session=${encodeURIComponent(gameSession)}`);
  if(state.revealed&&state.revealed[c]){const existing=state.revealed[c];acceptEngineState(state);hl=clueCells(P.clues[c]);$("#clue").innerHTML=`<b>${nm(c)} (${c}):</b> ${clueText(P.clues[c])}`;draw();toast(`Engine đã ghi nhận ${c} là ${L[existing]}; bàn vừa tải lại trạng thái đó. Nước vừa chọn không được tính.`,"warn");return;}
 }
 const forced=Object.entries(out.forced||{}).map(([cell,status])=>`${cell}: ${L[status]}`).join(", ");
 const msg=out.status==="CONTRADICTED"?"Engine đã chứng minh trạng thái ngược lại":out.status==="NOT_PROVABLE"?`Chưa đủ căn cứ cho ${c}.${forced?` Engine đang suy ra: ${forced}.`:" Hãy bấm Gợi ý để xem kết luận có thể chứng minh."}`:`${out.status}: ${out.message||"Nước đi không hợp lệ."}`;
 toast(msg,"warn");return;}
 const p=await api(`/api/state?id=${encodeURIComponent(P.id)}&session=${encodeURIComponent(gameSession)}`);acceptEngineState(p,c);log(`${c} ${nm(c)}: ${L[v]} (engine SAT)`);toast(solved?doneMsg():`Đúng rồi, ${nm(c)} là ${L[v].toLowerCase()}`,"ok");
 }catch(e){toast(e.message,"bad");}finally{submittingVerdict=false;$("#call").querySelectorAll("button").forEach(b=>b.disabled=false);}};
$("#bHint").onclick=async()=>{if(busy||paused||solved)return;try{const h=await api("/api/hint",{id:P.id,session:gameSession});if(h.status!=="HINT")return toast(h.message,"warn");hintCell=h.cell;assisted=true;makeHintColorGroups(h.clues||[]);hl=(h.clues||[]).flatMap(c=>P.clues[c]?clueCells(P.clues[c]):[]);draw();showHintSummary(h);}catch(e){toast(e.message,"bad");}};
async function stepOnce(){try{const r=await api("/api/step",{id:P.id,session:gameSession});if(r.status!=="ACCEPTED"){toast(r.status==="STUCK"?r.message:r.status,"warn");return false;}const p=await api(`/api/state?id=${encodeURIComponent(P.id)}&session=${encodeURIComponent(gameSession)}`);acceptEngineState(p,r.cell);log(`${r.cell} ${nm(r.cell)}: ${L[r.verdict]} (agent SAT)`);return !solved;}catch(e){toast(e.message,"bad");return false;}}
$("#bStep").onclick=()=>{if(!busy&&!paused&&!solved){assisted=true;stepOnce();}};
$("#bAuto").onclick=async()=>{if(busy){busy=false;return;}if(solved||paused)return;assisted=true;lock(true);while(busy&&await stepOnce())await sleep(1400/+$("#speed").value);lock(false);};
$("#bRestart").onclick=async()=>{if(busy)return;try{const p=await api("/api/reset",{id:P.id,session:gameSession});acceptEngineState(p);}catch(e){toast(e.message,"bad");}};
$("#file").disabled=true;$("#bLoad").disabled=true;
api("/api/puzzles").then(items=>{enginePuzzleIds=items;return startEnginePuzzle(0);}).catch(e=>toast(e.message,"bad"));
