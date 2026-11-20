"""Upload-and-compare Gradio interface, loaded only when launched."""
import os
from pathlib import Path
from .restore import load_generator, restore_image


def checkpoint_path(checkpoint=None):
    default = next((path for path in ("runs/detail_finetune/best.pt", "runs/caltech256_256px/best.pt", "runs/bsds500/best.pt", "runs/best.pt") if Path(path).is_file()), "runs/best.pt")
    checkpoint = Path(checkpoint or os.environ.get("CHRONORESTORE_CHECKPOINT", default))
    if not checkpoint.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint}. Train first or set CHRONORESTORE_CHECKPOINT.")
    return checkpoint


def create_app(checkpoint=None):
    import gradio as gr

    model = load_generator(checkpoint_path(checkpoint))

    def run(image):
        try:
            return restore_image(image, model)
        except (ValueError, RuntimeError) as exc:
            raise gr.Error(str(exc)) from exc

    with gr.Blocks(title="ChronoRestore") as app:
        gr.Markdown("# ChronoRestore\nRestore an old photograph and compare the result. Keep the original: reconstructed details may be approximate.")
        with gr.Row():
            source = gr.Image(type="pil", label="Old photo")
            result = gr.Image(type="pil", label="Restored photo", format="png")
        gr.Button("Restore photo", variant="primary").click(run, inputs=source, outputs=result, concurrency_limit=1)
    return app.queue(default_concurrency_limit=1)


if __name__ == "__main__":
    import uvicorn
    from .studio import create_studio

    uvicorn.run(create_studio(), host="127.0.0.1", port=7860)
