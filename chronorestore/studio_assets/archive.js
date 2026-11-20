const orbit = document.getElementById("orbit");
const cube = document.getElementById("cube");
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
const faces = [
  ["front", "rotateY(0deg)", [0, 6, 2, 4, 1, 8, 5, 7, 3]],
  ["right", "rotateY(90deg)", [8, 1, 5, 6, 3, 0, 7, 2, 4]],
  ["back", "rotateY(180deg)", [2, 5, 7, 1, 4, 3, 6, 0, 8]],
  ["left", "rotateY(-90deg)", [6, 0, 8, 5, 2, 4, 1, 3, 7]],
  ["top", "rotateX(90deg)", [4, 8, 1, 0, 7, 6, 3, 2, 5]],
  ["bottom", "rotateX(-90deg)", [5, 3, 0, 7, 6, 4, 2, 8, 1]],
];
for (const [name, rotation, cells] of faces) {
  const face = document.createElement("div");
  face.className = `face ${name}`;
  face.style.setProperty("--rotation", rotation);
  for (const cell of cells) {
    const tile = document.createElement("span");
    tile.className = "tile";
    tile.style.setProperty("--cell", `${cell % 3 * 50}% ${Math.floor(cell / 3) * 50}%`);
    face.append(tile);
  }
  cube.append(face);
}
const cubeStates = document.querySelectorAll("[data-cube-state]");
for (const button of cubeStates) {
  button.addEventListener("click", () => {
    orbit.dataset.state = button.dataset.cubeState;
    for (const option of cubeStates) option.setAttribute("aria-pressed", String(option === button));
  });
}
orbit.classList.add("enhanced");

let paused = false;
let visible = true;
let pitch = -19;
let yaw = -29;
let roll = -19;
let pointer = null;
let frame = 0;
let previous = 0;
let nextDirection = 0;
let speed = [0, 0, 0];
let targetSpeed = [0, 0, 0];
function draw(now) {
  frame = 0;
  const drift = !paused && visible && !document.hidden && !reducedMotion.matches;
  if (drift) {
    const step = Math.min(50, now - (previous || now)) / 1000;
    if (now >= nextDirection) {
      const sign = Math.random() < .5 ? -1 : 1;
      targetSpeed = [sign * (13 + Math.random() * 12), (Math.random() - .5) * 22, (Math.random() - .5) * 15];
      nextDirection = now + 1300 + Math.random() * 600;
    }
    speed = speed.map((value, i) => value + (targetSpeed[i] - value) * Math.min(1, step * 2.2));
    yaw = (yaw + speed[0] * step) % 360;
    pitch = Math.max(-62, Math.min(62, pitch + speed[1] * step));
    roll = Math.max(-45, Math.min(26, roll + speed[2] * step));
  }
  previous = drift ? now : 0;
  const scroll = reducedMotion.matches ? 0 : Math.min(scrollY, 650);
  cube.style.transform = `rotateZ(${roll + scroll * .016}deg) rotateX(${pitch}deg) rotateY(${yaw + scroll * .055}deg)`;
  if (drift) schedule();
}
function schedule() {
  if (!frame) frame = requestAnimationFrame(draw);
}
function toggleRotation() {
  paused = !paused;
  schedule();
}
new IntersectionObserver(([entry]) => {
  visible = entry.isIntersecting;
  if (visible) schedule();
}).observe(orbit);
document.addEventListener("visibilitychange", schedule);
schedule();

function turn(dx, dy) {
  yaw += dx;
  pitch = Math.max(-75, Math.min(75, pitch + dy));
  schedule();
}
orbit.addEventListener("pointerdown", event => {
  if (pointer || !event.isPrimary || event.button !== 0) return;
  pointer = {id: event.pointerId, x: event.clientX, y: event.clientY};
  orbit.setPointerCapture(event.pointerId);
  orbit.classList.add("dragging");
});
orbit.addEventListener("pointermove", event => {
  if (event.pointerId !== pointer?.id) return;
  const dx = event.clientX - pointer.x;
  const dy = event.clientY - pointer.y;
  turn(dx * .55, -dy * .45);
  pointer.x = event.clientX;
  pointer.y = event.clientY;
});
orbit.addEventListener("lostpointercapture", () => {
  pointer = null;
  orbit.classList.remove("dragging");
  schedule();
});
orbit.addEventListener("keydown", event => {
  if (event.code === "Space") {
    event.preventDefault();
    if (!event.repeat) toggleRotation();
    return;
  }
  const directions = {ArrowLeft: [-24, 0], ArrowRight: [24, 0], ArrowUp: [0, -15], ArrowDown: [0, 15]};
  if (!directions[event.key]) return;
  event.preventDefault();
  turn(...directions[event.key]);
});
addEventListener("scroll", () => {
  if (!pointer && scrollY <= innerHeight) schedule();
}, {passive: true});
reducedMotion.addEventListener("change", schedule);

if (!reducedMotion.matches && "IntersectionObserver" in window) {
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add("in-view");
      observer.unobserve(entry.target);
    }
  });
  for (const item of document.querySelectorAll(".reveal-item")) {
    item.classList.add("reveal-ready");
    observer.observe(item);
  }
}

const caseInfo = {
  alpine: ["Alpine railway", "Contrast returns in the waterfall and forest. Some fine scratches remain.", "19.32 → 25.49 dB PSNR"],
  engine: ["Fire engine", "The model brings back the red paint and road contrast. Small lettering remains soft.", "15.77 → 24.68 dB PSNR"],
  boathouse: ["Boathouse", "The turquoise hull becomes clearer against the steps. Some marks still show through.", "17.91 → 25.36 dB PSNR"],
  portrait: ["Portrait", "Inspect the face and clothing for changes in tone and retained detail.", "19.07 → 26.08 dB PSNR"],
  wildflower: ["Wildflower", "Compare the flower edges against the dark background.", "19.43 → 25.96 dB PSNR"],
  dog: ["Dog in the grass", "Compare the coat and grass texture after restoration.", "18.13 → 21.44 dB PSNR"],
};
const proofRange = document.getElementById("proof-range");
const proofImage = document.getElementById("proof-image");
const cases = document.querySelectorAll("[data-case]");
const before = document.getElementById("proof-before");
const after = document.getElementById("proof-after");
let proofRequest = 0;
proofRange.addEventListener("input", () => proofImage.style.setProperty("--cut", proofRange.value + "%"));
for (const item of cases) {
  item.addEventListener("click", async event => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    const request = ++proofRequest;
    const name = item.dataset.case;
    const [title, detail, score] = caseInfo[name];
    const images = ["before", "after"].map(state => {
      const image = new Image();
      image.src = `/studio/${name}-${state}.webp`;
      return image;
    });
    try {
      await Promise.all(images.map(image => image.decode()));
    } catch {
      if (request === proofRequest) location.href = item.href;
      return;
    }
    if (request !== proofRequest) return;
    before.src = images[0].src;
    after.src = images[1].src;
    before.alt = title + " with simulated damage";
    after.alt = title + " after restoration";
    document.getElementById("proof-title").textContent = title;
    document.getElementById("proof-detail").textContent = detail;
    document.getElementById("proof-score").textContent = score;
    document.getElementById("proof-link").href = item.href;
    for (const choice of cases) {
      if (choice === item) choice.setAttribute("aria-current", "true");
      else choice.removeAttribute("aria-current");
    }
    if (!reducedMotion.matches) proofImage.animate([{opacity: .75}, {opacity: 1}], {duration: 220});
  });
}

let lenis;
function updateScrollMode() {
  lenis?.destroy();
  lenis = undefined;
  if (!reducedMotion.matches && window.Lenis) {
    lenis = new Lenis({autoRaf: true, anchors: true, lerp: .13});
  }
}
reducedMotion.addEventListener("change", updateScrollMode);
updateScrollMode();
