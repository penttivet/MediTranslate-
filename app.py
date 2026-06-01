from flask import Flask, render_template_string, request, jsonify
import requests
import os

app = Flask(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MediTranslate</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: linear-gradient(135deg, #1a8a5a 0%, #0d5c3a 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
.container { background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); max-width: 500px; width: 100%; padding: 40px; }
h1 { text-align: center; color: #333; margin-bottom: 6px; font-size: 30px; }
.subtitle { text-align: center; color: #666; margin-bottom: 20px; font-size: 13px; }
.lang-label { text-align: center; font-size: 12px; color: #999; margin-bottom: 8px; }
.lang-section { display: flex; gap: 10px; margin-bottom: 25px; }
.lang-btn { flex: 1; padding: 12px; border: 2px solid #ddd; background: white; border-radius: 10px; cursor: pointer; font-weight: 600; font-size: 15px; transition: all 0.3s; }
.lang-btn.active { background: #1a8a5a; color: white; border-color: #1a8a5a; }
input { width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
.record-section { text-align: center; margin: 20px 0; }
.record-btn { width: 110px; height: 110px; border-radius: 50%; border: none; background: #1a8a5a; color: white; font-size: 44px; cursor: pointer; margin: 0 auto; transition: all 0.3s; display: flex; align-items: center; justify-content: center; }
.record-btn:hover { background: #0d5c3a; }
.record-btn.recording { background: #ff4757; animation: pulse 1s infinite; }
@keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.1); } }
.status { text-align: center; color: #666; font-size: 13px; margin-top: 10px; min-height: 20px; }
.main-btn { width: 100%; padding: 13px; border: none; border-radius: 8px; background: #1a8a5a; color: white; cursor: pointer; font-weight: 700; margin-bottom: 10px; transition: all 0.3s; font-size: 15px; }
.main-btn:hover { background: #0d5c3a; }
.main-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.download-btn { width: 100%; padding: 10px; border: 2px solid #2ed573; border-radius: 8px; background: white; color: #2ed573; cursor: pointer; font-weight: 600; margin-bottom: 10px; transition: all 0.3s; font-size: 14px; }
.download-btn:hover { background: #2ed573; color: white; }
.clear-btn { width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 8px; background: white; color: #999; cursor: pointer; font-weight: 600; margin-bottom: 10px; transition: all 0.3s; font-size: 14px; }
.clear-btn:hover { border-color: #ff4757; color: #ff4757; }
.result { background: #f5f5f5; padding: 15px; border-radius: 8px; margin-top: 10px; display: none; }
.result.show { display: block; }
.result-title { font-weight: 700; margin-bottom: 8px; color: #333; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }
.result-text { font-size: 14px; line-height: 1.8; color: #444; white-space: pre-wrap; }
.result-text.arabic { direction: rtl; text-align: right; font-size: 16px; }
.divider { border: none; border-top: 1px solid #ddd; margin: 12px 0; }
.section-box { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
.section-box.arabic-box { border-right: 4px solid #1a8a5a; }
.section-box.english-box { border-left: 4px solid #2b7fcc; }
</style>
</head>
<body>
<div class="container">
<h1>🌍 MediTranslate</h1>
<p class="subtitle">Arabic ↔ English • Voice Translation</p>

<div class="lang-label">I am speaking / أنا أتحدث:</div>
<div class="lang-section">
  <button class="lang-btn active" id="lang_ar" onclick="setLang('ar')">🇸🇦 العربية</button>
  <button class="lang-btn" id="lang_en" onclick="setLang('en')">🇬🇧 English</button>
</div>

<input type="text" id="session_title" placeholder="Session title / عنوان الجلسة...">

<div class="record-section">
  <button class="record-btn" id="record_btn" onclick="toggleRecord()">🎙️</button>
  <div class="status" id="status">اضغط للتسجيل / Click to record</div>
</div>

<button class="main-btn" id="submit_btn" onclick="process()" disabled>🔄 Translate / ترجمة</button>
<button class="download-btn" id="download_btn" onclick="downloadAndClear()" style="display:none">💾 Download & Save / حفظ</button>
<button class="clear-btn" onclick="clearAll()">🗑️ Clear / مسح</button>

<div id="result" class="result">
  <div class="section-box arabic-box">
    <div class="result-title">🎙️ النص الأصلي (العربية) / Original Arabic</div>
    <div class="result-text arabic" id="text_ar"></div>
  </div>
  <div class="section-box english-box">
    <div class="result-title">🎙️ Original English Text</div>
    <div class="result-text" id="text_en"></div>
  </div>
  <div class="divider"></div>
  <div class="section-box english-box">
    <div class="result-title">🔄 English Translation</div>
    <div class="result-text" id="translation_en"></div>
  </div>
  <div class="section-box arabic-box">
    <div class="result-title">🔄 الترجمة إلى العربية / Arabic Translation</div>
    <div class="result-text arabic" id="translation_ar"></div>
  </div>
</div>
</div>

<script>
let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let recordedAudio = null;
let selectedLang = 'ar';

function setLang(lang) {
  selectedLang = lang;
  document.querySelectorAll('.lang-btn').forEach(el => el.classList.remove('active'));
  document.getElementById('lang_' + lang).classList.add('active');
  document.getElementById('status').textContent = lang === 'ar'
    ? 'اضغط للتسجيل / Click to record'
    : 'Click to record / اضغط للتسجيل';
}

function appendText(id, newText) {
  if (!newText) return;
  const el = document.getElementById(id);
  const sep = '\\n\\n— ' + new Date().toLocaleTimeString() + ' —\\n';
  el.textContent = el.textContent ? el.textContent + sep + newText : newText;
}

async function toggleRecord() {
  if (!isRecording) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];
      mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
      mediaRecorder.onstop = () => {
        recordedAudio = new Blob(audioChunks, { type: 'audio/webm' });
        document.getElementById('submit_btn').disabled = false;
      };
      mediaRecorder.start();
      isRecording = true;
      document.getElementById('record_btn').textContent = '⏹️';
      document.getElementById('record_btn').classList.add('recording');
      document.getElementById('status').textContent = selectedLang === 'ar' ? '🔴 جارٍ التسجيل...' : '🔴 Recording...';
      document.getElementById('submit_btn').disabled = true;
    } catch (e) {
      alert('Microphone error: ' + e.message);
    }
  } else {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(t => t.stop());
    isRecording = false;
    document.getElementById('record_btn').textContent = '🎙️';
    document.getElementById('record_btn').classList.remove('recording');
    document.getElementById('status').textContent = selectedLang === 'ar'
      ? '✅ جاهز! اضغط ترجمة'
      : '✅ Done! Press Translate';
  }
}

async function process() {
  if (!recordedAudio) return;
  const btn = document.getElementById('submit_btn');
  btn.disabled = true;
  btn.textContent = selectedLang === 'ar' ? '⏳ جارٍ الترجمة...' : '⏳ Translating...';
  try {
    const formData = new FormData();
    formData.append('audio', recordedAudio, 'audio.webm');
    formData.append('lang', selectedLang);
    const transcribeRes = await fetch('/transcribe', { method: 'POST', body: formData });
    const transcribeData = await transcribeRes.json();
    if (!transcribeRes.ok) throw new Error(transcribeData.error);

    const translateRes = await fetch('/translate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: transcribeData.text, lang: selectedLang })
    });
    const translateData = await translateRes.json();
    if (!translateRes.ok) throw new Error(translateData.error);

    if (selectedLang === 'ar') {
      appendText('text_ar', transcribeData.text);
      appendText('translation_en', translateData.translation);
    } else {
      appendText('text_en', transcribeData.text);
      appendText('translation_ar', translateData.translation);
    }

    document.getElementById('result').classList.add('show');
    document.getElementById('download_btn').style.display = 'block';
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '🔄 Translate / ترجمة';
  }
}

function downloadAndClear() {
  const title = document.getElementById('session_title').value || 'session';
  let content = 'MEDITRANSLATE - ' + title + '\\n';
  content += 'Date: ' + new Date().toLocaleString() + '\\n';
  content += '='.repeat(50) + '\\n\\n';
  const ar = document.getElementById('text_ar').textContent;
  const en = document.getElementById('text_en').textContent;
  const trEn = document.getElementById('translation_en').textContent;
  const trAr = document.getElementById('translation_ar').textContent;
  if (ar) content += 'ARABIC ORIGINAL:\\n' + ar + '\\n\\n';
  if (en) content += 'ENGLISH ORIGINAL:\\n' + en + '\\n\\n';
  if (trEn) content += 'ENGLISH TRANSLATION:\\n' + trEn + '\\n\\n';
  if (trAr) content += 'ARABIC TRANSLATION:\\n' + trAr + '\\n';
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'meditranslate_' + title.replace(/\\s+/g,'_') + '_' + new Date().toISOString().slice(0,10) + '.txt';
  a.click();
  URL.revokeObjectURL(url);
  setTimeout(() => clearAll(), 500);
}

function clearAll() {
  ['text_ar','text_en','translation_ar','translation_en'].forEach(id => {
    document.getElementById(id).textContent = '';
  });
  document.getElementById('result').classList.remove('show');
  document.getElementById('submit_btn').disabled = true;
  document.getElementById('download_btn').style.display = 'none';
  document.getElementById('status').textContent = selectedLang === 'ar'
    ? 'اضغط للتسجيل / Click to record'
    : 'Click to record / اضغط للتسجيل';
  document.getElementById('record_btn').textContent = '🎙️';
  recordedAudio = null;
}
</script>
</body>
</html>"""

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        audio_file = request.files['audio']
        lang = request.form.get('lang', 'ar')
        whisper_lang = 'ar' if lang == 'ar' else 'en'
        r = requests.post(
            'https://api.openai.com/v1/audio/transcriptions',
            headers={'Authorization': f'Bearer {OPENAI_API_KEY}'},
            files={'file': ('audio.webm', audio_file.read(), 'audio/webm')},
            data={'model': 'whisper-1', 'language': whisper_lang},
            timeout=60
        )
        if r.status_code != 200:
            return jsonify({'error': r.text}), 500
        return jsonify({'text': r.json()['text']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/translate', methods=['POST'])
def translate():
    try:
        data = request.json
        text = data['text']
        lang = data.get('lang', 'ar')
        if lang == 'ar':
            prompt = f"You are a professional medical interpreter. Translate the following Arabic text to English accurately and completely. Return ONLY the English translation, nothing else.\n\nArabic text: {text}"
        else:
            prompt = f"أنت مترجم طبي محترف. ترجم النص الإنجليزي التالي إلى العربية بدقة وبشكل كامل. أعد الترجمة العربية فقط، لا شيء آخر.\n\nEnglish text: {text}"
        r = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': ANTHROPIC_API_KEY,
                'anthropic-version': '2023-06-01'
            },
            json={
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 1000,
                'messages': [{'role': 'user', 'content': prompt}]
            },
            timeout=30
        )
        if r.status_code != 200:
            return jsonify({'error': 'Translation failed'}), 500
        translation = r.json()['content'][0]['text'].strip()
        return jsonify({'translation': translation})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
