// Thay thế avatar.js cũ. Giữ NGUYÊN chữ ký: window.avatar(id, name, look, status) -> chuỗi SVG
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { BeanHead } from "beanheads";

// ====== CHỈNH Ở ĐÂY ======
const ZOOM = 1.5;          // phóng to vào đầu: 1 = nguyên bản, 1.5~2 = thấy rõ kính/khẩu trang
const ZOOM_TOP_BIAS = 0.1; // 0 = bám mép trên, 1 = bám mép dưới (đầu nằm trên nên để nhỏ)
// =========================

// ⚠ Giá trị hợp lệ có thể khác theo version beanheads. Nếu hình trống/lỗi, gõ thử <BeanHead eyes=" trong VS Code để xem enum.
const SKIN   = ["light", "yellow", "brown", "dark", "red", "black"];
const HAIR_F = ["long", "bun", "pixie", "bob", "short"];
const HAIR_M = ["short", "buzz", "afro", "balding", "none"];
const HAIRC  = ["blonde", "orange", "black", "white", "brown", "blue", "pink"];
const CLOTH_F = ["dress", "vneck", "tankTop", "shirt"];
const CLOTH_M = ["shirt", "dressShirt", "vneck", "tankTop"];
const CLOTHC = ["white", "blue", "black", "green", "red"];
const CIRCLE = ["blue", "red", "green", "yellow", "orange"];
const LIP    = ["red", "purple", "pink", "green"];

// Biểu cảm theo phe
const FACE = {
  INNOCENT: {
    eyes:     ["happy", "content", "normal", "wink", "heart", "simple"],
    mouth:    ["grin", "openSmile", "lips", "tongue", "open"],
    eyebrows: ["raised", "concerned", "serious"],
  },
  CRIMINAL: {
    eyes:     ["squint", "dizzy", "leftTwitch", "simple"],
    mouth:    ["serious", "sad", "open", "lips"],
    eyebrows: ["angry", "leftLowered", "serious"],
  },
  // thẻ chưa lật: trộn đủ loại
  UNKNOWN: {
    eyes:     ["normal", "happy", "content", "wink", "simple", "squint"],
    mouth:    ["grin", "openSmile", "lips", "serious", "open", "sad"],
    eyebrows: ["raised", "concerned", "serious", "leftLowered"],
  },
};

function hash(s) { let h = 2166136261; for (const c of s) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }
const pick = (h, k, a) => a[(h >>> k) % a.length];

// ---- Tự kiểm tra: loại bỏ giá trị prop mà version beanheads của bạn không hỗ trợ ----
const BASE = {
  accessory: "none", body: "chest", circleColor: "blue", clothing: "tankTop", clothingColor: "black",
  eyebrows: "serious", eyes: "normal", facialHair: "none", graphic: "none", hair: "short", hairColor: "black",
  hat: "none", hatColor: "green", lashes: false, lipColor: "red", mask: true, faceMask: false,
  mouth: "serious", skinTone: "brown",
};
const renderBean = p => renderToStaticMarkup(React.createElement(BeanHead, p));
function works(props) { try { renderBean(props); return true; } catch (e) { return false; } }
const BASE_OK = works(BASE);
function filt(prop, list) {
  if (!BASE_OK) return list;
  const ok = list.filter(v => works({ ...BASE, [prop]: v }));
  const bad = list.filter(v => !ok.includes(v));
  if (bad.length) console.warn(`[avatar] giá trị "${prop}" không hợp lệ, đã bỏ qua:`, bad);
  return ok.length ? ok : [BASE[prop]];
}
// lipColor chỉ bị đọc khi miệng có môi (lips, grin...), nên phải thử cùng với từng kiểu miệng
const ALL_MOUTH = ["grin", "openSmile", "lips", "serious", "open", "sad", "tongue"];
function filtLip(list) {
  if (!BASE_OK) return list;
  const ok = list.filter(v => ALL_MOUTH.every(m => works({ ...BASE, mouth: m, lipColor: v }) || !works({ ...BASE, mouth: m })));
  const bad = list.filter(v => !ok.includes(v));
  if (bad.length) console.warn('[avatar] giá trị "lipColor" không hợp lệ, đã bỏ qua:', bad);
  return ok.length ? ok : ["red"];
}
const V = {
  skinTone: filt("skinTone", SKIN), hairColor: filt("hairColor", HAIRC), clothingColor: filt("clothingColor", CLOTHC),
  circleColor: filt("circleColor", CIRCLE), lipColor: filtLip(LIP),
  hairF: filt("hair", HAIR_F), hairM: filt("hair", HAIR_M),
  clothF: filt("clothing", CLOTH_F), clothM: filt("clothing", CLOTH_M),
};
for (const k of Object.keys(FACE)) {
  FACE[k].eyes = filt("eyes", FACE[k].eyes);
  FACE[k].mouth = filt("mouth", FACE[k].mouth);
  FACE[k].eyebrows = filt("eyebrows", FACE[k].eyebrows);
}

// Cắt viewBox để phóng to vào đầu
function zoomViewBox(svg) {
  return svg.replace(/viewBox="([\d.\-\s,]+)"/, (m, vb) => {
    const [x, y, w, h] = vb.trim().split(/[\s,]+/).map(Number);
    if (![x, y, w, h].every(Number.isFinite)) return m;
    const nw = w / ZOOM, nh = h / ZOOM;
    return `viewBox="${(x + (w - nw) / 2).toFixed(2)} ${(y + (h - nh) * ZOOM_TOP_BIAS).toFixed(2)} ${nw.toFixed(2)} ${nh.toFixed(2)}"`;
  });
}

const cache = new Map();

window.avatar = function (id, name, look, status) {
  const key = id + "|" + name + "|" + (status || "") + "|" + (look ? JSON.stringify(look) : "");
  if (cache.has(key)) return cache.get(key);

  const h = hash(name + id);
  const female = (look?.gender || pick(h, 0, ["f", "m", "n", "f", "m"])) !== "m";
  const crim = status === "CRIMINAL";
  const F = FACE[status] || FACE.UNKNOWN;

  const props = {
    body: female ? "breasts" : "chest",
    skinTone: look?.skin || pick(h, 3, V.skinTone),
    hair: look?.hair || pick(h, 6, female ? V.hairF : V.hairM),
    hairColor: look?.hairColor || pick(h, 9, V.hairColor),
    clothing: look?.outfit || pick(h, 12, female ? V.clothF : V.clothM),
    clothingColor: look?.outfitColor || pick(h, 15, V.clothingColor),
    circleColor: pick(h, 18, V.circleColor),
    lipColor: pick(h, 21, V.lipColor),
    lashes: female,
    facialHair: !female && (h >>> 5) % 4 === 0 ? "stubble" : "none",
    accessory: (h >>> 18) % 4 === 0 ? "roundGlasses" : "none",
    hat: "none",
    graphic: "none",
    mask: true,
    // biểu cảm: mỗi người một kiểu, cố định theo hash
    eyes: pick(h, 2, F.eyes),
    mouth: pick(h, 7, F.mouth),
    eyebrows: pick(h, 11, F.eyebrows),
    faceMask: crim,
  };
  if (crim) props.accessory = "shades"; // tội phạm: kính đen + khẩu trang

  let svg;
  try { svg = renderBean(props); }
  catch (e) {
    console.warn("[avatar] BeanHead lỗi với props này, dùng bản dự phòng:", props, e);
    svg = renderBean({ ...BASE, body: props.body, lashes: props.lashes, faceMask: crim, accessory: crim ? "shades" : "none" });
  }
  svg = svg.replace("<svg", `<svg class="av" role="img" aria-label="${name}"`);
  svg = zoomViewBox(svg);
  cache.set(key, svg);
  return svg;
};