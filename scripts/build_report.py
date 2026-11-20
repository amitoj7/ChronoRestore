"""Render the final ChronoRestore academic report with fixed, inspected pages."""
from pathlib import Path
import csv, json, math
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf/ChronoRestore_Project_Report.pdf'
W,H=A4
INK=HexColor('#142337'); MUTED=HexColor('#55677a'); RED=HexColor('#ad2831'); PALE=HexColor('#f2f5f7'); LINE=HexColor('#d5dfe5'); GREEN=HexColor('#0c775e'); BLUE=HexColor('#286eaa')
LEFT=58; RIGHT=W-58; CW=RIGHT-LEFT
MET=json.loads((ROOT/'evaluation_caltech256/metrics.json').read_text()); OLD=json.loads((ROOT/'evaluation/metrics.json').read_text())
HISTORY=list(csv.DictReader((ROOT/'runs/caltech256_256px/losses.csv').open()))
C=canvas.Canvas(str(OUT),pagesize=A4,pageCompression=1)
C.setTitle('ChronoRestore: Old Photograph Restoration Using a Compact GAN')
C.setAuthor('Amitoj Singh')
C.setSubject('Experiential Learning Project Report, Thapar Institute of Engineering and Technology')
PAGES=[]; page_no=0; y=0

def text(x, yy, s, size=10, font='Helvetica', color=INK):
    C.setFillColor(color); C.setFont(font,size); C.drawString(x,yy,s)
def center(yy,s,size=10,font='Helvetica',color=INK):
    C.setFillColor(color); C.setFont(font,size); C.drawCentredString(W/2,yy,s)
def line(x1,y1,x2,y2,color=LINE,width=0.8):
    C.setStrokeColor(color); C.setLineWidth(width); C.line(x1,y1,x2,y2)
def box(x,yy,w,h,fill=PALE,stroke=LINE,r=6):
    C.setFillColor(fill); C.setStrokeColor(stroke); C.roundRect(x,yy,w,h,r,stroke=1,fill=1)
def arrow(x1,y1,x2,y2,color=MUTED,width=1.2):
    line(x1,y1,x2,y2,color,width)
    a=math.atan2(y2-y1,x2-x1); d=6
    path=C.beginPath();path.moveTo(x2,y2);path.lineTo(x2-d*math.cos(a-.55),y2-d*math.sin(a-.55));path.lineTo(x2-d*math.cos(a+.55),y2-d*math.sin(a+.55));path.close()
    C.setFillColor(color);C.drawPath(path,fill=1,stroke=0)
def wrap(s, max_width, size=10, font='Helvetica'):
    words=s.split(); rows=[]; row=''
    for word in words:
        if stringWidth(word,font,size)>max_width:
            if row: rows.append(row); row=''
            part=''
            for ch in word:
                if stringWidth(part+ch,font,size)>max_width:
                    rows.append(part); part=ch
                else: part+=ch
            row=part
            continue
        test=(row+' '+word).strip()
        if stringWidth(test,font,size)<=max_width: row=test
        else:
            if row: rows.append(row)
            row=word
    if row: rows.append(row)
    return rows

def para(s,size=10.7,leading=16.2,space=8,indent=0,color=INK):
    global y
    for row in wrap(s,CW-indent,size):
        text(LEFT+indent,y,row,size,color=color); y-=leading
    y-=space
    guard()
def bullet(s):
    global y
    C.setFillColor(RED); C.circle(LEFT+4,y+3,2,fill=1,stroke=0)
    para(s,indent=16,space=5)
def h2(s):
    global y
    y-=7; text(LEFT,y,s,13,'Helvetica-Bold',INK); y-=23; guard()
def h3(s):
    global y
    text(LEFT,y,s,10.5,'Helvetica-Bold',RED); y-=18; guard()
def callout(title,s):
    global y
    rows=wrap(s,CW-28,9.5); height=31+14*len(rows)
    box(LEFT,y-height+8,CW,height,HexColor('#f9f4f1'),HexColor('#e9d8d4'))
    text(LEFT+14,y-11,title,9.8,'Helvetica-Bold',RED)
    yy=y-28
    for row in rows: text(LEFT+14,yy,row,9.5);yy-=14
    y-=height+12;guard()
def guard():
    if y<58: raise RuntimeError(f'Page {page_no} content below margin: {y:.1f}')
def page(title,kicker='CHRONORESTORE | PROJECT REPORT'):
    global page_no,y
    if page_no: C.showPage()
    page_no+=1;PAGES.append(title)
    C.setFillColor(RED);C.rect(0,H-6,W,6,fill=1,stroke=0)
    text(LEFT,H-39,kicker,8.5,'Helvetica-Bold',RED)
    line(LEFT,H-50,RIGHT,H-50)
    text(LEFT,H-82,title,21,'Times-Bold',INK)
    line(LEFT,45,RIGHT,45)
    text(LEFT,31,'Amitoj Singh  |  Experiential Learning',8,color=MUTED)
    C.setFont('Helvetica',8); C.setFillColor(MUTED);C.drawRightString(RIGHT,31,f'{page_no:02d}')
    y=H-111

def table(headers,rows,widths=None,rowh=26,fonts=8.7):
    global y
    widths=widths or [CW/len(headers)]*len(headers)
    total=rowh*(len(rows)+1)
    guard_y=y-total-6
    if guard_y<57:raise RuntimeError(f'Table spills on page {page_no}: {guard_y}')
    C.setFillColor(INK);C.roundRect(LEFT,y-rowh,CW,rowh,4,fill=1,stroke=0)
    x=LEFT
    for hd,w in zip(headers,widths): text(x+8,y-rowh+8,hd,fonts,'Helvetica-Bold',HexColor('#ffffff'));x+=w
    y-=rowh
    for i,row in enumerate(rows):
        C.setFillColor(HexColor('#f5f8fa') if i%2==0 else HexColor('#ffffff'));C.rect(LEFT,y-rowh,CW,rowh,fill=1,stroke=0)
        x=LEFT
        for value,w in zip(row,widths):
            cells=wrap(str(value),w-13,fonts)
            if len(cells)>2:raise RuntimeError('Table cell overflow: '+str(value))
            for j,part in enumerate(cells): text(x+8,y-rowh+8+(len(cells)-1-j)*8,part,fonts)
            x+=w
        line(LEFT,y-rowh,RIGHT,y-rowh,LINE,.4);y-=rowh
    y-=13

def diagram_box(x,top,w,h,title,sub='',color=PALE):
    box(x,top-h,w,h,color,LINE,5)
    C.setFont('Helvetica-Bold',9); C.setFillColor(INK); C.drawCentredString(x+w/2,top-18,title)
    if sub:
        for j,row in enumerate(wrap(sub,w-12,8,'Helvetica')):
            C.setFont('Helvetica',8);C.setFillColor(MUTED);C.drawCentredString(x+w/2,top-32-j*10,row)

def code(lines):
    global y
    height=15+12*len(lines)
    box(LEFT,y-height+6,CW,height,HexColor('#172638'),HexColor('#172638'),4)
    yy=y-9
    for l in lines:
        text(LEFT+12,yy,l,8.1,'Courier',HexColor('#f1f5f7'));yy-=12
    y-=height+14;guard()

def ref(num,author,title,source,url):
    global y
    text(LEFT,y,f'[{num}]',9,'Helvetica-Bold',RED)
    rows=wrap(f'{author}. {title}. {source}.',CW-31,9.1)
    for row in rows:text(LEFT+30,y,row,9.1);y-=13
    for row in wrap(url,CW-31,8,'Helvetica'):
        text(LEFT+30,y,row,8,color=BLUE);y-=12
    y-=10;guard()

# COVER: positions modelled on the supplied title page.
page_no=1;PAGES.append('Cover')
C.setFillColor(HexColor('#ffffff'));C.rect(0,0,W,H,fill=1,stroke=0)
center(H-98,'ChronoRestore: Old Photograph',25,'Times-Bold')
center(H-132,'Restoration Using a Compact',25,'Times-Bold')
center(H-166,'Generative Adversarial Network',25,'Times-Bold')
center(H-246,'submitted in partial fulfilment of the requirements for the',11.5)
center(H-265,'completion of the course Experiential Learning',11.5)
center(H-331,'Submitted By',11.2,'Helvetica-Bold')
center(H-350,'Amitoj Singh (1024240139)',11.2)
center(H-399,'Under the Guidance of',11.2,'Helvetica-Bold')
center(H-418,'Asst. Prof. Manav Malhotra',11.2)
# Use only the logo region of the user-supplied cover. The PDF clip leaves its other text out.
logo=ImageReader('/var/folders/hs/b4c76nv95gjgydqmqlswy_dr0000gn/T/codex-clipboard-26242e9d-2f95-4c4b-94a3-9a341955a2e2.png')
ix0,iy0,iw,ih=318,655,180,168; scale=.82
clip_w,clip_h=iw*scale,ih*scale; clip_x=(W-clip_w)/2; clip_y=H-588
C.saveState();clip=C.beginPath();clip.rect(clip_x,clip_y,clip_w,clip_h);C.clipPath(clip,stroke=0)
C.drawImage(logo,clip_x-ix0*scale,clip_y-(1164-iy0-ih)*scale,width=812*scale,height=1164*scale,mask='auto')
C.restoreState()
center(H-662,'Department of Computer Science and Engineering',11.8)
center(H-681,'Thapar Institute of Engineering & Technology',11.8)
center(H-700,'PATIALA - 147004',11.8)
center(H-750,'October, 2026',11.2)

page('Abstract')
para('Photographs are vulnerable to fading, scratches, dust, compression damage and small missing patches. A practical restoration system must handle these faults together while preserving the scene that the photograph records. ChronoRestore is a compact, reproducible restoration pipeline built for this purpose. It learns from clean photographs paired with synthetically aged copies and produces a restored image through a U-Net generator. A conditional PatchGAN discriminator encourages more plausible local texture after an initial reconstruction-only warmup.')
para('The completed system includes dataset preparation, deterministic degradation, training and checkpoint recovery, held-out evaluation, tiled inference and a browser demo. Its larger run used 5,000 Caltech256 images for training, 500 for validation and 500 for final testing. Training ran for 30 epochs on a Google Colab Tesla T4 with 256 x 256 crops and a batch size of four. The validation-selected checkpoint came from epoch 28.')
para('On the 500-image synthetic test split, mean PSNR increased from 18.54 dB for damaged inputs to 26.37 dB for restored outputs. Mean SSIM increased from 0.7305 to 0.8199. The model improved PSNR on 496 images and SSIM on 458. These are controlled results against known clean targets. They do not establish equivalent performance on genuine historical scans, whose damage can be more irregular and whose original colors are often unknowable.')
h2('Keywords')
para('Old photo restoration; image-to-image translation; U-Net; conditional GAN; synthetic degradation; PSNR; SSIM; PyTorch.',space=15)
h2('What this report documents')
bullet('The problem, related work and a clear boundary between the initial proposal and implemented system.')
bullet('The complete data, network, training, inference and evaluation methods, with flowcharts and UML diagrams.')
bullet('Measured results, six side-by-side image comparisons, limitations and a reproducibility checklist.')
callout('Scope statement','ChronoRestore restores images at their original dimensions. It does not implement learned super-resolution, face-specific refinement or self-supervised adaptation to real old photographs.')

page('Contents and guide to figures')
table(['Section','Page'],[
('1. Introduction and objectives','4'),('2. Related work and design choice','5'),('3. Dataset and image processing','6'),('4. Architecture and UML','7'),('5. Training methodology','8'),('6. Inference and deployment','9'),('7. Evaluation and results','10'),('8. Visual comparisons','11-12'),('9. Discussion and conclusion','13'),('References and reproducibility','14')],[CW-75,75],rowh=29,fonts=9.5)
h2('Figures')
para('Figure 1. End-to-end workflow, page 4. Figure 2. Ordered degradation and paired-data flow, page 6. Figure 3. Network architecture and component UML, page 7. Figure 4. Training flowchart, page 8. Figure 5. Inference sequence UML, page 9. Figure 6. Validation-loss trend and benchmark comparison, page 10. Figures 7-12. Held-out image comparisons, pages 11-12.')
h2('Reading the image panels')
para('Each comparison is arranged left to right as synthetically damaged input, model restoration and original clean target. The rightmost panel is available because these are paired evaluation examples. For a real old photograph, the unknown clean target would not exist.')
callout('How to read the numbers','PSNR and SSIM on the two training runs use different datasets and crop sizes. They show performance within each experiment, not a controlled head-to-head comparison between the two checkpoints.')

page('1. Introduction and objectives')
para('An old photograph is usually affected by several processes at once. Paper and dyes shift tone; the print accumulates scratches or dust; scanning adds noise; and a compressed digital copy can blur fine detail. A single blur filter or contrast adjustment can help one fault while worsening another. The goal here is a single restoration step that learns the relationship between a damaged image and a plausible clean image.')
h2('1.1 Problem statement')
para('Given a degraded RGB image x, estimate a restored image G(x) of the same dimensions. Training needs a clean target y, but true historical photographs rarely provide one. The project therefore starts with modern clean photographs and constructs training pairs (D(y), y), where D is a controlled synthetic-aging function. The learned model is then available to process uploaded photographs through a simple interface.')
h2('1.2 Objectives')
bullet('Handle fading, warm color casts, thin scratches, dust, noise, JPEG artifacts and small masked regions in one model.')
bullet('Run on a free Colab T4 with a modest model, restartable checkpoints and an accessible demo.')
bullet('Measure reconstruction on held-out synthetic images and show actual output panels alongside the clean target.')
h2('1.3 End-to-end workflow')
top=y-4; bw=104;gap=17; start=LEFT
labels=[('Clean image','Caltech256'),('Damage model','paired input'),('Train GAN','T4 + validation'),('Select best','epoch 28')]
for i,(a,b) in enumerate(labels):
    xx=start+i*(bw+gap);diagram_box(xx,top,bw,64,a,b)
    if i<3:arrow(xx+bw+2,top-32,xx+bw+gap-2,top-32,RED)
y=top-91
text(LEFT,y,'Figure 1. End-to-end workflow.',8.6,'Helvetica-Bold',MUTED);y-=18
para('At inference, a user image enters the same trained generator through an overlapping-tile path. The comparison interface keeps the uploaded original visible next to the output. This workflow is the implemented system; it is intentionally smaller than the research-scale proposal described in the project idea.')

page('2. Related work and design choice')
para('Wan et al. [1] identify a key obstacle in historical-photo restoration: the gap between simulated corruption and the defects found in real scans. Their method addresses this with domain translation and specialized branches. ChronoRestore adopts the broad paired-restoration problem but uses a smaller conditional GAN that can be trained and inspected within the available compute.')
para('U-Net [2] motivates the encoder-decoder with skip connections that retain spatial structure. Pix2pix [3] motivates the use of a conditional discriminator for paired image translation. The project keeps these ideas but uses nearest-neighbour upsampling followed by convolution, instance normalization and spectral normalization in the discriminator.')
h2('2.1 Design comparison')
table(['Aspect','Research reference [1]','ChronoRestore'],[
('Training signal','Real and synthetic domains','Synthetic paired images'),
('Restoration','Global and local branches','Compact U-Net generator'),
('Adversarial model','Study-specific system','Conditional PatchGAN'),
('Output size','Method dependent','Same size as input'),
('Real-photo adaptation','Explicit domain translation','Not implemented')],[100,181,CW-281],rowh=43,fonts=8.6)
h2('2.2 Why the scope changed')
para('The initial concept proposed large face and scene datasets, perceptual losses, cycle consistency, super-resolution and face refinement. Those additions would require substantially more training, tuning and evaluation. The completed pipeline instead prioritizes a reproducible end-to-end experiment with a functioning interface. Reporting this boundary matters: synthetic test gains should not be presented as evidence for modules that were never built.')
callout('Research gap','A strong synthetic benchmark is useful for checking reconstruction, but it cannot tell us whether a model invents plausible yet incorrect details on an irreplaceable family photograph.')

page('3. Dataset and image processing')
para('Caltech256 [4] contains diverse object photographs. The preparation script verifies the published archive checksum, filters very small or extreme-aspect images, resizes the shorter side to 320 pixels and removes exact duplicates using a pixel hash. With a fixed shuffle seed of 17, it writes 5,000 training images, 500 validation images and 500 test images. The split is recorded in a manifest.')
para('Training resizes to a short side of 288 pixels, takes a seeded random 256 x 256 crop and sometimes flips horizontally. Validation and test evaluation use a center crop. Degradation is regenerated deterministically from a seed, so the same validation example receives the same corruption on repeat runs. The clean crop remains the target.')
h2('3.1 Ordered degradation flowchart')
top=y-2; bw=88;gap=9
steps=[('Clean RGB','target y'),('Chemical','fade + tint'),('Physical','scratches + dust'),('Digital','noise + JPEG'),('Missing','small masks')]
for i,(a,b) in enumerate(steps):
 xx=LEFT+i*(bw+gap);diagram_box(xx,top,bw,65,a,b)
 if i<4:arrow(xx+bw+1,top-32,xx+bw+gap-1,top-32,RED)
y=top-91
text(LEFT,y,'Figure 2. Ordered synthetic aging and paired-data generation.',8.6,'Helvetica-Bold',MUTED);y-=18
para('This order approximates successive changes to a print and its digitized copy. Contrast falls to 0.55-0.90 of the starting value; a warm paper tone is blended at 8%-28%; saturation is reduced; and a small number of line scratches and translucent dust spots are drawn. Gaussian noise with a sampled standard deviation of 2-10 is added before JPEG encoding at quality 35-78. In 45% of generated pairs, one to three pale elliptical regions represent limited material loss.')
h2('3.2 Data integrity and limits')
bullet('The final test images are held out from optimization and model selection; the evaluator rejects paths listed as training inputs.')
bullet('Exact-pixel duplicate removal does not rule out visually similar photos appearing across splits.')
bullet('Caltech256 is broad but is not a curated archive of aged portraits. The chosen corruption model covers selected defects, not every kind of historical damage.')

page('4. Architecture and component UML')
para('The generator accepts a three-channel degraded crop and returns three RGB channels through a sigmoid output. Four stride-two encoder stages reduce spatial resolution. Decoder stages upsample with nearest-neighbour interpolation and convolution. Skip concatenations reconnect features from the input and corresponding encoder levels. The conditional discriminator receives the degraded image concatenated with either the clean target or the generated result and predicts local real/fake logits.')
h2('4.1 Network schematic')
top=y; bw=82
nodes=[('RGB input','3 x 256²'),('Encoder','32 -> 256 ch'),('Bottleneck','16 x 16'),('Decoder','skip joins'),('RGB output','3 x 256²')]
for i,(a,b) in enumerate(nodes):
 xx=LEFT+i*98;diagram_box(xx,top,bw,62,a,b)
 if i<4:arrow(xx+bw+2,top-31,xx+96,top-31,RED)
line(LEFT+155,top-69,LEFT+370,top-69,BLUE,1.4)
arrow(LEFT+155,top-69,LEFT+155,top-57,BLUE);arrow(LEFT+370,top-69,LEFT+370,top-57,BLUE)
text(LEFT+232,top-82,'skip features',8,color=BLUE)
y=top-110
h2('4.2 UML component view')
top=y
components=[(LEFT,top,150,75,'PhotoDataset','loads clean images + pairs'),(LEFT+185,top,150,75,'Trainer','updates G and D'),(LEFT+370,top,110,75,'Checkpoint','best/latest')]
for x,t,w,h,a,b in components:diagram_box(x,t,w,h,a,b)
arrow(LEFT+152,top-38,LEFT+183,top-38);arrow(LEFT+337,top-38,LEFT+368,top-38)
diagram_box(LEFT+185,top-105,150,64,'Evaluator','PSNR / SSIM')
diagram_box(LEFT+370,top-105,110,64,'Gradio demo','upload + view')
arrow(LEFT+425,top-77,LEFT+425,top-103)
arrow(LEFT+373,top-66,LEFT+337,top-130)
y=top-190
text(LEFT,y,'Figure 3. Generator schematic and UML component view.',8.6,'Helvetica-Bold',MUTED);y-=18
para('Here G denotes the generator and D the discriminator. The trainer owns optimization, validation and checkpoint writing. Evaluation and the demo load the selected generator without modifying it. This separation keeps the output used for the final benchmark independent of interactive demo use.')

page('5. Training methodology')
para('The run used PyTorch on a Tesla T4. Generator and discriminator both use Adam with beta values (0.5, 0.999), at learning rates 0.0001 and 0.0004 respectively. The first three epochs optimize reconstruction only. Later epochs add adversarial supervision with weight 0.01. Discriminator targets use a real value of 0.95 and a fake value of 0. The generator is trained toward real logits while L1 remains its main term.')
h2('5.1 Training flowchart')
top=y; cx=W/2
for i,(a,b) in enumerate([('Load batch','degraded x, clean y'),('Warmup or GAN?','epoch <= 3'),('Update D','after warmup only'),('Update G','L1 + 0.01 x BCE'),('Validate','mean L1 on 500'),('Save checkpoint','latest + best')]):
  yy=top-i*47;diagram_box(cx-115,yy,230,38,a,b)
  if i<5:arrow(cx,yy-39,cx,yy-45,RED)
y=top-6*47-5
text(LEFT,y,'Figure 4. Training and checkpoint-selection flowchart.',8.6,'Helvetica-Bold',MUTED);y-=18
para('Validation L1 chooses the best checkpoint; the 500 test images are evaluated only afterward. The latest checkpoint contains optimizer and model states for exact continuation. Early stopping was configured with patience five, but the run completed all 30 epochs because validation kept improving through epoch 28.')
h2('5.2 Core update, simplified from the implementation')
code(['restored = generator(damaged)', 'if epoch > warmup_epochs:', '    d_loss = BCE(D(damaged, clean), 0.95) / 2', '    d_loss += BCE(D(damaged, restored.detach()), 0) / 2', '    update(discriminator, d_loss)', 'g_loss = L1(restored, clean) + 0.01 * BCE(D(damaged, restored), 1)', 'update(generator, g_loss)'])
para('During warmup, only L1 applies. The excerpt is explanatory; full code is in the source.',size=9.2)

page('6. Inference, UML sequence and deployment')
para('A user uploads a photograph to the Gradio interface. The selected generator checkpoint is loaded in evaluation mode, and inference runs without gradients. Images can be larger than the 256-pixel training crop: the restoration function divides them into overlapping 256-pixel tiles, pads edges to valid network sizes and blends each tile with a Hann weight window. The saved result has the original width and height.')
h2('6.1 UML sequence diagram')
top=y; actors=[('User',LEFT+40),('Gradio UI',LEFT+165),('Restorer',LEFT+300),('Generator',LEFT+430)]
for name,x in actors:
 text(x-24,top,name,9,'Helvetica-Bold');C.setDash(2,3);line(x,top-12,x,top-226,LINE);C.setDash()
seq=[(0,1,'upload photo',top-37),(1,2,'restore(image)',top-74),(2,3,'tile forward pass',top-111),(3,2,'restored tiles',top-148),(2,1,'blended PNG',top-185),(1,0,'show comparison',top-222)]
for a,b,label,yy in seq:
 xa=actors[a][1];xb=actors[b][1];arrow(xa,yy,xb,yy,RED if a<b else BLUE)
 text(min(xa,xb)+7,yy+6,label,8,color=MUTED)
y=top-263
text(LEFT,y,'Figure 5. UML sequence of an uploaded photo restoration.',8.6,'Helvetica-Bold',MUTED);y-=18
h2('6.2 Boundary handling')
code(['for tile in overlapping_tiles(image, size=256, overlap=32):', '    patch = pad_to_multiple_of_16(tile)', '    prediction = generator(patch)', '    output += prediction * hann_window(tile)', '    weights += hann_window(tile)', 'return output / weights'])
para('The upload remains visible beside the result. A 481 x 321 sample was processed through the running demo, and the returned PNG retained those dimensions. The command-line interface also refuses to overwrite an existing output image. Inputs above 25 megapixels must be resized first.',size=9.5)

page('7. Evaluation and measured results')
para('Final evaluation used the best validation checkpoint, seed 1701 and 256 x 256 center crops from 500 held-out Caltech256 images. Each clean image was degraded, restored and compared with its original. PSNR measures pixel error on a decibel scale; SSIM measures local structural similarity [5]. Higher values are better for both here. The reported means are averages of per-image scores.')
h2('7.1 Final held-out benchmark')
table(['Measure','Damaged input','Restored','Change'],[
('Mean PSNR (dB)','18.5401','26.3741','+7.8340'),('Mean SSIM','0.7305','0.8199','+0.0894'),('Images improved: PSNR','-','496 / 500','99.2%'),('Images improved: SSIM','-','458 / 500','91.6%')],[190,115,100,CW-405],rowh=28,fonts=8.9)
h2('7.2 Validation curve')
chart_x=LEFT+42;chart_y=y-128;chart_w=CW-70;chart_h=116
line(chart_x,chart_y,chart_x,chart_y+chart_h,INK);line(chart_x,chart_y,chart_x+chart_w,chart_y,INK)
vals=[float(r['val_l1']) for r in HISTORY];vmin=.03;vmax=.07
for level in (.03,.04,.05,.06,.07):
 yy=chart_y+(level-vmin)/(vmax-vmin)*chart_h
 line(chart_x,yy,chart_x+chart_w,yy,LINE,.5);text(LEFT-1,yy-3,f'{level:.2f}',7.5,color=MUTED)
for i in range(1,len(vals)):
 x1=chart_x+(i-1)/(len(vals)-1)*chart_w;x2=chart_x+i/(len(vals)-1)*chart_w
 yy1=chart_y+(vals[i-1]-vmin)/(vmax-vmin)*chart_h;yy2=chart_y+(vals[i]-vmin)/(vmax-vmin)*chart_h
 line(x1,yy1,x2,yy2,RED,1.8)
for epoch in (1,5,10,15,20,25,30):text(chart_x+(epoch-1)/29*chart_w-4,chart_y-14,str(epoch),7.5,color=MUTED)
text(chart_x+chart_w/2-25,chart_y-27,'Epoch',8,color=MUTED)
y=chart_y-43
para('Figure 6. Validation L1 fell from 0.0648 at epoch 1 to a minimum of 0.0359 at epoch 28. The last epoch rose slightly to 0.0363, so the epoch-28 weights were selected.')
h2('7.3 Earlier starter experiment')
para('The separate 200-image BSDS500 starter run used 128-pixel crops and improved PSNR from 18.66 to 21.43 dB, and SSIM from 0.689 to 0.723. Because its dataset and image size differ, those values are context for development rather than a direct controlled model comparison.')

for group in ((1,2,3),(4,5,6)):
 page('8. Visual comparisons' if group[0]==1 else '8. Visual comparisons, continued')
 para('The panels are 256 x 256 center crops from the held-out test set. Within each row, the order is damaged input, restored output and clean target. The middle panel shows what the model predicted; the right panel shows what it was asked to recover.',size=9.6,space=5)
 for idx in group:
  pic=ROOT/f'evaluation_caltech256/comparison_{idx}.png'; top=y-13;imgw=CW*.87;imgh=imgw/3; image_x=LEFT+(CW-imgw)/2
  C.drawImage(ImageReader(str(pic)),image_x,top-imgh,width=imgw,height=imgh)
  text(image_x,top+4,'Damaged input',8,'Helvetica-Bold',MUTED)
  text(image_x+imgw/3,top+4,'Restored',8,'Helvetica-Bold',RED)
  text(image_x+2*imgw/3,top+4,'Clean target',8,'Helvetica-Bold',GREEN)
  text(LEFT,top-imgh-15,f'Figure {6+idx}. Held-out example {idx}.',8.7,'Helvetica-Bold')
  y=top-imgh-31;guard()
 if group[0]==1:
  para('The model recovers stronger color and contrast in a landscape, a portrait and a vehicle. These examples also show the reconstruction challenge: the restored panel may be convincing while fine edges or original hues differ from the target.',size=9.5)
 else:
  para('Low-light and thin-object examples remain harder. Some scratches, pale masked areas and color shifts persist. The clean target is a reference for the synthetic test only; a real old photograph provides no such ground truth.',size=9.5)

page('9. Discussion, limitations and conclusion')
h2('9.1 What the results support')
para('The controlled experiment supports a narrow but meaningful conclusion: for the tested synthetic degradation process and held-out Caltech256 photographs, the selected network usually reconstructs images closer to the clean target. The gains appear in both mean metrics and the majority of individual samples. The visual panels show particularly clear recovery of contrast and broad color structure.')
h2('9.2 Important limitations')
bullet('Real historical scans were not used for quantitative testing. Their fading, folds and chemical damage may not resemble the synthetic training distribution.')
bullet('Restoration can change identity-sensitive details or invent texture. A plausible-looking result is not necessarily a faithful record.')
bullet('The network preserves dimensions; it does not create a higher-resolution image. The damage model uses thin lines and small elliptical patches, so large tears remain outside its training scope.')
bullet('The split excludes exact duplicate pixels, but it has not been audited for near duplicates or shared source scenes.')
bullet('PSNR and SSIM do not capture historical authenticity, color certainty or human preference. No perceptual-metric, real-photo or user study is claimed.')
h2('9.3 Practical next steps')
para('A careful next phase would assemble permission-cleared scans with varied ages and print media, label a small blind qualitative panel, document common failure cases, then refine the degradation simulator. A direct ablation of L1-only versus L1 plus GAN on one fixed split would clarify the adversarial term. Face-aware checks should focus first on preserving recognizable features rather than increasing apparent sharpness.')
h2('9.4 Conclusion')
para('ChronoRestore is a complete, compact restoration prototype: it prepares paired data, trains a conditional GAN, chooses a checkpoint by validation, evaluates on a held-out split and serves an upload-and-compare demo. Its strongest result is a reproducible synthetic benchmark. For valuable originals, the model output should be treated as an interpretation and reviewed alongside the untouched scan.')

page('References and reproducibility')
ref(1,'Z. Wan et al.','Bringing Old Photos Back to Life','Proceedings of CVPR, 2020','https://openaccess.thecvf.com/content_CVPR_2020/html/Wan_Bringing_Old_Photos_Back_to_Life_CVPR_2020_paper.html')
ref(2,'O. Ronneberger, P. Fischer and T. Brox','U-Net: Convolutional Networks for Biomedical Image Segmentation','MICCAI, 2015','https://arxiv.org/abs/1505.04597')
ref(3,'P. Isola, J.-Y. Zhu, T. Zhou and A. Efros','Image-to-Image Translation with Conditional Adversarial Networks','Proceedings of CVPR, 2017','https://openaccess.thecvf.com/content_cvpr_2017/html/Isola_Image-To-Image_Translation_With_CVPR_2017_paper.html')
ref(4,'G. Griffin, A. Holub and P. Perona','Caltech-256 Object Category Dataset','CaltechDATA, 2007','https://data.caltech.edu/records/nyy15-4j048')
ref(5,'Z. Wang, A. Bovik, H. Sheikh and E. Simoncelli','Image quality assessment: From error visibility to structural similarity','IEEE Transactions on Image Processing, 13(4), 2004','https://ece.uwaterloo.ca/~z70wang/research/ssim/')
ref(6,'P. Arbelaez et al.','Contour Detection and Hierarchical Image Segmentation','IEEE TPAMI, 2011','https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/grouping/resources.html')
h2('Reproducibility notes')
para('The source tree, self-contained Colab notebook, trained weights, split manifest, 30-epoch loss log and per-image test scores accompany this report. Key settings: seed 17 for training/data split; seed 1701 for final degradation; 256-pixel crop; batch size four; three reconstruction-only warmup epochs; GAN weight 0.01; Tesla T4; 30 epochs; best checkpoint at epoch 28. Seven regression checks passed locally and in the Colab run.',size=9.2)
C.save()
print(f'Created {OUT} with {page_no} pages')
