/* Browser adapter for the hosted workbench. Inference runs off the UI thread. */
window.hostedRestore = {
  maxPixels: 2_000_000,
  async prepare(file, preview) {
    const { naturalWidth, naturalHeight } = preview;
    const scale = Math.min(1, Math.sqrt(this.maxPixels / (naturalWidth * naturalHeight)),
      2048 / Math.max(naturalWidth, naturalHeight));
    const width = Math.max(1, Math.floor(naturalWidth * scale));
    const height = Math.max(1, Math.floor(naturalHeight * scale));
    if (scale === 1) return { file, width, height };

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    context.imageSmoothingQuality = "high";
    context.drawImage(preview, 0, 0, width, height);
    const resized = await new Promise(resolve => canvas.toBlob(resolve, "image/png"));
    if (!resized) throw new Error("This photo could not be resized.");
    return { file: new File([resized], file.name, { type: resized.type }), width, height };
  },
  async run(file, refine, onProgress) {
    const image = await createImageBitmap(file);
    const canvas = document.createElement("canvas");
    canvas.width = image.width;
    canvas.height = image.height;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    context.drawImage(image, 0, 0);
    image.close();
    const source = context.getImageData(0, 0, canvas.width, canvas.height);

    this.worker ??= new Worker("/studio/restore-worker.mjs", { type: "module" });
    const pixels = await new Promise((resolve, reject) => {
      let timer;
      const failed = message => {
        clearTimeout(timer);
        this.worker.terminate();
        this.worker = null;
        reject(new Error(message));
      };
      const resetTimer = () => {
        clearTimeout(timer);
        timer = setTimeout(() => failed("Restoration stopped responding. Try again or choose Standard mode."), 45_000);
      };
      resetTimer();
      this.worker.onmessage = ({ data }) => {
        if (data.progress !== undefined) {
          resetTimer();
          onProgress(data.progress);
          return;
        }
        clearTimeout(timer);
        if (data.error) reject(new Error(data.error));
        else resolve(new Uint8ClampedArray(data.pixels));
      };
      this.worker.onerror = () => failed("The restoration engine could not start. Try again.");
      this.worker.postMessage(
        { pixels: source.data.buffer, width: canvas.width, height: canvas.height, refine },
        [source.data.buffer],
      );
    });

    context.putImageData(new ImageData(pixels, canvas.width, canvas.height), 0, 0);
    return new Promise((resolve, reject) => {
      canvas.toBlob(blob => {
        if (blob) resolve(blob);
        else reject(new Error("The restored photo could not be encoded."));
      }, "image/png");
    });
  },
};
