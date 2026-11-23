// Avatar người hoạt hình 3D (SVG, sinh theo seed). Dùng: avatar(cellId, name, look?, status?)
// look (tùy chọn trong JSON): {gender:"f|m|n", skin, hair, hairColor, outfit, outfitColor, glasses, hat}
(function(){
const INK="#231f20",SKINS=["#ffd9b8","#f6c49a","#e2a574","#c58a5c","#9b6440","#6e4329"],
HAIRC=["#2b1d1a","#4a2c1d","#7a4a2a","#e8b84a","#c4552d","#6b6b7a","#ff5fa8","#3fb6d6"],
OUTC=["#ff5fa8","#4cecff","#ffe236","#b79cff","#5bd68b","#ff9f43","#fffdf6"],
H={f:["bob","long","bun","pony","curly","crop"],m:["crop","quiff","spiky","curly","bald","quiff"],n:["crop","bob","quiff","curly","bun","spiky","pony","bald"]},
O={f:["tee","vneck","hoodie","overall"],m:["tee","collar","hoodie","overall"],n:["tee","hoodie","collar","vneck","overall"]};
function hash(s){let h=2166136261;for(const c of s){h^=c.charCodeAt(0);h=Math.imul(h,16777619)}return h>>>0}
const pick=(h,k,a)=>a[(h>>>k)%a.length];
const st=(f,w=3)=>`fill="${f}" stroke="${INK}" stroke-width="${w}" stroke-linejoin="round" stroke-linecap="round"`;
function shade(hex,a){const n=parseInt(hex.slice(1),16),f=x=>Math.max(0,Math.min(255,Math.round(x+a)));return"#"+[(n>>16)&255,(n>>8)&255,n&255].map(x=>f(x).toString(16).padStart(2,"0")).join("")}
window.avatar=function(id,name,look,status){
 const h=hash(name+id),g=look?.gender||pick(h,0,["f","m","n","f","m"]),
 skin=look?.skin||pick(h,3,SKINS),hair=look?.hair||pick(h,6,H[g]),hc=look?.hairColor||pick(h,9,HAIRC),
 outfit=look?.outfit||pick(h,12,O[g]),oc=look?.outfitColor||pick(h,15,OUTC),
 glasses=look?.glasses??(h>>>18)%4==0,hat=look?.hat??((h>>>21)%7==0&&hair!="long"&&hair!="bun"),u="a"+(h%99999);
 const hd=shade(hc,-35),od=shade(oc,-45);
 const defs=`<defs><radialGradient id="${u}s" cx=".35" cy=".3" r=".9"><stop offset="0" stop-color="${shade(skin,22)}"/><stop offset=".6" stop-color="${skin}"/><stop offset="1" stop-color="${shade(skin,-30)}"/></radialGradient>
 <linearGradient id="${u}b" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".45"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".25"/></linearGradient>
 <linearGradient id="${u}h" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${shade(hc,40)}"/><stop offset=".5" stop-color="${hc}"/><stop offset="1" stop-color="${hd}"/></linearGradient></defs>`;
 const Hf=`fill="url(#${u}h)" stroke="${INK}" stroke-width="3" stroke-linejoin="round"`;
 let back="",front="";
 switch(hair){
  case"bob":back=`<path d="M25 40C21 64 26 72 35 69L65 69C74 72 79 64 75 40Z" ${Hf}/>`;front=`<path d="M26 44C23 21 40 15 50 15C62 15 77 22 74 44C70 35 62 30 50 30C38 30 30 36 26 44Z" ${Hf}/>`;break;
  case"long":back=`<path d="M24 40C17 70 19 85 31 85L69 85C81 85 83 70 76 40Z" ${Hf}/>`;front=`<path d="M26 46C22 21 40 14 51 14C63 14 78 22 74 46C72 36 64 28 52 29C44 30 33 36 26 46Z" ${Hf}/>`;break;
  case"bun":back=`<circle cx="50" cy="14" r="9" ${Hf}/>`;front=`<path d="M28 41C28 22 40 17 50 17C62 17 72 22 72 41C66 33 58 30 50 30C42 30 34 33 28 41Z" ${Hf}/>`;break;
  case"curly":back=[[30,34],[38,25],[50,21],[62,25],[70,34],[26,46],[74,46]].map(([x,y])=>`<circle cx="${x}" cy="${y}" r="10" ${Hf}/>`).join("");front=[[37,30],[47,26],[58,27],[66,32]].map(([x,y])=>`<circle cx="${x}" cy="${y}" r="7" ${Hf}/>`).join("");break;
  case"spiky":front=`<path d="M27 42L28 22L36 30L40 13L47 28L54 11L60 28L68 15L70 30L75 21L73 42C68 34 60 31 50 31C40 31 33 34 27 42Z" ${Hf}/>`;break;
  case"pony":back=`<ellipse cx="79" cy="52" rx="7" ry="15" transform="rotate(14 79 52)" ${Hf}/>`;front=`<path d="M28 41C28 22 40 17 50 17C62 17 72 22 72 41C66 33 58 30 50 30C42 30 34 33 28 41Z" ${Hf}/>`;break;
  case"quiff":front=`<path d="M27 43C23 20 42 12 57 15C71 17 77 30 73 43C68 34 60 29 48 31C40 32 32 35 27 43Z" ${Hf}/>`;break;
  case"bald":break;
  default:front=`<path d="M28 41C28 22 40 17 50 17C62 17 72 22 72 41C66 33 58 30 50 30C42 30 34 33 28 41Z" ${Hf}/>`}
 const S=`fill="${oc}" stroke="${INK}" stroke-width="3" stroke-linejoin="round"`;
 let body=`<path d="M10 100C10 83 26 74 50 74C74 74 90 83 90 100Z" ${S}/>`,det="";
 if(outfit=="hoodie")back=`<path d="M30 78C28 64 72 64 70 78Z" fill="${od}" stroke="${INK}" stroke-width="3" stroke-linejoin="round"/>`+back,det=`<path d="M44 80L43 92M56 80L57 92" stroke="${INK}" stroke-width="2.5" stroke-linecap="round"/>`;
 if(outfit=="tee")det=`<path d="M39 74Q50 87 61 74Z" fill="${skin}" stroke="${INK}" stroke-width="3" stroke-linejoin="round"/>`;
 if(outfit=="vneck")det=`<path d="M39 74L50 92L61 74Z" fill="${skin}" stroke="${INK}" stroke-width="3" stroke-linejoin="round"/>`;
 if(outfit=="collar")det=`<path d="M38 74L50 90L52 76ZM62 74L50 90L48 76Z" fill="#fffdf6" stroke="${INK}" stroke-width="3" stroke-linejoin="round"/><path d="M50 88L46.5 92L50 100L53.5 92Z" fill="${oc==="#ff5fa8"?"#4cecff":"#ff5fa8"}" stroke="${INK}" stroke-width="2.5" stroke-linejoin="round"/>`;
 if(outfit=="overall")det=`<path d="M33 100L33 90Q33 84 40 84L60 84Q67 84 67 90L67 100ZM36 76L38 84M64 76L62 84" fill="#4a74c9" stroke="${INK}" stroke-width="3" stroke-linejoin="round"/><circle cx="38" cy="86" r="2" fill="#ffe236"/><circle cx="62" cy="86" r="2" fill="#ffe236"/>`;
 const neck=`<path d="M43 60L43 76Q50 80 57 76L57 60Z" ${st(shade(skin,-22),3)}/>`;
 const lash=g=="f"?`<path d="M36 44l-3-2M64 44l3-2" stroke="${INK}" stroke-width="2.4" stroke-linecap="round"/>`:"";
 const brow=g=="m"?3.4:2.4,
 face=`<ellipse cx="29" cy="48" rx="4.5" ry="5.5" ${st(skin,3)}/><ellipse cx="71" cy="48" rx="4.5" ry="5.5" ${st(skin,3)}/>
 <ellipse cx="50" cy="44" rx="22" ry="24" fill="url(#${u}s)" stroke="${INK}" stroke-width="3"/>
 <ellipse cx="36" cy="55" rx="5" ry="3.2" fill="#ff5fa8" opacity=".45"/><ellipse cx="64" cy="55" rx="5" ry="3.2" fill="#ff5fa8" opacity=".45"/>
 <path d="M37 39Q42 36.5 46 38.5M54 38.5Q58 36.5 63 39" stroke="${hd}" stroke-width="${brow}" fill="none" stroke-linecap="round"/>
 <ellipse cx="42" cy="47" rx="3.2" ry="4.4" fill="${INK}"/><ellipse cx="58" cy="47" rx="3.2" ry="4.4" fill="${INK}"/>
 <circle cx="43.2" cy="45.5" r="1.3" fill="#fff"/><circle cx="59.2" cy="45.5" r="1.3" fill="#fff"/>${lash}
 <path d="${status=="CRIMINAL"?"M43 58Q50 61 57 56":"M43 56Q50 63 57 56"}" stroke="${INK}" stroke-width="2.8" fill="${status=="CRIMINAL"?"none":"#fff"}" stroke-linecap="round" stroke-linejoin="round"/>
 <path d="M32 30Q36 24 44 22" stroke="#fff" stroke-width="3.2" fill="none" stroke-linecap="round" opacity=".55"/>`;
 const mask=status=="CRIMINAL"?`<path d="M28 41Q50 34 72 41L71 52Q60 50 50 52Q40 50 29 52Z" fill="#231f20"/><ellipse cx="42" cy="46.5" rx="4" ry="3.2" fill="#fff"/><ellipse cx="58" cy="46.5" rx="4" ry="3.2" fill="#fff"/><circle cx="42" cy="46.5" r="1.6" fill="${INK}"/><circle cx="58" cy="46.5" r="1.6" fill="${INK}"/>`:"";
 const gl=glasses&&status!="CRIMINAL"?`<g fill="#fff" fill-opacity=".3" stroke="${INK}" stroke-width="2.6"><circle cx="42" cy="47" r="7"/><circle cx="58" cy="47" r="7"/><path d="M49 47H51" fill="none"/></g>`:"";
 const hatS=hat?`<path d="M27 37C26 12 74 12 73 37Z" fill="${oc===OUTC[1]?"#ff5fa8":"#4cecff"}" stroke="${INK}" stroke-width="3" stroke-linejoin="round"/><rect x="25" y="32" width="50" height="8" rx="4" fill="${od}" stroke="${INK}" stroke-width="3"/><circle cx="50" cy="12" r="5" fill="#fffdf6" stroke="${INK}" stroke-width="3"/>`:"";
 return`<svg class="av" viewBox="0 0 100 100" role="img" aria-label="${name}" xmlns="http://www.w3.org/2000/svg">${defs}${back}${neck}${body}<path d="M10 100C10 83 26 74 50 74C74 74 90 83 90 100Z" fill="url(#${u}b)"/>${det}${face}${front}${hatS}${mask}${gl}</svg>`};
})();
