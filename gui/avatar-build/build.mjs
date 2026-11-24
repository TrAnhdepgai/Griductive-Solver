// Gói BeanHead + React thành 1 file IIFE duy nhất cho GUI (không cần React ở runtime).
import { build } from "esbuild";

await build({
  entryPoints: ["src/avatar-bean.mjs"],
  outfile: "../static/avatar.js", // ghi đè avatar.js cũ (sửa đường dẫn nếu thư mục khác)
  bundle: true,
  format: "iife",
  platform: "browser",
  minify: true,
  define: { "process.env.NODE_ENV": '"production"' },
});
console.log("OK -> static/avatar.js");