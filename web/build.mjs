import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";

const dist = new URL("../dist/", import.meta.url);
const studio = new URL("studio/", dist);
const assets = new URL("../chronorestore/studio_assets/", import.meta.url);
const ort = new URL("../node_modules/onnxruntime-web/dist/", import.meta.url);

await rm(dist, { recursive: true, force: true });
await cp(assets, studio, { recursive: true });
await cp(new URL("archive.html", assets), new URL("index.html", dist));
const workbench = await readFile(new URL("index.html", assets), "utf8");
await writeFile(new URL("workbench.html", dist), workbench
  .replace('<script src="/studio/studio.js" defer></script>', '<script src="/studio/hosted.js" defer></script>\n  <script src="/studio/studio.js" defer></script>')
  .replace("Running locally", "Restores in your browser"));
for (const name of ["hosted.js", "restore-worker.mjs", "models/detail.onnx"]) {
  await cp(new URL(name, import.meta.url), new URL(name.split("/").pop(), studio));
}
await mkdir(new URL("ort/", studio), { recursive: true });
for (const name of ["ort.wasm.min.mjs", "ort-wasm-simd-threaded.mjs", "ort-wasm-simd-threaded.wasm"]) {
  await cp(new URL(name, ort), new URL(`ort/${name}`, studio));
}
