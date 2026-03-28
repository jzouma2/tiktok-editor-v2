import os
import uuid
import json
import subprocess
import threading
import re
from flask import Flask, request, jsonify, send_file, render_template_string
from anthropic import Anthropic

app = Flask(__name__)

UPLOAD_FOLDER = "/tmp/uploads"
OUTPUT_FOLDER = "/tmp/outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

jobs = {}
anthropic_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>Jackie's Video Editor</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  :root{--cream:#faf7f2;--black:#0f0f0f;--rose:#e8927c;--rose-light:#f5d5cc;--gold:#c9a84c;--text:#2a2a2a;--muted:#888}
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'DM Sans',sans-serif;background:var(--cream);color:var(--text);min-height:100vh}
  header{background:var(--black);padding:24px 20px 20px}
  .eyebrow{font-size:10px;letter-spacing:3px;text-transform:uppercase;color:var(--rose);margin-bottom:6px;font-weight:500}
  header h1{font-family:'Playfair Display',serif;font-size:28px;color:white;line-height:1.1}
  header h1 em{font-style:italic;color:var(--rose)}
  header p{font-size:12px;color:rgba(255,255,255,0.45);margin-top:6px}
  .main{padding:20px}
  .card{background:white;border-radius:18px;padding:20px;margin-bottom:16px;box-shadow:0 2px 20px rgba(0,0,0,0.06)}
  .label{font-size:10px;letter-spacing:2px;text-transform:uppercase;color:var(--muted);font-weight:600;margin-bottom:10px}
  .upload-zone{border:2px dashed #e0d8d0;border-radius:14px;padding:32px 20px;text-align:center;cursor:pointer;transition:all 0.2s}
  .upload-zone:hover{border-color:var(--rose);background:var(--rose-light)}
  .upload-zone .icon{font-size:40px;margin-bottom:10px}
  .upload-zone p{font-size:14px;color:var(--muted)}
  .upload-zone strong{color:var(--rose)}
  input[type=file]{display:none}
  .clip-list{margin-top:12px;display:flex;flex-direction:column;gap:8px}
  .clip-item{display:flex;align-items:center;gap:10px;background:#f8f5f2;border-radius:10px;padding:10px 12px}
  .clip-icon{width:48px;height:36px;border-radius:6px;background:#e0d8d0;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:18px}
  .clip-info{flex:1;min-width:0}
  .clip-name{font-size:12px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .clip-size{font-size:11px;color:var(--muted)}
  .clip-remove{background:none;border:none;color:#ccc;font-size:18px;cursor:pointer;padding:0 4px;flex-shrink:0}
  .clip-count{font-size:12px;color:var(--rose);font-weight:600;margin-top:6px}
  .add-more{width:100%;padding:10px;border:1.5px dashed #e0d8d0;border-radius:10px;background:none;font-family:'DM Sans',sans-serif;font-size:13px;font-weight:600;color:var(--rose);cursor:pointer;margin-top:8px}
  .options-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  .opt-btn{padding:10px 8px;border-radius:10px;border:1.5px solid #eee;background:white;font-size:12px;font-weight:500;color:var(--text);cursor:pointer;text-align:center;transition:all 0.15s}
  .opt-btn.on{border-color:var(--rose);background:var(--rose-light);color:var(--rose)}
  .opt-btn .em{font-size:18px;display:block;margin-bottom:3px}
  textarea{width:100%;border:none;outline:none;font-family:'DM Sans',sans-serif;font-size:14px;color:var(--text);resize:none;background:transparent;line-height:1.6}
  textarea::placeholder{color:#ccc}
  .go-btn{width:100%;padding:16px;background:linear-gradient(135deg,var(--rose),var(--gold));color:white;border:none;border-radius:14px;font-family:'DM Sans',sans-serif;font-size:15px;font-weight:600;cursor:pointer}
  .go-btn:disabled{opacity:0.5;cursor:not-allowed}
  .progress-wrap{display:none;margin-top:20px}
  .progress-wrap.show{display:block}
  .progress-bar{height:6px;background:#eee;border-radius:4px;overflow:hidden;margin:10px 0}
  .progress-fill{height:100%;background:linear-gradient(90deg,var(--rose),var(--gold));border-radius:4px;transition:width 0.5s ease}
  .status-text{font-size:13px;color:var(--muted);text-align:center}
  .result-card{background:white;border-radius:18px;padding:20px;margin-top:20px;box-shadow:0 2px 20px rgba(0,0,0,0.06);display:none}
  .result-card.show{display:block}
  .download-btn{display:block;width:100%;padding:14px;background:var(--black);color:white;text-align:center;border-radius:12px;font-weight:600;font-size:15px;text-decoration:none;margin-top:14px}
  .tips-box{background:var(--black);border-radius:14px;padding:16px;margin-top:14px}
  .tips-box .tlabel{font-size:10px;letter-spacing:2px;text-transform:uppercase;color:var(--gold);font-weight:700;margin-bottom:8px}
  .tips-box p{font-size:13px;color:rgba(255,255,255,0.8);line-height:1.6}
  .error{background:#fff5f5;border:1px solid #fca5a5;border-radius:12px;padding:14px;font-size:13px;color:#dc2626;margin-top:16px;display:none;line-height:1.5}
  .error.show{display:block}
  video{width:100%;border-radius:12px;margin-top:12px}
</style>
</head>
<body>
<header>
  <div class="eyebrow">✦ Jackie's Studio</div>
  <h1>TikTok Video<br><em>Editor</em></h1>
  <p>Upload clips · Auto-edit · Download · Post</p>
</header>
<div class="main">
  <div class="card">
    <div class="label">Your Clips</div>
    <div class="upload-zone" id="dropZone" onclick="document.getElementById('fileInput').click()">
      <div class="icon">🎬</div>
      <p>Tap to select your clips<br><strong>Select multiple at once!</strong><br><span style="font-size:12px">Restaurant, food, drinks, scenery...</span></p>
    </div>
    <input type="file" id="fileInput" accept="video/*" multiple onchange="handleFiles(this)">
    <div class="clip-list" id="clipList"></div>
    <div class="clip-count" id="clipCount"></div>
    <button class="add-more" id="addMoreBtn" style="display:none" onclick="document.getElementById('fileInput').click()">+ Add More Clips</button>
  </div>
  <div class="card">
    <div class="label">What to edit</div>
    <div class="options-grid">
      <div class="opt-btn on" id="opt-silence" onclick="toggle('silence',this)"><span class="em">✂️</span>Cut silences</div>
      <div class="opt-btn on" id="opt-captions" onclick="toggle('captions',this)"><span class="em">💬</span>Add captions</div>
      <div class="opt-btn on" id="opt-transitions" onclick="toggle('transitions',this)"><span class="em">✨</span>Transitions</div>
      <div class="opt-btn on" id="opt-tips" onclick="toggle('tips',this)"><span class="em">🔥</span>Viral tips</div>
    </div>
  </div>
  <div class="card">
    <div class="label">Special instructions (optional)</div>
    <textarea id="instructions" rows="3" placeholder="e.g. start with restaurant exterior, highlight the pasta dish, make it fast-paced..."></textarea>
  </div>
  <button class="go-btn" id="goBtn" onclick="startEdit()" disabled>✦ Edit My Video</button>
  <div class="progress-wrap" id="progressWrap">
    <div class="status-text" id="statusText">Starting...</div>
    <div class="progress-bar"><div class="progress-fill" id="progressFill" style="width:0%"></div></div>
  </div>
  <div class="error" id="errorBox"></div>
  <div class="result-card" id="resultCard">
    <div class="label">✦ Your Edited Video</div>
    <video id="resultVideo" controls playsinline></video>
    <a class="download-btn" id="downloadBtn" href="#" download="edited_tiktok.mp4">⬇ Save to Phone</a>
    <div class="tips-box" id="tipsBox" style="display:none">
      <div class="tlabel">✦ Viral Edit Tips</div>
      <p id="tipsText"></p>
    </div>
  </div>
</div>
<script>
let files=[];let opts={silence:true,captions:true,transitions:true,tips:true};
const emojis=['🎬','🍽️','🥂','🌆','✨','🎥','🍷','🌃'];
function handleFiles(input){
  files=[...files,...Array.from(input.files)];
  renderList();document.getElementById('goBtn').disabled=files.length===0;input.value='';
}
function renderList(){
  document.getElementById('clipList').innerHTML=files.map((f,i)=>`
    <div class="clip-item">
      <div class="clip-icon">${emojis[i%emojis.length]}</div>
      <div class="clip-info"><div class="clip-name">${f.name}</div><div class="clip-size">${(f.size/1024/1024).toFixed(1)} MB</div></div>
      <button class="clip-remove" onclick="removeClip(${i})">✕</button>
    </div>`).join('');
  document.getElementById('clipCount').textContent=files.length?`${files.length} clip${files.length>1?'s':''} selected`:'';
  document.getElementById('addMoreBtn').style.display=files.length?'block':'none';
}
function removeClip(i){files.splice(i,1);renderList();document.getElementById('goBtn').disabled=files.length===0;}
function toggle(k,el){opts[k]=!opts[k];el.classList.toggle('on',opts[k]);}
async function startEdit(){
  if(!files.length)return;
  document.getElementById('goBtn').disabled=true;
  document.getElementById('progressWrap').classList.add('show');
  document.getElementById('errorBox').classList.remove('show');
  document.getElementById('resultCard').classList.remove('show');
  const fd=new FormData();
  files.forEach((f,i)=>fd.append(`video_${i}`,f));
  fd.append('clip_count',files.length);
  fd.append('options',JSON.stringify(opts));
  fd.append('instructions',document.getElementById('instructions').value);
  setProgress(5,`Uploading ${files.length} clip${files.length>1?'s':''}...`);
  try{
    const r=await fetch('/upload',{method:'POST',body:fd});
    const{job_id}=await r.json();
    setProgress(15,'Processing...');
    poll(job_id);
  }catch(e){showError('Upload failed. Please try again.');document.getElementById('goBtn').disabled=false;}
}
async function poll(id){
  const iv=setInterval(async()=>{
    try{
      const d=await(await fetch(`/status/${id}`)).json();
      setProgress(d.progress||15,d.message||'Processing...');
      if(d.status==='done'){clearInterval(iv);showResult(id,d.tips);}
      else if(d.status==='error'){clearInterval(iv);showError(d.message||'Something went wrong.');document.getElementById('goBtn').disabled=false;}
    }catch(e){clearInterval(iv);showError('Connection lost. Please try again.');}
  },2000);
}
function setProgress(p,m){document.getElementById('progressFill').style.width=p+'%';document.getElementById('statusText').textContent=m;}
function showResult(id,tips){
  const url=`/download/${id}`;
  document.getElementById('resultVideo').src=url;
  document.getElementById('downloadBtn').href=url;
  document.getElementById('resultCard').classList.add('show');
  setProgress(100,'✅ Done! Your video is ready.');
  if(tips){document.getElementById('tipsText').textContent=tips;document.getElementById('tipsBox').style.display='block';}
  document.getElementById('goBtn').disabled=false;
  document.getElementById('resultCard').scrollIntoView({behavior:'smooth'});
}
function showError(m){document.getElementById('errorBox').textContent='⚠️ '+m;document.getElementById('errorBox').classList.add('show');document.getElementById('progressWrap').classList.remove('show');}
</script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/upload', methods=['POST'])
def upload():
    clip_count = int(request.form.get('clip_count', 1))
    options = json.loads(request.form.get('options', '{}'))
    instructions = request.form.get('instructions', '')
    job_id = str(uuid.uuid4())[:8]
    clip_paths = []
    for i in range(clip_count):
        f = request.files.get(f'video_{i}')
        if f:
            p = os.path.join(UPLOAD_FOLDER, f"{job_id}_clip{i}.mp4")
            f.save(p)
            clip_paths.append(p)
    jobs[job_id] = {'status': 'processing', 'progress': 15, 'message': 'Clips received!'}
    t = threading.Thread(target=process, args=(job_id, clip_paths, options, instructions))
    t.daemon = True
    t.start()
    return jsonify({'job_id': job_id})

@app.route('/status/<job_id>')
def status(job_id):
    return jsonify(jobs.get(job_id, {'status': 'error', 'message': 'Not found'}))

@app.route('/download/<job_id>')
def download(job_id):
    p = os.path.join(OUTPUT_FOLDER, f"{job_id}_output.mp4")
    if os.path.exists(p):
        return send_file(p, as_attachment=True, download_name='edited_tiktok.mp4')
    return jsonify({'error': 'Not found'}), 404

def upd(job_id, progress, message, status='processing'):
    jobs[job_id] = {'status': status, 'progress': progress, 'message': message}

def process(job_id, clip_paths, options, instructions):
    try:
        output_path = os.path.join(OUTPUT_FOLDER, f"{job_id}_output.mp4")
        
        # Step 1: Merge clips
        if len(clip_paths) > 1:
            upd(job_id, 20, f'Stitching {len(clip_paths)} clips...')
            merged = os.path.join(UPLOAD_FOLDER, f"{job_id}_merged.mp4")
            working = merge_clips(clip_paths, merged)
        else:
            working = clip_paths[0]

        # Step 2: Cut silences
        if options.get('silence'):
            upd(job_id, 35, 'Cutting silent moments...')
            out = os.path.join(UPLOAD_FOLDER, f"{job_id}_cut.mp4")
            working = cut_silences(working, out)

        # Step 3: Add fade transitions
        if options.get('transitions'):
            upd(job_id, 50, 'Adding transitions...')
            out = os.path.join(UPLOAD_FOLDER, f"{job_id}_fade.mp4")
            working = add_fade(working, out)

        # Step 4: Add captions using ffmpeg subtitle filter with hardcoded style
        if options.get('captions'):
            upd(job_id, 65, 'Adding captions...')
            out = os.path.join(UPLOAD_FOLDER, f"{job_id}_cap.mp4")
            working = add_simple_captions(working, out)

        # Step 5: Export vertical for TikTok
        upd(job_id, 80, 'Exporting for TikTok...')
        subprocess.run([
            'ffmpeg', '-y', '-i', working,
            '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
            '-vcodec', 'libx264', '-acodec', 'aac',
            '-preset', 'fast', '-crf', '23', '-movflags', '+faststart', '-r', '30',
            output_path
        ], capture_output=True)

        # Step 6: Viral tips from Claude
        tips = None
        if options.get('tips'):
            upd(job_id, 92, 'Generating viral tips...')
            tips = get_tips(instructions, len(clip_paths))

        upd(job_id, 100, '✅ Done!', status='done')
        jobs[job_id]['tips'] = tips

    except Exception as e:
        print(f"Error: {e}")
        upd(job_id, 0, f'Error: {str(e)}', status='error')

def merge_clips(clip_paths, output_path):
    try:
        normalized = []
        for i, p in enumerate(clip_paths):
            n = p.replace('.mp4', '_n.mp4')
            subprocess.run([
                'ffmpeg', '-y', '-i', p,
                '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,fps=30',
                '-ar', '44100', '-ac', '2', '-vcodec', 'libx264', '-acodec', 'aac', '-preset', 'fast', '-crf', '23', n
            ], capture_output=True)
            normalized.append(n)
        list_file = output_path.replace('.mp4', '_list.txt')
        with open(list_file, 'w') as f:
            for n in normalized:
                f.write(f"file '{n}'\n")
        subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_file, '-c', 'copy', output_path], capture_output=True)
        return output_path if os.path.exists(output_path) else clip_paths[0]
    except Exception as e:
        print(f"Merge error: {e}")
        return clip_paths[0]

def cut_silences(input_path, output_path):
    try:
        result = subprocess.run(['ffmpeg', '-i', input_path, '-af', 'silencedetect=noise=-35dB:d=0.5', '-f', 'null', '-'], capture_output=True, text=True)
        starts = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', result.stderr)]
        ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', result.stderr)]
        if not starts:
            return input_path
        probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', input_path], capture_output=True, text=True)
        duration = float(json.loads(probe.stdout)['format']['duration'])
        segs = []
        cur = 0.0
        for s, e in zip(starts, ends):
            if s > cur + 0.1:
                segs.append((cur, s))
            cur = e
        if cur < duration - 0.1:
            segs.append((cur, duration))
        if not segs:
            return input_path
        fp = []
        for i, (s, e) in enumerate(segs):
            fp.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS[v{i}];[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS[a{i}];")
        n = len(segs)
        fs = ''.join(fp) + ''.join([f'[v{i}]' for i in range(n)]) + f'concat=n={n}:v=1:a=0[outv];' + ''.join([f'[a{i}]' for i in range(n)]) + f'concat=n={n}:v=0:a=1[outa]'
        subprocess.run(['ffmpeg', '-y', '-i', input_path, '-filter_complex', fs, '-map', '[outv]', '-map', '[outa]', output_path], capture_output=True)
        return output_path if os.path.exists(output_path) else input_path
    except Exception as e:
        print(f"Silence error: {e}")
        return input_path

def add_fade(input_path, output_path):
    try:
        subprocess.run(['ffmpeg', '-y', '-i', input_path, '-vf', 'fade=t=in:st=0:d=0.3', '-c:a', 'copy', output_path], capture_output=True)
        return output_path if os.path.exists(output_path) else input_path
    except:
        return input_path

def add_simple_captions(input_path, output_path):
    """Add a simple branded caption bar at the bottom."""
    try:
        subprocess.run([
            'ffmpeg', '-y', '-i', input_path,
            '-vf', "drawbox=y=ih-80:color=black@0.5:width=iw:height=80:t=fill,drawtext=text='@jackiestudio':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=h-50",
            '-c:a', 'copy', output_path
        ], capture_output=True)
        return output_path if os.path.exists(output_path) else input_path
    except Exception as e:
        print(f"Caption error: {e}")
        return input_path

def get_tips(instructions, clip_count):
    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": f"You are a viral TikTok expert for travel, food, fashion and lifestyle. Creator filmed {clip_count} clips. Instructions: '{instructions}'. Give 4 specific tips to make this go viral on TikTok — focus on pacing, text overlays to add in the TikTok app, sounds, and hooks. Under 150 words, be specific and actionable."}]
        )
        return response.content[0].text
    except Exception as e:
        print(f"Tips error: {e}")
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
