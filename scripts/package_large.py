"""Build a single-cell, self-contained larger Colab run."""
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
nb = json.loads((root/'notebooks/ChronoRestore_Colab.ipynb').read_text())
source = ''.join(nb['cells'][1]['source']) + '\n' + ''.join(nb['cells'][2]['source']) + '\n' + ''.join(nb['cells'][3]['source'])
source += "\nrun([sys.executable, '-u', '-m', 'chronorestore.download_large'])\nDATA = PROJECT / 'data/caltech256_restoration'\n"
s = ''.join(nb['cells'][5]['source']).replace('IMAGE_SIZE = 128', 'IMAGE_SIZE = 256').replace('BATCH_SIZE = 8', 'BATCH_SIZE = 4').replace('bsds500', 'caltech256_256px').replace("'--device', 'cuda']", "'--device', 'cuda', '--patience', '5', '--warmup-epochs', '3']")
source += '\n'+s
source += '\n'+''.join(nb['cells'][6]['source']).replace("'evaluation'", "'evaluation_caltech256'").replace("'200'", "'500'")
source += '\n'+''.join(nb['cells'][7]['source']).replace('ChronoRestore_results.zip','ChronoRestore_256px_results.zip').replace('runs/bsds500/', 'runs/caltech256_256px/').replace("'evaluation/'", "'evaluation_caltech256/'")
source = '# Larger run: 5000 train / 500 validation / 500 test, 256px, T4\n'+source
(root/'notebooks/colab_large_cell.py').write_text(source)
nb['cells'] = [{'cell_type':'markdown','metadata':{},'source':['# ChronoRestore — larger T4 run\n5000 training images, 500 validation, 500 test. 256px crops, batch 4, up to 30 epochs; stop after 5 epochs without validation improvement. Checkpoints are stored in the runtime unless USE_DRIVE is enabled. Download results before the runtime expires.\n']}, {'cell_type':'code','metadata':{},'source':source.splitlines(keepends=True),'execution_count':None,'outputs':[]}]
nb['metadata']['colab']['name']='ChronoRestore_256px.ipynb'
(root/'notebooks/ChronoRestore_256px.ipynb').write_text(json.dumps(nb,indent=1))
compile(source, 'colab_large_cell.py', 'exec')
print('Larger notebook built and syntax checked')
