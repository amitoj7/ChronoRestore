async function simulatePhotoDamage(file) {
  const photo = await createImageBitmap(file);
  const canvas = document.createElement("canvas");
  const { width, height } = photo;
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.fillStyle = "#f2e7d5";
  ctx.fillRect(0, 0, width, height);
  ctx.filter = "contrast(0.70) saturate(0.50)";
  ctx.drawImage(photo, 0, 0);
  photo.close();
  ctx.filter = "none";
  ctx.fillStyle = "rgba(198, 171, 126, .24)";
  ctx.fillRect(0, 0, width, height);

  const size = Math.min(width, height);
  for (let i = 0; i < 12; i++) {
    const x = Math.random() * width;
    const y = Math.random() * height;
    ctx.strokeStyle = i % 3 === 0 ? "rgba(45, 35, 27, .50)" : "rgba(250, 232, 198, .68)";
    ctx.lineWidth = Math.max(.65, size * (.0015 + Math.random() * .003));
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + (Math.random() - .5) * size * .15, y + size * (.09 + Math.random() * .3));
    ctx.stroke();
  }
  for (let i = 0; i < 90; i++) {
    ctx.fillStyle = i % 3 === 0 ? "rgba(55, 44, 35, .45)" : "rgba(245, 227, 194, .55)";
    ctx.beginPath();
    ctx.arc(Math.random() * width, Math.random() * height, Math.max(.4, size * Math.random() * .004), 0, 2 * Math.PI);
    ctx.fill();
  }

  const pixels = ctx.getImageData(0, 0, width, height);
  for (let i = 0; i < pixels.data.length; i += 4) {
    const noise = (Math.random() + Math.random() - 1) * 22;
    pixels.data[i] += noise;
    pixels.data[i + 1] += noise;
    pixels.data[i + 2] += noise;
  }
  ctx.putImageData(pixels, 0, 0);
  return new Promise((resolve, reject) => {
    canvas.toBlob(blob => {
      if (blob) resolve(blob);
      else reject(new Error("The simulated photo could not be prepared."));
    }, "image/jpeg", .58);
  });
}
