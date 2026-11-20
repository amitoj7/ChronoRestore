(() => {
  const motion = matchMedia("(pointer:fine) and (prefers-reduced-motion:no-preference)");
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  canvas.className = "splash-cursor";
  canvas.setAttribute("aria-hidden", "true");
  document.body.append(canvas);

  const lightPage = document.getElementById("workspace") !== null;
  const palette = lightPage ? ["178,64,44", "213,113,47", "143,60,90"] :
    ["255,94,60", "255,173,90", "221,74,111", "255,220,163"];
  const brushes = palette.map(color => {
    const texture = document.createElement("canvas");
    texture.width = texture.height = 64;
    const brush = texture.getContext("2d");
    const gradient = brush.createRadialGradient(32, 32, 1, 32, 32, 32);
    gradient.addColorStop(0, `rgba(${color},.86)`);
    gradient.addColorStop(.36, `rgba(${color},.47)`);
    gradient.addColorStop(.76, `rgba(${color},.11)`);
    gradient.addColorStop(1, `rgba(${color},0)`);
    brush.fillStyle = gradient;
    brush.fillRect(0, 0, 64, 64);
    return texture;
  });

  const ink = [];
  const waves = [];
  let last, width, height;
  let frame = 0, previous = 0, distance = 0;

  function resize() {
    width = innerWidth;
    height = innerHeight;
    const density = Math.min(devicePixelRatio || 1, 1.25);
    canvas.width = Math.round(width * density);
    canvas.height = Math.round(height * density);
    ctx.setTransform(density, 0, 0, density, 0, 0);
    last = null;
  }

  function dab(x, y, vx, vy, radius, color, life) {
    ink.push({x, y, vx, vy, radius, color, life, age: 0, curl: (Math.random() - .5) * .22});
  }

  function draw(time) {
    frame = 0;
    const dt = Math.min(2.4, (time - (previous || time - 16.7)) / 16.7);
    previous = time;
    ctx.clearRect(0, 0, width, height);
    ctx.globalCompositeOperation = lightPage ? "source-over" : "screen";
    for (let i = ink.length - 1; i >= 0; i--) {
      const drop = ink[i];
      drop.age += dt;
      if (drop.age >= drop.life) {
        ink.splice(i, 1);
        continue;
      }
      const t = drop.age / drop.life;
      const angle = drop.curl * dt;
      const drag = .965 ** dt;
      const vx = drop.vx * Math.cos(angle) - drop.vy * Math.sin(angle);
      drop.vy = (drop.vx * Math.sin(angle) + drop.vy * Math.cos(angle)) * drag;
      drop.vx = vx * drag;
      drop.x += drop.vx * dt;
      drop.y += drop.vy * dt;
      const radius = drop.radius * (1 + t * .48);
      const length = radius * (1 + Math.hypot(drop.vx, drop.vy) * .075);
      ctx.globalAlpha = (lightPage ? .38 : .68) * (1 - t) ** 1.6;
      ctx.save();
      ctx.translate(drop.x, drop.y);
      ctx.rotate(Math.atan2(drop.vy, drop.vx));
      ctx.drawImage(brushes[drop.color], -length, -radius, length * 2, radius * 2);
      ctx.restore();
    }
    for (let i = waves.length - 1; i >= 0; i--) {
      const wave = waves[i];
      wave.age += dt;
      if (wave.age >= 27) {
        waves.splice(i, 1);
        continue;
      }
      const t = wave.age / 27;
      ctx.globalAlpha = .57 * (1 - t) ** 2;
      ctx.strokeStyle = lightPage ? "#ac4933" : "#ffb474";
      ctx.lineWidth = 1.3;
      ctx.beginPath();
      ctx.arc(wave.x, wave.y, 5 + 39 * (1 - (1 - t) ** 2), 0, Math.PI * 2);
      ctx.stroke();
    }
    if (ink.length || waves.length) schedule();
    else previous = 0;
  }

  function schedule() {
    if (ink.length > 155) ink.splice(0, ink.length - 155);
    if (!frame) frame = requestAnimationFrame(draw);
  }

  function reset() {
    cancelAnimationFrame(frame);
    frame = previous = 0;
    ink.length = waves.length = 0;
    last = null;
    ctx.clearRect(0, 0, width, height);
  }

  resize();
  addEventListener("resize", resize, {passive: true});
  addEventListener("blur", reset);
  motion.addEventListener("change", reset);
  document.documentElement.addEventListener("pointerleave", () => { last = null; });

  addEventListener("pointermove", event => {
    if (!motion.matches || event.pointerType !== "mouse") return;
    const {clientX: x, clientY: y, timeStamp: time} = event;
    const prior = last;
    last = {x, y, time};
    if (!prior || time - prior.time > 180) return;
    const dx = x - prior.x, dy = y - prior.y;
    const length = Math.hypot(dx, dy);
    if (length < 3) return;
    const count = Math.min(9, Math.ceil(length / 8));
    for (let i = 1; i <= count; i++) {
      const along = i / count;
      distance += length / count;
      const color = Math.floor(distance / 42) % brushes.length;
      const swirl = Math.sin(distance * .11) * 2.6;
      dab(prior.x + dx * along, prior.y + dy * along,
          dx / length * 2 - dy / length * swirl, dy / length * 2 + dx / length * swirl,
          9 + Math.min(length, 70) * .14, color, 25 + Math.random() * 13);
    }
    schedule();
  }, {passive: true});

  addEventListener("pointerdown", event => {
    if (!motion.matches || event.pointerType !== "mouse" || event.button !== 0) return;
    const {clientX: x, clientY: y} = event;
    waves.push({x, y, age: 0});
    for (let i = 0; i < 27; i++) {
      const angle = i / 27 * Math.PI * 2;
      const speed = 1.7 + Math.random() * 5;
      dab(x, y, Math.cos(angle) * speed, Math.sin(angle) * speed,
          4 + Math.random() * 12, i % brushes.length, 20 + Math.random() * 20);
    }
    schedule();
  }, {passive: true});
})();
