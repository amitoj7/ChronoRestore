"""Rebuild the self-contained Colab notebook and distributable source ZIP."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
paths = sorted((ROOT / 'chronorestore').glob('*.py')) + sorted((ROOT / 'tests').glob('*.py'))
paths += [ROOT / 'README.md', ROOT / 'requirements.txt', ROOT / 'requirements-dev.txt']
paths += sorted((ROOT / 'docs').glob('*.md'))
sources = {str(p.relative_to(ROOT)): p.read_text() for p in paths}
cells = []


def cell(kind, source):
    item = {'cell_type': kind, 'id': hashlib.sha256(source.encode()).hexdigest()[:12], 'metadata': {}, 'source': source.splitlines(keepends=True)}
    if kind == 'code':
        item.update(execution_count=None, outputs=[])
    cells.append(item)


cell('markdown', '''# ChronoRestore — runnable T4 training notebook
Run all cells in order with **Python 3 / T4 GPU**. This notebook embeds the complete project source, checks the pipeline, downloads the official BSDS500 starter dataset, trains a compact GAN, and evaluates it on separate test images.

This small dataset produces a starter model. Synthetic benchmark scores do not establish restoration quality on real historical photos. The final cell downloads a results ZIP to your computer.
''')
cell('code', '#@title 1. Write the bundled project source\nfrom pathlib import Path\nimport os, subprocess, sys, json\nPROJECT = Path("/content/ChronoRestore")\nSOURCE_FILES = ' + repr(sources) + '\nfor name, source in SOURCE_FILES.items():\n    path = PROJECT / name\n    path.parent.mkdir(parents=True, exist_ok=True)\n    path.write_text(source)\nos.chdir(PROJECT)\nprint("Project ready:", PROJECT)\n')
cell('code', '''#@title 2. Prepare dependencies and confirm the GPU
def run(command):
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as process:
        for line in process.stdout:
            print(line, end='', flush=True)
        if process.wait():
            raise subprocess.CalledProcessError(process.returncode, command)
run([sys.executable, '-m', 'pip', 'install', '-q', 'scikit-image>=0.22,<1', 'gradio>=6,<7'])
import torch, torchvision
if not torch.cuda.is_available():
    raise RuntimeError('Select Runtime → Change runtime type → T4 GPU, then reconnect.')
print('Torch:', torch.__version__, '| Torchvision:', torchvision.__version__)
print('GPU:', torch.cuda.get_device_name(0))
''')
cell('code', '''#@title 3. Run regression checks before training
run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'])
''')
cell('code', '''#@title 4. Download the starter dataset (200 train / 100 validation / 200 test)
run([sys.executable, '-m', 'chronorestore.download'])
DATA = PROJECT / 'data' / 'bsds500'
''')
cell('code', '''#@title 5. Train or resume (T4 defaults)
EPOCHS = 30 #@param {type:"integer"}
IMAGE_SIZE = 128 #@param {type:"integer"}
BATCH_SIZE = 8 #@param {type:"integer"}
USE_DRIVE = False #@param {type:"boolean"}
# Drive is optional. Without it, download the final ZIP before the runtime expires.
if USE_DRIVE:
    from google.colab import drive
    drive.mount('/content/drive')
    RUNS = Path('/content/drive/MyDrive/ChronoRestore/runs/bsds500')
else:
    RUNS = PROJECT / 'runs' / 'bsds500'
command = [sys.executable, '-u', '-m', 'chronorestore.train', '--data', str(DATA / 'train'), '--val-data', str(DATA / 'val'), '--output', str(RUNS), '--epochs', str(EPOCHS), '--size', str(IMAGE_SIZE), '--batch-size', str(BATCH_SIZE), '--device', 'cuda']
if (RUNS / 'latest.pt').is_file():
    command += ['--resume', str(RUNS / 'latest.pt')]
run(command)
''')
cell('code', '''#@title 6. Evaluate the selected model on the separate test split
EVALUATION = PROJECT / 'evaluation'
run([sys.executable, '-m', 'chronorestore.evaluate', '--checkpoint', str(RUNS / 'best.pt'), '--data', str(DATA / 'test'), '--output', str(EVALUATION), '--size', str(IMAGE_SIZE), '--count', '200', '--device', 'cuda'])
from IPython.display import display
from PIL import Image
print('Comparisons: damaged / restored / clean')
for path in sorted(EVALUATION.glob('comparison_*.png'))[:3]:
    display(Image.open(path))
''')
cell('code', '''#@title 7. Download trained weights, metrics, and example restorations
import zipfile
from google.colab import files
archive = PROJECT / 'ChronoRestore_results.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
    for path in sorted(RUNS.iterdir()):
        if path.is_file() and path.suffix in ('.pt', '.csv', '.json'):
            bundle.write(path, 'runs/bsds500/' + path.name)
    for path in sorted(EVALUATION.iterdir()):
        if path.is_file():
            bundle.write(path, 'evaluation/' + path.name)
print('Download this before your runtime expires:', archive)
files.download(str(archive))
''')
cell('markdown', '''## Use your trained model
Extract the results ZIP into the local project folder, then run:
```
python -m chronorestore.restore --checkpoint runs/bsds500/best.pt --input old.jpg --output restored.png
```
For the browser demo, set `CHRONORESTORE_CHECKPOINT=runs/bsds500/best.pt` and run `python -m chronorestore.demo` locally. Training data: [official Berkeley BSDS500](https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/grouping/resources.html). Keep original photographs; generated details can be approximate.
''')
notebook = {'cells': cells, 'metadata': {'accelerator': 'GPU', 'colab': {'name': 'ChronoRestore_Colab.ipynb', 'provenance': [], 'gpuType': 'T4'}, 'kernelspec': {'display_name': 'Python 3', 'name': 'python3'}, 'language_info': {'name': 'python'}}, 'nbformat': 4, 'nbformat_minor': 5}
notebook_path = ROOT / 'notebooks' / 'ChronoRestore_Colab.ipynb'
notebook_path.write_text(json.dumps(notebook, indent=1))
with zipfile.ZipFile(ROOT / 'ChronoRestore.zip', 'w', zipfile.ZIP_DEFLATED) as bundle:
    for path in paths + sorted((ROOT / 'chronorestore/studio_assets').glob('*')) + list((ROOT / 'notebooks').glob('*.ipynb')) + list((ROOT / 'scripts').glob('*.py')) + [ROOT / '.gitignore']:
        bundle.write(path, path.relative_to(ROOT))
print('Built self-contained notebook and ChronoRestore.zip')

# Include the trained artifacts when they are available in this checkout.
if (ROOT / 'runs/bsds500/best.pt').is_file():
    with zipfile.ZipFile(ROOT / 'ChronoRestore_Ready.zip', 'w', zipfile.ZIP_DEFLATED) as ready:
        with zipfile.ZipFile(ROOT / 'ChronoRestore.zip') as source:
            for name in source.namelist():
                ready.writestr(name, source.read(name))
        for folder in ('runs/bsds500', 'runs/caltech256_256px', 'evaluation', 'evaluation_caltech256', 'runs/detail_finetune', 'evaluation_detail', 'examples'):
            for path in sorted((ROOT / folder).glob('*')):
                if path.is_file():
                    ready.write(path, path.relative_to(ROOT))
        screenshot = ROOT / 'docs/demo-screenshot.jpg'
        if screenshot.is_file():
            ready.write(screenshot, screenshot.relative_to(ROOT))
        short_report = ROOT / 'output/pdf/ChronoRestore_Image_Processing_Report.pdf'
        if short_report.is_file():
            ready.write(short_report, short_report.relative_to(ROOT))
    print('Built ChronoRestore_Ready.zip with trained weights and results')
