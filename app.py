from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import requests
import os
import sqlite3
import hashlib
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

def get_db():
    db = sqlite3.connect('users.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    db.commit()
    db.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

init_db()

LOGIN_HTML = (
    '<!DOCTYPE html>'
    '<html lang="en"><head>'
    '<meta charset="UTF-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
    '<title>MediTranslate - Sign In</title>'
    '<style>'
    '* { margin: 0; padding: 0; box-sizing: border-box; }'
    'body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: linear-gradient(135deg, #1a8a5a 0%, #0d5c3a 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }'
    '.container { background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); max-width: 400px; width: 100%; padding: 40px; }'
    'h1 { text-align: center; color: #333; margin-bottom: 6px; font-size: 28px; }'
    '.subtitle { text-align: center; color: #666; margin-bottom: 30px; font-size: 13px; }'
    '.tabs { display: flex; margin-bottom: 25px; border: 2px solid #1a8a5a; border-radius: 10px; overflow: hidden; }'
    '.tab { flex: 1; padding: 10px; text-align: center; cursor: pointer; font-weight: 600; font-size: 14px; background: white; color: #1a8a5a; border: none; }'
    '.tab.active { background: #1a8a5a; color: white; }'
    'input { width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }'
    '.btn { width: 100%; padding: 13px; border: none; border-radius: 8px; background: #1a8a5a; color: white; cursor: pointer; font-weight: 700; font-size: 15px; }'
    '.error { color: #ff4757; font-size: 13px; margin-bottom: 10px; text-align: center; }'
    '.success { color: #1a8a5a; font-size: 13px; margin-bottom: 10px; text-align: center; }'
    '</style></head><body>'
    '<div class="container">'
    '<h1>MediTranslate</h1>'
    '<p class="subtitle">Medical Translation Platform</p>'
    '<div class="tabs">'
    '<button class="tab active" id="tab_login" onclick="showTab(\'login\')">Sign In</button>'
    '<button class="tab" id="tab_register" onclick="showTab(\'register\')">Register</button>'
    '</div>'
    '{% if error %}<div class="error">{{ error }}</div>{% endif %}'
    '{% if success %}<div class="success">{{ success }}</div>{% endif %}'
    '<div id="login_form">'
    '<form method="POST" action="/login">'
    '<input type="hidden" name="action" value="login">'
    '<input type="email" name="email" placeholder="Email" required>'
    '<input type="password" name="password" placeholder="Password" required>'
    '<button type="submit" class="btn">Sign In</button>'
    '</form></div>'
    '<div id="register_form" style="display:none">'
    '<form method="POST" action="/login">'
    '<input type="hidden" name="action" value="register">'
    '<input type="text" name="name" placeholder="Full Name" required>'
    '<input type="email" name="email" placeholder="Email" required>'
    '<input type="password" name="password" placeholder="Password (min 6 chars)" required>'
    '<button type="submit" class="btn">Create Account</button>'
    '</form></div></div>'
    '<script>'
    'function showTab(tab) {'
    '  document.getElementById("login_form").style.display = tab === "login" ? "block" : "none";'
    '  document.getElementById("register_form").style.display = tab === "register" ? "block" : "none";'
    '  document.getElementById("tab_login").classList.toggle("active", tab === "login");'
    '  document.getElementById("tab_register").classList.toggle("active", tab === "register");'
    '}'
    '{% if show_register %}showTab("register");{% endif %}'
    '</script></body></html>'
)

HTML = (
    '<!DOCTYPE html>'
    '<html lang="en"><head>'
    '<meta charset="UTF-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
    '<title>MediTranslate</title>'
    '<style>'
    '* { margin: 0; padding: 0; box-sizing: border-box; }'
    'body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: linear-gradient(135deg, #1a8a5a 0%, #0d5c3a 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }'
    '.container { background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); max-width: 500px; width: 100%; padding: 40px; }'
    'h1 { text-align: center; color: #333; margin-bottom: 6px; font-size: 30px; }'
    '.subtitle { text-align: center; color: #666; margin-bottom: 5px; font-size: 13px; }'
    '.user-bar { text-align: right; margin-bottom: 15px; font-size: 13px; color: #666; }'
    '.user-bar a { color: #ff4757; text-decoration: none; font-weight: 600; }'
    '.lang-label { text-align: center; font-size: 12px; color: #999; margin-bottom: 8px; }'
    '.lang-section { display: flex; gap: 10px; margin-bottom: 25px; }'
    '.lang-btn { flex: 1; padding: 12px; border: 2px solid #ddd; background: white; border-radius: 10px; cursor: pointer; font-weight: 600; font-size: 15px; transition: all 0.3s; }'
    '.lang-btn.active { background: #1a8a5a; color: white; border-color: #1a8a5a; }'
    'input { width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }'
    '.record-section { text-align: center; margin: 20px 0; }'
    '.record-btn { width: 110px; height: 110px; border-radius: 50%; border: none; background: #1a8a5a; color: white; font-size: 44px; cursor: pointer; margin: 0 auto; transition: all 0.3s; display: flex; align-items: center; justify-content: center; }'
    '.record-btn.recording { background: #ff4757; animation: pulse 1s infinite; }'
    '@keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.1); } }'
    '.status { text-align: center; color: #666; font-size: 13px; margin-top: 10px; min-height: 20px; }'
    '.main-btn { width: 100%; padding: 13px; border: none; border-radius: 8px; background: #1a8a5a; color: white; cursor: pointer; font-weight: 700; margin-bottom: 10px; font-size: 15px; }'
    '.main-btn:disabled { opacity: 0.5; cursor: not-allowed; }'
    '.download-btn { width: 100%; padding: 10px; border: 2px solid #2ed573; border-radius: 8px; background: white; color: #2ed573; cursor: pointer; font-weight: 600; margin-bottom: 10px; font-size: 14px; }'
    '.clear-btn { width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 8px; background: white; color: #999; cursor: pointer; font-weight: 600; margin-bottom: 10px; font-size: 14px; }'
    '.result { background: #f5f5f5; padding: 15px; border-radius: 8px; margin-top: 10px; display: none; }'
    '.result.show { display: block; }'
    '.result-title { font-weight: 700; margin-bottom: 8px; color: #333; font-size: 13px; text-transform: uppercase; }'
    '.result-text { font-size: 14px; line-height: 1.8; color: #444; white-space: pre-wrap; }'
    '.result-text.arabic { direction: rtl; text-align: right; font-size: 16px; }'
    '.divider { border: none; border-top: 1px solid #ddd; margin: 12px 0; }'
    '.section-box { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; margin-bottom: 10px; }'
    '.section-box.arabic-box { border-right: 4px solid #1a8a5a; }'
    '.section-box.english-box { border-left: 4px solid #2b7fcc; }'
    '</style></head><body>'
    '<div class="container">'
    '<div class="user-bar">{{ user_name }} &nbsp;|&nbsp; <a href="/logout">Sign Out</a></div>'
    '<h1>MediTranslate</h1>'
    '<p class="subtitle">Arabic - English - Voice Translation</p>'
    '<div class="lang-label">I am speaking:</div>'
    '<div class="lang-section">'
    '<button class="lang-btn active" id="lang_ar" onclick="setLang(\'ar\')">Arabic</button>'
    '<button class="lang-btn" id="lang_en" onclick="setLang(\'en\')">English</button>'
    '</div>'
    '<input type="text" id="session_title" placeholder="Session title...">'
    '<div class="record-section">'
    '<button class="record-btn" id="record_btn" onclick="toggleRecord()">&#127908;</button>'
    '<div class="status" id="status">Click to record</div>'
    '</div>'
    '<button class="main-btn" id="submit_btn" onclick="process()" disabled>Translate</button>'
    '<button class="download-btn" id="download_btn" onclick="downloadAndClear()" style="display:none">Download and Save</button>'
    '<button class="clear-btn" onclick="clearAll()">Clear</button>'
    '<div id="result" class="result">'
    '<div class="section-box arabic-box">'
    '<div class="result-title">Original Arabic</div>'
    '<div class="result-text arabic" id="text_ar"></div>'
    '</div>'
    '<div class="section-box english-box">'
    '<div class="result-title">Original English</div>'
    '<div class="result-text" id="text_en"></div>'
    '</div>'
    '<div class="divider"></div>'
    '<div class="section-box english-box">'
    '<div class="result-title">English Translation</div>'
    '<div class="result-text" id="translation_en"></div>'
    '</div>'
    '<div class="section-box arabic-box">'
    '<div class="result-title">Arabic Translation</div>'
    '<div class="result-text arabic" id="translation_ar"></div>'
    '</div>'
    '</div></div>'
    '<script>'
    'var mediaRecorder, audioChunks = [], isRecording = false, recordedAudio = null, selectedLang = "ar";'
    'function setLang(lang) {'
    '  selectedLang = lang;'
    '  document.querySelectorAll(".lang-btn").forEach(function(el) { el.classList.remove("active"); });'
    '  document.getElementById("lang_" + lang).classList.add("active");'
    '  document.getElementById("status").textContent = "Click to record";'
    '}'
    'function appendText(id, newText) {'
    '  if (!newText) return;'
    '  var el = document.getElementById(id);'
    '  var sep = "\\n\\n--- " + new Date().toLocaleTimeString() + " ---\\n";'
    '  el.textContent = el.textContent ? el.textContent + sep + newText : newText;'
    '}'
    'async function toggleRecord() {'
    '  if (!isRecording) {'
    '    try {'
    '      var stream = await navigator.mediaDevices.getUserMedia({ audio: true });'
    '      mediaRecorder = new MediaRecorder(stream);'
    '      audioChunks = [];'
    '      mediaRecorder.ondataavailable = function(e) { audioChunks.push(e.data); };'
    '      mediaRecorder.onstop = function() {'
    '        recordedAudio = new Blob(audioChunks, { type: "audio/webm" });'
    '        document.getElementById("submit_btn").disabled = false;'
    '      };'
    '      mediaRecorder.start();'
    '      isRecording = true;'
    '      document.getElementById("record_btn").innerHTML = "&#9209;";'
    '      document.getElementById("record_btn").classList.add("recording");'
    '      document.getElementById("status").textContent = "Recording...";'
    '      document.getElementById("submit_btn").disabled = true;'
    '    } catch(e) { alert("Microphone error: " + e.message); }'
    '  } else {'
    '    mediaRecorder.stop();'
    '    mediaRecorder.stream.getTracks().forEach(function(t) { t.stop(); });'
    '    isRecording = false;'
    '    document.getElementById("record_btn").innerHTML = "&#127908;";'
    '    document.getElementById("record_btn").classList.remove("recording");'
    '    document.getElementById("status").textContent = "Done! Press Translate";'
    '  }'
    '}'
    'async function process() {'
    '  if (!recordedAudio) return;'
    '  var btn = document.getElementById("submit_btn");'
    '  btn.disabled = true;'
    '  btn.textContent = "Translating...";'
    '  try {'
    '    var formData = new FormData();'
    '    formData.append("audio", recordedAudio, "audio.webm");'
    '    formData.append("lang", selectedLang);'
    '    var transcribeRes = await fetch("/transcribe", { method: "POST", body: formData });'
    '    var transcribeData = await transcribeRes.json();'
    '    if (!transcribeRes.ok) throw new Error(transcribeData.error);'
    '    var translateRes = await fetch("/translate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: transcribeData.text, lang: selectedLang }) });'
    '    var translateData = await translateRes.json();'
    '    if (!translateRes.ok) throw new Error(translateData.error);'
    '    if (selectedLang === "ar") { appendText("text_ar", transcribeData.text); appendText("translation_en", translateData.translation); }'
    '    else { appendText("text_en", transcribeData.text); appendText("translation_ar", translateData.translation); }'
    '    document.getElementById("result").classList.add("show");'
    '    document.getElementById("download_btn").style.display = "block";'
    '  } catch(e) { alert("Error: " + e.message); }'
    '  finally { btn.disabled = false; btn.textContent = "Translate"; }'
    '}'
    'function downloadAndClear() {'
    '  var title = document.getElementById("session_title").value || "session";'
    '  var content = "MEDITRANSLATE - " + title + "\\nDate: " + new Date().toLocaleString() + "\\n\\n";'
    '  var ar = document.getElementById("text_ar").textContent;'
    '  var en = document.getElementById("text_en").textContent;'
    '  var trEn = document.getElementById("translation_en").textContent;'
    '  var trAr = document.getElementById("translation_ar").textContent;'
    '  if (ar) content += "ARABIC ORIGINAL:\\n" + ar + "\\n\\n";'
    '  if (en) content += "ENGLISH ORIGINAL:\\n" + en + "\\n\\n";'
    '  if (trEn) content += "ENGLISH TRANSLATION:\\n" + trEn + "\\n\\n";'
    '  if (trAr) content += "ARABIC TRANSLATION:\\n" + trAr + "\\n";'
    '  var blob = new Blob([content], { type: "text/plain;charset=utf-8" });'
    '  var url = URL.createObjectURL(blob);'
    '  var a = document.createElement("a");'
    '  a.href = url;'
    '  a.download = "meditranslate_" + title.replace(/\\s+/g,"_") + ".txt";'
    '  a.click();'
    '  URL.revokeObjectURL(url);'
    '  setTimeout(function() { clearAll(); }, 500);'
    '}'
    'function clearAll() {'
    '  ["text_ar","text_en","translation_ar","translation_en"].forEach(function(id) { document.getElementById(id).textContent = ""; });'
    '  document.getElementById("result").classList.remove("show");'
    '  document.getElementById("submit_btn").disabled = true;'
    '  document.getElementById("download_btn").style.display = "none";'
    '  document.getElementById("status").textContent = "Click to record";'
    '  document.getElementById("record_btn").innerHTML = "&#127908;";'
    '  recordedAudio = null;'
    '}'
    '</script></body></html>'
)


@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template_string(HTML, user_name=session.get('user_name', 'User'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template_string(LOGIN_HTML, error=None, success=None, show_register=False)

    action = request.form.get('action')
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    if action == 'register':
        name = request.form.get('name', '').strip()
        if len(password) < 6:
            return render_template_string(LOGIN_HTML, error='Password must be at least 6 characters', success=None, show_register=True)
        db = get_db()
        try:
            db.execute('INSERT INTO users (email, password, name) VALUES (?, ?, ?)',
                       (email, hash_password(password), name))
            db.commit()
            return render_template_string(LOGIN_HTML, error=None, success='Account created! Please sign in.', show_register=False)
        except sqlite3.IntegrityError:
            return render_template_string(LOGIN_HTML, error='Email already registered', success=None, show_register=True)
        finally:
            db.close()

    elif action == 'login':
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ? AND password = ?',
                          (email, hash_password(password))).fetchone()
        db.close()
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name'] or email
            return redirect(url_for('home'))
        return render_template_string(LOGIN_HTML, error='Invalid email or password', success=None, show_register=False)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
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
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    try:
        data = request.json
        text = data['text']
        lang = data.get('lang', 'ar')
        if lang == 'ar':
            prompt = 'You are a professional medical interpreter. Translate the following Arabic text to English accurately. Return ONLY the English translation.\n\nArabic text: ' + text
        else:
            prompt = 'You are a professional medical interpreter. Translate the following English text to Arabic accurately. Return ONLY the Arabic translation.\n\nEnglish text: ' + text
        r = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={'x-api-key': ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01'},
            json={'model': 'claude-sonnet-4-20250514', 'max_tokens': 1000, 'messages': [{'role': 'user', 'content': prompt}]},
            timeout=30
        )
        if r.status_code != 200:
            return jsonify({'error': 'Translation failed'}), 500
        return jsonify({'translation': r.json()['content'][0]['text'].strip()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


ADMIN_HTML = (
    '<!DOCTYPE html>'
    '<html lang="en"><head>'
    '<meta charset="UTF-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
    '<title>MediTranslate Admin</title>'
    '<style>'
    '* { margin: 0; padding: 0; box-sizing: border-box; }'
    'body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #1a1a2e; min-height: 100vh; padding: 20px; color: #fff; }'
    'h1 { color: #2ed573; margin-bottom: 5px; font-size: 24px; }'
    '.subtitle { color: #888; margin-bottom: 25px; font-size: 13px; }'
    '.back { color: #2ed573; text-decoration: none; font-size: 13px; display: inline-block; margin-bottom: 20px; }'
    'table { width: 100%; border-collapse: collapse; background: #16213e; border-radius: 12px; overflow: hidden; }'
    'th { background: #0f3460; padding: 12px 15px; text-align: left; font-size: 12px; text-transform: uppercase; color: #2ed573; }'
    'td { padding: 12px 15px; border-bottom: 1px solid #1a2a4a; font-size: 14px; }'
    'tr:last-child td { border-bottom: none; }'
    'tr:hover td { background: rgba(46,213,115,0.05); }'
    '.delete-btn { background: #ff4757; color: white; border: none; padding: 5px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; }'
    '.delete-btn:hover { background: #ff3742; }'
    '.count { background: #0f3460; padding: 10px 15px; border-radius: 8px; display: inline-block; margin-bottom: 20px; font-size: 13px; }'
    '.count span { color: #2ed573; font-weight: 700; font-size: 18px; }'
    '</style></head><body>'
    '<a href="/" class="back">Back to App</a>'
    '<h1>Admin Panel</h1>'
    '<p class="subtitle">MediTranslate User Management</p>'
    '<div class="count">Total users: <span>{{ users|length }}</span></div>'
    '<table>'
    '<tr><th>#</th><th>Name</th><th>Email</th><th>Registered</th><th>Action</th></tr>'
    '{% for user in users %}'
    '<tr>'
    '<td>{{ loop.index }}</td>'
    '<td>{{ user.name or "-" }}</td>'
    '<td>{{ user.email }}</td>'
    '<td>{{ user.created_at[:10] if user.created_at else "-" }}</td>'
    '<td><button class="delete-btn" onclick="deleteUser({{ user.id }}, \'{{ user.email }}\')">Delete</button></td>'
    '</tr>'
    '{% endfor %}'
    '</table>'
    '<script>'
    'async function deleteUser(id, email) {'
    '  if (!confirm("Delete user " + email + "?")) return;'
    '  var res = await fetch("/admin/delete/" + id, { method: "POST" });'
    '  var data = await res.json();'
    '  if (data.success) { location.reload(); }'
    '  else { alert("Error: " + data.error); }'
    '}'
    '</script></body></html>'
)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

@app.route('/admin')
def admin():
    if request.args.get('pw') != ADMIN_PASSWORD:
        return 'Access denied. Add ?pw=YOUR_PASSWORD to URL.', 403
    db = get_db()
    users = db.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    db.close()
    return render_template_string(ADMIN_HTML, users=users)

@app.route('/admin/delete/<int:user_id>', methods=['POST'])
def admin_delete(user_id):
    if request.args.get('pw') != ADMIN_PASSWORD:
        return jsonify({'error': 'Access denied'}), 403
    db = get_db()
    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
