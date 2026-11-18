// Browser adapter: all game state and deductions come from the team's Python engine.
const API_BASE = location.port === "8001" ? "" : "http://127.0.0.1:8001";
const api = async (path, body) => {
  let r;
  try { r = await fetch(API_BASE + path, body ? {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)} : {}); }
  catch (_) { throw Error("Chưa kết nối engine. Hãy chạy: python -m src.engine.gui_server"); }
  const type = r.headers.get("content-type") || "";
  if (!type.includes("application/json")) throw Error("API trả về trang HTML. Hãy chạy GUI qua python -m src.engine.gui_server (cổng 8001).");
  const data = await r.json(); if(!r.ok) throw Error(data.error || "Lỗi kết nối engine"); return data;
};
let enginePuzzleIds=[],gameSession=null;
const plainClueText=clueText;
const legacyDraw=draw;
draw=function(flipped){
  legacyDraw();
  document.querySelectorAll("#board .cell").forEach(card=>{
    const c=card.dataset.c;
    if(!rev[c]||!P.clues[c])return;
    card.classList.add("has-clue");
    const note=document.createElement("span");note.className="inline-clue";note.textContent=plainClueText(P.clues[c]);
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
$("#clue").closest(".card").hidden=true;
$(".side").append($("#toast"));
function acceptEngineState(p,explicitFlip=null){
  if (!curDate) { curDate=today(); viewMon=monday(curDate); }
  const sameSession=gameSession&&gameSession===p.session;
  const newlyFlipped=sameSession?Object.keys(p.revealed||{}).find(c=>!rev[c]):null;
  const flipped=explicitFlip||newlyFlipped;
  P=p; gameSession=p.session; N=p.size; cells=Object.keys(p.characters); rev={...p.revealed};
  P.initial_revealed=Object.keys(rev); solved=Object.keys(rev).length===cells.length;
  steps=p.steps||0; sat=0; sel=null; hl=flipped&&P.clues[flipped]?clueCells(P.clues[flipped]):[]; hintCell=null;
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
pick=async function(c){if(busy||paused)return;sel=c;hintCell=null;hl=[];
 if(rev[c]){$("#clue").innerHTML=`<b>${nm(c)} (${c}):</b> ${clueText(P.clues[c])}`;hl=clueCells(P.clues[c]);$("#call").innerHTML="";}
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
$("#bHint").onclick=async()=>{if(busy||paused||solved)return;try{const h=await api("/api/hint",{id:P.id,session:gameSession});if(h.status!=="HINT")return toast(h.message,"warn");hintCell=h.cell;assisted=true;hl=(h.clues||[]).flatMap(c=>P.clues[c]?clueCells(P.clues[c]):[]);draw();toast(`Gợi ý: ${h.cell} là ${L[h.verdict].toLowerCase()}`,"warn");}catch(e){toast(e.message,"bad");}};
async function stepOnce(){try{const r=await api("/api/step",{id:P.id,session:gameSession});if(r.status!=="ACCEPTED"){toast(r.status==="STUCK"?r.message:r.status,"warn");return false;}const p=await api(`/api/state?id=${encodeURIComponent(P.id)}&session=${encodeURIComponent(gameSession)}`);acceptEngineState(p,r.cell);log(`${r.cell} ${nm(r.cell)}: ${L[r.verdict]} (agent SAT)`);return !solved;}catch(e){toast(e.message,"bad");return false;}}
$("#bStep").onclick=()=>{if(!busy&&!paused&&!solved){assisted=true;stepOnce();}};
$("#bAuto").onclick=async()=>{if(busy){busy=false;return;}if(solved||paused)return;assisted=true;lock(true);while(busy&&await stepOnce())await sleep(1400/+$("#speed").value);lock(false);};
$("#bRestart").onclick=async()=>{if(busy)return;try{const p=await api("/api/reset",{id:P.id,session:gameSession});acceptEngineState(p);}catch(e){toast(e.message,"bad");}};
$("#file").disabled=true;$("#bLoad").disabled=true;
api("/api/puzzles").then(items=>{enginePuzzleIds=items;return startEnginePuzzle(0);}).catch(e=>toast(e.message,"bad"));
