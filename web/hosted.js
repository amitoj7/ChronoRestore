/* Browser adapter for the hosted workbench. Inference runs off the UI thread. */
window.hostedRestore = {
  maxPixels: 2_000_000,
  async run(file, refine) {
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
      this.worker.onmessage = ({ data }) => {
        if (data.error) reject(new Error(data.error));
        else resolve(new Uint8ClampedArray(data.pixels));
      };
      this.worker.onerror = () => {
        this.worker.terminate();
        this.worker = null;
        reject(new Error("The restoration engine could not start. Try reloading this page."));
      };
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
