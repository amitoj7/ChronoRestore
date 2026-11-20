import * as ort from "./ort/ort.wasm.min.mjs";

ort.env.wasm.numThreads = 1;
ort.env.wasm.wasmPaths = new URL("./ort/", import.meta.url).href;

const tile = 256;
const step = 224;
let session;

function positions(length) {
  const last = Math.max(0, length - tile);
  const starts = [];
  for (let position = 0; position < last; position += step) starts.push(position);
  starts.push(last);
  return starts;
}

function hann(length) {
  return Float32Array.from({ length }, (_, index) =>
    length === 1 ? 1 : 0.5 - 0.5 * Math.cos(2 * Math.PI * index / (length - 1)));
}

async function restore(source, width, height, refine) {
  session ??= await ort.InferenceSession.create(new URL("./detail.onnx", import.meta.url).href, {
    executionProviders: ["wasm"],
  });
  const w = Math.min(tile, width);
  const h = Math.min(tile, height);
  const padW = Math.max(32, Math.ceil(w / 16) * 16);
  const padH = Math.max(32, Math.ceil(h / 16) * 16);
  const plane = padW * padH;
  const horizontal = hann(w);
  const vertical = hann(h);
  const weights = new Float32Array(width * height);
  const sums = new Float32Array(width * height * 3);
  const views = refine ? [[false, false], [true, false], [false, true], [true, true]] : [[false, false]];

  for (const top of positions(height)) {
    for (const left of positions(width)) {
      for (const [flipX, flipY] of views) {
        const patch = new Float32Array(plane * 3);
        for (let y = 0; y < padH; y++) {
          const row = Math.min(flipY ? padH - 1 - y : y, h - 1);
          for (let x = 0; x < padW; x++) {
            const column = Math.min(flipX ? padW - 1 - x : x, w - 1);
            const index = ((top + row) * width + left + column) * 4;
            for (let channel = 0; channel < 3; channel++) {
              patch[channel * plane + y * padW + x] = source[index + channel] / 255;
            }
          }
        }
        const tensor = new ort.Tensor("float32", patch, [1, 3, padH, padW]);
        const { restoration } = await session.run({ photo: tensor });
        const prediction = restoration.data;
        for (let y = 0; y < h; y++) {
          const row = flipY ? padH - 1 - y : y;
          for (let x = 0; x < w; x++) {
            const column = flipX ? padW - 1 - x : x;
            const index = (top + y) * width + left + x;
            const weight = Math.max(horizontal[x] * vertical[y], 0.01);
            weights[index] += weight;
            for (let channel = 0; channel < 3; channel++) {
              sums[index * 3 + channel] += prediction[channel * plane + row * padW + column] * weight;
            }
          }
        }
        restoration.dispose();
        tensor.dispose();
      }
    }
  }

  const result = new Uint8ClampedArray(width * height * 4);
  for (let index = 0; index < weights.length; index++) {
    for (let channel = 0; channel < 3; channel++) {
      result[index * 4 + channel] = sums[index * 3 + channel] * 255 / weights[index];
    }
    result[index * 4 + 3] = 255;
  }
  return result;
}

self.onmessage = async ({ data: { pixels, width, height, refine } }) => {
  try {
    const result = await restore(new Uint8ClampedArray(pixels), width, height, refine);
    self.postMessage({ pixels: result.buffer }, [result.buffer]);
  } catch (error) {
    console.error("Restoration failed", error);
    self.postMessage({ error: "Restoration could not run on this device. Try a smaller image or Standard mode." });
  }
};
