const hostedRestore = window.hostedRestore;
const get = id => document.getElementById(id);
const frame = get("frame");
const stage = frame.parentElement;
const reveal = get("reveal");
const modeButtons = [...document.querySelectorAll("button[data-mode]")];
const samples = [...document.querySelectorAll("[data-example]")];
const restore = get("restore");
const download = get("download");
const picker = get("file");
const drop = get("drop");
const dataset = get("dataset-photo");
const randomPhoto = get("dataset-random");
const simulate = get("simulate");
let selected = null;
let originalUrl = "";
let isUpload = false;
let simulated = null;
let usingSimulation = false;
let restoredUrl = "";
let busy = false;
let width = 256;
let height = 256;

function fitFrame() {
  const scale = Math.min(stage.clientWidth / width, stage.clientHeight / height);
  frame.style.width = `${width * scale}px`;
  frame.style.height = `${height * scale}px`;
}

function setMode(mode, hasResult = !selected || Boolean(restoredUrl)) {
  frame.dataset.mode = mode;
  for (const button of modeButtons) {
    button.setAttribute("aria-pressed", String(button.dataset.mode === mode));
    button.hidden = button.dataset.mode === "clean" && !usingSimulation;
    button.disabled = !hasResult && ["after", "split"].includes(button.dataset.mode);
    if (button.dataset.mode === "before") button.textContent = usingSimulation ? "Damaged" : "Before";
  }
  get("hint").textContent = mode === "split" ? "Drag the divider to reveal the restoration." :
    mode === "after" ? "Restored photo" :
    mode === "clean" ? "Original upload" : usingSimulation ? "Simulated damage" : "Original photo";
}

function status(message, kind = "") {
  get("status").textContent = message;
  get("status").className = `status ${kind}`;
}

function setBusy(value) {
  busy = value;
  restore.disabled = value || !selected;
  drop.disabled = value;
  dataset.disabled = randomPhoto.disabled = value;
  get("clear").disabled = value;
  simulate.disabled = value || Boolean(selected && !isUpload);
  for (const sample of samples) sample.disabled = value;
  for (const option of document.querySelectorAll('input[name="quality"]')) option.disabled = value;
}

function clearUrls() {
  if (originalUrl) URL.revokeObjectURL(originalUrl);
  if (simulated) URL.revokeObjectURL(simulated.url);
  originalUrl = "";
  simulated = null;
  showInput(false);
  get("clean").removeAttribute("src");
  clearResult();
}

function clearResult() {
  if (restoredUrl) URL.revokeObjectURL(restoredUrl);
  restoredUrl = "";
  get("after").removeAttribute("src");
  download.hidden = true;
  download.removeAttribute("href");
}

function showInput(useSimulation) {
  usingSimulation = useSimulation;
  const before = get("before");
  if (originalUrl) before.src = useSimulation ? simulated.url : originalUrl;
  before.alt = useSimulation ? "Photo with simulated damage" : "Photo before restoration";
  get("before-tag").textContent = useSimulation ? "SIMULATED DAMAGE" : "ORIGINAL";
  reveal.setAttribute("aria-label", useSimulation
    ? "Percentage of damaged photo revealed" : "Percentage of original photo revealed");
}

function showSample(sample) {
  clearUrls();
  selected = null;
  dataset.value = "";
  picker.value = "";
  get("selection").hidden = true;
  const base = `/studio/${sample.dataset.example}`;
  get("before").src = `${base}-before.webp`;
  get("after").src = `${base}-after.webp`;
  get("scene").textContent = sample.dataset.name;
  setDimensions(256, 256);
  setMode("split");
  setBusy(false);
  status("");
  for (const item of samples) item.setAttribute("aria-pressed", String(item === sample));
}

function setDimensions(w, h, wasResized = false) {
  width = w;
  height = h;
  get("dimensions").textContent = `${w} × ${h} px${wasResized ? " (resized)" : ""}`;
  fitFrame();
}

async function pick(file, scene = "Your photo") {
  if (!file || busy) return;
  if (file.size > 24 * 1024 * 1024) {
    status("Choose a file no larger than 24 MB.", "error");
    return;
  }
  if (!/\.(jpe?g|png|webp)$/i.test(file.name)) {
    status("Choose a JPG, PNG, or WebP image.", "error");
    return;
  }
  let ready = false;
  const url = URL.createObjectURL(file);
  setBusy(true);
  status("Opening photo…", "busy");
  try {
    const preview = new Image();
    preview.src = url;
    await preview.decode();
    const { naturalWidth, naturalHeight } = preview;
    if (!hostedRestore && naturalWidth * naturalHeight > 25_000_000) {
      throw new Error("Choose an image of 25 megapixels or less.");
    }
    const prepared = hostedRestore ? await hostedRestore.prepare(file, preview) :
      { file, width: naturalWidth, height: naturalHeight };
    clearUrls();
    selected = prepared.file;
    isUpload = scene === "Your photo";
    originalUrl = url;
    get("clean").src = url;
    get("before").src = url;
    get("after").removeAttribute("src");
    get("scene").textContent = scene;
    if (scene === "Your photo") dataset.value = "";
    get("filename").textContent = file.name;
    get("selection").hidden = false;
    for (const sample of samples) sample.setAttribute("aria-pressed", "false");
    setDimensions(prepared.width, prepared.height, prepared.file !== file);
    setMode("before", false);
    ready = true;
  } catch (error) {
    URL.revokeObjectURL(url);
    status(error instanceof DOMException ? "This image could not be opened." : error.message, "error");
  } finally {
    setBusy(false);
  }
  if (ready) await restoreSelected();
}

async function restoreOnServer(file, refine) {
  const response = await fetch(`/api/restore?refine=${refine}`, {
    method: "POST", headers: {"Content-Type": "application/octet-stream"}, body: file,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Restoration failed. Try again.");
  }
  return response.blob();
}

async function restoreSelected() {
  if (busy || !selected) return;
  setBusy(true);
  status("Restoring your photo…", "busy");
  const start = performance.now();
  try {
    const refine = document.querySelector('input[name="quality"]:checked').value === "refine";
    const useSimulation = isUpload && simulate.checked;
    if (useSimulation && !simulated) {
      status("Simulating damage…", "busy");
      const file = await simulatePhotoDamage(selected);
      simulated = { file, url: URL.createObjectURL(file) };
    }
    if (useSimulation !== usingSimulation) {
      clearResult();
      showInput(useSimulation);
      setMode("before");
    }
    status(hostedRestore ? "Loading restoration model…" : "Restoring your photo…", "busy");
    const input = useSimulation ? simulated.file : selected;
    const progress = percent => status(`Restoring your photo… ${percent}%`, "busy");
    const blob = hostedRestore ? await hostedRestore.run(input, refine, progress) : await restoreOnServer(input, refine);
    const url = URL.createObjectURL(blob);
    const after = new Image();
    after.src = url;
    try {
      await after.decode();
    } catch (error) {
      URL.revokeObjectURL(url);
      throw error;
    }
    if (restoredUrl) URL.revokeObjectURL(restoredUrl);
    restoredUrl = url;
    get("after").src = url;
    download.href = url;
    download.download = `${selected.name.replace(/\.[^.]+$/, "")}-restored.png`;
    download.hidden = false;
    setMode("split");
    status(`Comparison ready · ${((performance.now() - start) / 1000).toFixed(1)} s.`);
    const previewBounds = stage.getBoundingClientRect();
    if (previewBounds.bottom < 110 || previewBounds.top > innerHeight - 80) {
      get("workspace").scrollIntoView({block: "start"});
    }
  } catch (error) {
    status(error.message || "Restoration failed. Try again.", "error");
  } finally {
    setBusy(false);
  }
}

restore.addEventListener("click", restoreSelected);
simulate.addEventListener("change", () => {
  if (selected && isUpload) restoreSelected();
});

async function loadDatasetPhoto() {
  if (busy || !dataset.value) return;
  const id = dataset.value;
  const title = dataset.selectedOptions[0].textContent;
  let file;
  setBusy(true);
  status("Opening dataset photo…", "busy");
  try {
    const response = await fetch(`/studio/bsds-${id}-damaged.webp`);
    if (!response.ok) throw new Error("Could not open the dataset photo. Try again.");
    file = new File([await response.blob()], `bsds-${title.split(" ")[0]}.webp`, {type: "image/webp"});
  } catch (error) {
    status(error.message, "error");
  } finally {
    setBusy(false);
  }
  if (file) await pick(file, `BSDS500 · ${title}`);
}

dataset.addEventListener("change", loadDatasetPhoto);
randomPhoto.addEventListener("click", () => {
  const choices = [...dataset.options].filter(option => option.value && option.value !== dataset.value);
  dataset.value = choices[Math.floor(Math.random() * choices.length)].value;
  loadDatasetPhoto();
});

drop.addEventListener("click", () => picker.click());
picker.addEventListener("change", () => {
  pick(picker.files[0]);
  picker.value = "";
});
drop.addEventListener("dragover", event => {
  event.preventDefault();
  if (!busy) drop.classList.add("dragging");
});
drop.addEventListener("dragleave", () => drop.classList.remove("dragging"));
drop.addEventListener("drop", event => {
  event.preventDefault();
  drop.classList.remove("dragging");
  pick(event.dataTransfer.files[0]);
});
get("clear").addEventListener("click", () => {
  showSample(samples[0]);
  drop.focus();
});
for (const sample of samples) sample.addEventListener("click", () => showSample(sample));
for (const button of modeButtons) button.addEventListener("click", () => setMode(button.dataset.mode));
reveal.addEventListener("input", () => frame.style.setProperty("--reveal", `${reveal.value}%`));
const requestedSample = new URLSearchParams(location.search).get("sample");
const linkedSample = samples.find(sample => sample.dataset.example === requestedSample);
if (linkedSample) showSample(linkedSample);
new ResizeObserver(fitFrame).observe(stage);
fitFrame();

const stages = document.querySelectorAll("[data-stage]");
const processPhoto = get("process-photo");
for (const button of stages) {
  button.addEventListener("click", async () => {
    for (const step of stages) step.setAttribute("aria-pressed", String(step === button));
    processPhoto.src = `/studio/boathouse-${button.dataset.stage}.webp`;
    processPhoto.alt = button.querySelector("strong").textContent;
    if (!matchMedia("(prefers-reduced-motion: reduce)").matches) {
      await processPhoto.decode().catch(() => {});
      processPhoto.animate([{opacity: 0.65}, {opacity: 1}], {duration: 220});
    }
  });
}

const metricButtons = document.querySelectorAll("[data-metric]");
const metrics = {
  psnr: ["Peak signal-to-noise ratio. Higher is better.", 32, 2, " dB"],
  ssim: ["Structural similarity. Higher is better.", 1, 4, ""],
  edge_mae: ["Mean error in horizontal and vertical pixel differences. Lower is better.", .03, 4, ""],
};

fetch("/studio/detail-benchmark.json").then(response => {
  if (!response.ok) throw new Error("Benchmark unavailable");
  return response.json();
}).then(benchmark => {
  function showMetric(key) {
    const [description, minimumScale, digits, unit] = metrics[key];
    get("metric-description").textContent = description;
    const rows = Object.entries(benchmark.mean).map(([method, values]) => ({method, ...values}));
    const max = Math.max(minimumScale, ...rows.map(row => row[key]));
    get("chart").replaceChildren(...rows.map(row => {
      const item = document.createElement("div");
      item.className = "chart-row";
      item.innerHTML = '<span></span><span class="track" aria-hidden="true"><span class="bar"></span></span><strong></strong>';
      item.firstChild.textContent = row.method;
      const bar = item.querySelector(".bar");
      bar.style.width = `${100 * row[key] / max}%`;
      bar.classList.toggle("refined", row.method === "Detail + Refine");
      item.lastChild.textContent = `${row[key].toFixed(digits)}${unit}`;
      return item;
    }));
    for (const button of metricButtons) button.setAttribute("aria-pressed", String(button.dataset.metric === key));
  }
  for (const button of metricButtons) button.addEventListener("click", () => showMetric(button.dataset.metric));
  showMetric("psnr");
}).catch(() => { get("chart").textContent = "The benchmark data could not be loaded."; });

if (!matchMedia("(prefers-reduced-motion: reduce)").matches) {
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        entry.target.classList.add("in-view");
        observer.unobserve(entry.target);
      }
    }
  }, {threshold: 0.08});
  for (const section of document.querySelectorAll("[data-reveal]")) {
    section.classList.add("reveal-ready");
    observer.observe(section);
  }
  let pending = false;
  const updateProgress = () => {
    const distance = document.documentElement.scrollHeight - innerHeight;
    document.querySelector(".top").style.setProperty("--reading", String(distance > 0 ? scrollY / distance : 0));
    pending = false;
  };
  addEventListener("scroll", () => {
    if (!pending) requestAnimationFrame(updateProgress);
    pending = true;
  }, {passive: true});
  updateProgress();
}
