"""Build the ChronoRestore Image Processing report with three content pages."""
from io import BytesIO
import json
import re
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfmetrics import stringWidth, registerFont, registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf'
DATA = ROOT / 'evaluation_detail'
stats = json.loads((DATA/'metrics.json').read_text())['mean']
ink = HexColor('#232323')
muted = HexColor('#484848')
rule = HexColor('#777777')
W,H = A4
L = 45
R = W-L
CW = R-L
buf = BytesIO()
c = Canvas(buf, pagesize=A4)
font_root = Path('/System/Library/Fonts/Supplemental')
if (font_root/'Georgia.ttf').is_file() and (font_root/'Arial.ttf').is_file():
    for name, filename in [('Serif','Georgia.ttf'), ('Text','Arial.ttf'),
                           ('Text-Bold','Arial Bold.ttf'), ('Text-Italic','Arial Italic.ttf')]:
        registerFont(TTFont(name, str(font_root/filename)))
    registerFontFamily('Text', normal='Text', bold='Text-Bold', italic='Text-Italic')
    serif, regular, bold = 'Serif', 'Text', 'Text-Bold'
else:
    serif, regular, bold = 'Times-Roman', 'Helvetica', 'Helvetica-Bold'

body = ParagraphStyle('body', fontName=regular, fontSize=10.4, leading=15.4, textColor=ink)
note = ParagraphStyle('note', parent=body, fontSize=8.8, leading=12, textColor=muted)
cell = ParagraphStyle('cell', parent=note, textColor=ink)
center = ParagraphStyle('center', parent=cell, alignment=TA_CENTER)


def paragraph(text, x, top, width=CW, style=body):
    p = Paragraph(text, style)
    _, h = p.wrap(width, H)
    p.drawOn(c, x, top-h)
    return top-h


def label(text, x, y):
    c.setFont(bold, 8.5)
    c.setFillColor(ink)
    c.drawString(x,y,text)


def heading(text, x, y, size=20):
    c.setFont(serif, size)
    c.setFillColor(ink)
    c.drawString(x,y,text)


def section(title, y, size=15):
    heading(title,L,y,size)


def page(title, number, size=23):
    heading(title,L,H-82,size)
    c.setFont(regular, 9)
    c.setFillColor(muted)
    c.drawCentredString(W/2,31,str(number))


def table(headers, rows, widths, top):
    header_style = ParagraphStyle('table-head', parent=cell, fontName=bold)
    grid = Table([[Paragraph(x,header_style) for x in headers]] +
                 [[Paragraph(str(x),cell) for x in row] for row in rows], colWidths=widths)
    grid.setStyle(TableStyle([
        ('LINEABOVE',(0,0),(-1,0),.75,rule),
        ('LINEBELOW',(0,0),(-1,0),.45,rule),
        ('LINEBELOW',(0,-1),(-1,-1),.75,rule),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('TOPPADDING',(0,0),(-1,-1),4),
        ('BOTTOMPADDING',(0,0),(-1,-1),4),
    ]))
    _, h = grid.wrap(CW,H)
    grid.drawOn(c,L,top-h)
    return top-h


def arrow(points, dashed=False):
    c.setStrokeColor(ink)
    c.setLineWidth(.75)
    if dashed:
        c.setDash(3, 2)
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        c.line(x1, y1, x2, y2)
    c.setDash()
    from math import atan2, cos, sin
    x, y = points[-1]
    px, py = points[-2]
    angle = atan2(y-py, x-px)
    for spread in (-.52, .52):
        c.line(x, y, x-5*cos(angle+spread), y-5*sin(angle+spread))


def diagram_box(x, y, w, h, title, *, terminal=False, component=False):
    c.setStrokeColor(rule)
    c.setFillColor(white)
    c.setLineWidth(.8)
    if terminal:
        c.roundRect(x, y, w, h, h/2, fill=1, stroke=1)
    else:
        c.rect(x, y, w, h, fill=1, stroke=1)
    if component:
        c.setFillColor(muted)
        c.setFont(regular, 7)
        c.drawCentredString(x+w/2, y+h-10, '«component»')
    _, text_height = Paragraph(title, center).wrap(w-10, h)
    text_top = y + (h+text_height)/2 - (5 if component else 0)
    paragraph(title, x+5, text_top, w-10, center)


page('Abstract',1,size=16)
paragraph('ChronoRestore uses a compact generative adversarial network to restore photographs affected by fading, scratches and noise. On 200 synthetically degraded BSDS500 test images, the fine-tuned model with four-pass inference achieved 26.69 dB PSNR and 0.8478 SSIM.',L,739)
section('1. Restoration Methodology',671,23)

y_img=506
side=118
with Image.open(DATA/'comparison_1.png') as image:
    for i,title in enumerate(('Damaged input','Original + Refine','Detail + Refine','Clean reference')):
        x=L+i*((CW-side)/3)
        label(title,x,y_img+side+8)
        c.drawImage(ImageReader(image.crop((i*256,0,(i+1)*256,256))),x,y_img,side,side)
paragraph('<b>Figure 1.</b> BSDS500 test example. The Detail model suppresses several scratches on the ice. Fine fur and surface textures remain less distinct than in the clean reference.',L,493,style=note)

section('1.1 Paired Data Generation',440)
paragraph('A clean 256 × 256 crop serves as the target. The input simulates fading, colour shifts, scratches, dust and occasional pale patches. Gaussian noise and JPEG compression introduce additional artefacts.',L,426)

section('1.2 Model Training',361)
paragraph('The U-Net generator was trained for 30 epochs on 5,000 Caltech256 images using a Tesla T4. Skip connections preserve spatial detail. A conditional PatchGAN discriminator was introduced after three epochs of pixel L1 training. Epoch 28 achieved the lowest validation L1.',L,347)

section('1.3 Gradient-Aware Fine-Tuning',277)
paragraph('The Detail model was initialised from the Caltech256 checkpoint and fine-tuned on 200 BSDS500 training images for 10 epochs. The loss combines pixel and gradient errors. Epoch 10 achieved the lowest mean squared error on the 100-image validation set.',L,263)
paragraph('Detail loss = pixel L1 + 0.4 × mean(horizontal gradient L1, vertical gradient L1)',L,203,CW,center)

section('1.4 Evaluation Protocol',171)
paragraph('All methods were evaluated on the same 200 held-out BSDS500 images with identical simulated damage. Peak signal-to-noise ratio (PSNR) measures pixel fidelity, the structural similarity index (SSIM) measures structural similarity, and edge mean absolute error (MAE) measures error in local intensity gradients.',L,157)
c.showPage()

page('2. System Implementation',2)
section('2.1 Training Workflow',715)
diagram_box(L,652,85,31,'Clean crops',terminal=True)
diagram_box(151,652,106,31,'Simulate damage')
diagram_box(279,652,110,31,'Train and fine-tune')
diagram_box(413,652,137,31,'Select on validation',terminal=True)
for start, end in [(130,151),(257,279),(389,413)]:
    arrow([(start,667.5),(end,667.5)])
paragraph('<b>Figure 2.</b> Training and checkpoint selection. Caltech256 pretraining is followed by fine-tuning on BSDS500.',L,638,style=note)

section('2.2 Studio Architecture',582)
diagram_box(L,522,132,36,'Browser studio',component=True)
diagram_box(231,522,132,36,'FastAPI service',component=True)
diagram_box(R-132,522,132,36,'PyTorch restorer',component=True)
arrow([(177,540),(231,540)],dashed=True)
arrow([(363,540),(R-132,540)],dashed=True)
label('HTTP',191,547)
label('calls',378,547)
paragraph('<b>Figure 3.</b> UML component diagram. FastAPI passes the uploaded image to the restorer and returns a PNG. The browser displays it beside the input in a comparison slider.',L,507,style=note)

section('2.3 Qualitative Assessment',441)
panel = 155
with Image.open(DATA/'comparison_4.png') as image:
    for order, (index, title) in enumerate(((0,'Damaged input'),(2,'Detail + Refine'),(3,'Clean reference'))):
        x = L + order * (CW-panel)/2
        label(title,x,416)
        c.drawImage(ImageReader(image.crop((index*256,0,(index+1)*256,256))),x,252,panel,panel)
paragraph('<b>Figure 4.</b> Aircraft example from the BSDS500 test set. The restoration improves colour and contrast. A residual blemish remains near the lower-right corner.',L,238,style=note)

section('2.4 Four-Pass Inference',170)
col_gap=26
col=(CW-col_gap)/2
x2=L+col+col_gap
paragraph('For each tile, the model averages predictions from the original input and three flipped variants after reversing the flips. Overlapping predictions are blended to reduce seams.',L,154,col)
label('Listing 1. Prediction averaging',x2,145)
c.setFont('Courier',8)
c.setFillColor(ink)
for index, line in enumerate((
    'prediction = model(patches)',
    'for axes in ((-1,), (-2,), (-2, -1)):',
    '    flipped = model(patches.flip(axes))',
    '    prediction += flipped.flip(axes)',
    'prediction /= 4',
)):
    c.drawString(x2,128-index*10,line)
c.showPage()

page('3. Results and Discussion',3)
section('3.1 Controlled Benchmark',713)
paragraph('Relative to Original + Refine, Detail + Refine increased mean PSNR by 0.66 dB and reduced mean edge error by 8.3%. SSIM improved on 194 of 200 test images. Single-pass Detail also exceeded the original four-pass baseline on all three mean metrics.',L,697)
paragraph('<b>Table 1.</b> Mean restoration metrics on the BSDS500 test set.',L,634,style=note)
names=('Input','Median + autocontrast','Original','Original + Refine','Detail','Detail + Refine')
rows=[]
for name in names:
    m=stats[name]
    style = '<b>{}</b>' if name == 'Detail + Refine' else '{}'
    rows.append([style.format(x) for x in (name,f'{m["psnr"]:.2f}',f'{m["ssim"]:.4f}',f'{m["edge_mae"]:.5f}')])
bottom=table(['Method','PSNR (dB) ↑','SSIM ↑','Edge MAE ↓'],rows,[214,96,85,CW-395],618)
y=paragraph('An ablation using identical fine-tuning data and pixel L1 alone would isolate the effect of the gradient term.',L,bottom-9,style=note)
section('3.2 Comparison with Published Studies',y-22)
paragraph('<b>Table 2.</b> Published and project results under their respective protocols.',L,y-32,style=note)
papers=[
    ['Wan et al. [1], CVPR 2020','Synthetic DIV2K','23.33 / 0.690','Latent translation for old-photo restoration.'],
    ['Pik-Fix [2], WACV 2023','Degraded Pascal VOC','22.22 / 0.828','Repair with reference colorization.'],
    ['Pik-Fix [2], WACV 2023','RealOld','17.20 / 0.758','Evaluation against expert repairs.'],
    ['ChronoRestore Detail + Refine','Synthetic BSDS500','26.69 / 0.8478','Compact, single-image RGB restoration.'],
]
bottom=table(['Study','Evaluation data','PSNR / SSIM','Approach'],papers,[127,110,92,CW-329],y-47)
y=paragraph('These scores come from different datasets, degradation protocols and tasks. A direct comparison requires a common evaluation protocol.',L,bottom-9,style=note)
section('3.3 Limitations',y-22,17)
y=paragraph('Fine textures can remain blurred and some scratches persist. Evaluation on historical scans is needed to determine how well the method generalises to real damage.',L,y-34,style=note)
section('3.4 Conclusion',y-22)
y=paragraph('Under controlled synthetic degradation, fine-tuning improved both single-pass and four-pass restoration. Detail + Refine achieved the best mean PSNR, SSIM and edge MAE among the evaluated variants.',L,y-36,style=note)
section('References',y-21)
y=paragraph('[1] Wan et al., <i>Bringing Old Photos Back to Life</i>, CVPR 2020, Table 1. <link href="https://openaccess.thecvf.com/content_CVPR_2020/html/Wan_Bringing_Old_Photos_Back_to_Life_CVPR_2020_paper.html" color="#232323">Paper</link>.',L,y-27,style=note)
paragraph('[2] Xu et al., <i>Pik-Fix: Restoring and Colorizing Old Photos</i>, WACV 2023, Tables 1 and 2. <link href="https://openaccess.thecvf.com/content/WACV2023/html/Xu_Pik-Fix_Restoring_and_Colorizing_Old_Photos_WACV_2023_paper.html" color="#232323">Paper</link>.',L,y-4,style=note)
c.showPage()
c.save()

writer = PdfWriter()
cover = PdfReader(OUT/'ChronoRestore_Project_Report.pdf').pages[0]
stream = cover.get_contents().get_data()
for old, new, size in [
    ('completion of the course Experiential Learning', 'completion of the course Image Processing', 11.5),
    ('Asst. Prof. Manav Malhotra', 'Asst. Prof. Dr. Paluck Arora', 11.2),
    ('October, 2026', 'November 2026', 11.2),
]:
    pattern = rb'BT 1 0 0 1 [0-9.]+ ([0-9.]+) Tm \(' + re.escape(old.encode()) + rb'\) Tj T\* ET'
    x = (float(cover.mediabox.width) - stringWidth(new, 'Helvetica', size)) / 2
    stream, count = re.subn(pattern, lambda match: b'BT 1 0 0 1 ' + f'{x:.4f}'.encode() +
                            b' ' + match[1] + b' Tm (' + new.encode() + b') Tj T* ET', stream)
    if count != 1:
        raise ValueError(f'Could not replace cover text: {old}')
updated = DecodedStreamObject()
updated.set_data(stream)
cover[NameObject('/Contents')] = updated
writer.add_page(cover)
buf.seek(0)
for p in PdfReader(buf).pages:
    writer.add_page(p)
writer.add_metadata({'/Title':'ChronoRestore | Image Processing Project Report','/Author':'Amitoj Singh'})
writer.write(OUT/'ChronoRestore_Image_Processing_Report.pdf')
