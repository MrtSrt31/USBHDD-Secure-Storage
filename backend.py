import os, shutil, time, functools, sqlite3, hashlib, io, json, stat, sys, threading, socket
from datetime import datetime, timedelta
from flask import Flask, render_template_string, Response, abort, redirect, session, request, url_for, send_file, flash, jsonify, send_from_directory
from PIL import Image
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from cryptography.fernet import Fernet
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# --- AYARLAR ---
def get_app_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.secret_key = b'\x8a\x12\xd4\x1f\x91\xa0\xb2\xc3\xd4\xe5\xf6\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b'
app.config['SESSION_COOKIE_SECURE'] = True      
app.config['SESSION_COOKIE_HTTPONLY'] = True    
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'   
csrf = CSRFProtect(app)

CACHE_CIPHER = Fernet(b'I0exgBqrqKHqbc2HQ2Jc2dEqY3oiJ41wup1CDNgxE2c=')
INDEX_CIPHER = Fernet(b'L4YpB3p8X8x8X8x8X8x8X8x8X8x8X8x8X8x8X8x8X8o=') 

APP_ROOT = get_app_path()
DATA_DIR  = os.path.join(APP_ROOT, "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
DB_FILE   = os.path.join(DATA_DIR, "s9x_secure_storage.db")
CERT_FILE = os.path.join(DATA_DIR, "cert.pem")
KEY_FILE  = os.path.join(DATA_DIR, "key.pem")
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'mkv', 'webp', 'avi', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'csv', 'rtf', 'odt', 'ods', 'odp'}
INDEX_STATUS = {"status": "Waiting...", "current_path": "", "total_files": 0}

# --- DİL PAKETLERİ / LANGUAGE PACKS ---
LANGUAGES = {
    'en': {
        # General
        'lang_code': 'en',
        'login_title': 'Login',
        'login_heading': '🔒 LOGIN',
        'username_placeholder': 'Username',
        'password_placeholder': 'Password',
        'login_btn': 'SIGN IN',
        'logout_btn': 'Logout',
        'wrong_login': 'Invalid credentials!',
        'error': 'An error occurred.',
        'fill_all': 'Please fill in all fields.',
        # Setup
        'setup_title': 'Setup',
        'setup_heading': '🛠️ INITIAL SETUP',
        'setup_notice': 'Create your admin account.',
        'share_name_label': 'Share Name',
        'path_label': 'Path',
        'complete_btn': 'COMPLETE',
        'select_folder_btn': '📂 Select',
        'select_folder_title': 'Select Folder',
        'select_btn': 'Select',
        'cancel_btn': 'Cancel',
        # Index page
        'files_title': 'Files',
        'search_placeholder': 'Search...',
        'sort_name': 'A-Z',
        'sort_date': 'Date',
        'folder_placeholder': 'Folder',
        # Admin panel
        'admin_title': 'Management',
        'back_btn': '⬅ Back',
        'monitor_title': '📡 HDD Index Monitor (Night Mode)',
        'monitor_status': 'STATUS:',
        'monitor_processing': 'PROCESSING:',
        'monitor_total': 'TOTAL:',
        'users_heading': 'Users',
        'user_col': 'User',
        'role_col': 'Role',
        'delete_col': 'Delete',
        'delete_btn': 'Delete',
        'add_btn': 'Add',
        'shares_heading': 'Shares',
        'name_col': 'Name',
        'path_col': 'Path',
        'remove_col': 'Remove',
        'permissions_heading': 'Permissions',
        'user_folder_col': 'User \\ Folder',
        'confirm_delete': 'Delete?',
        'loading': 'Loading...',
        # Night mode scanner
        'idx_waiting': 'Waiting...',
        'idx_scanning': '🚀 Night Mode: Scanning...',
        'idx_ready': '✅ Ready (Night Mode Waiting)',
        'idx_ready_cache': '✅ Ready (Loaded from Cache)',
        'idx_error': '❌ Error',
        'idx_scanning_share': '📂 Scanning:',
        'idx_last_scan': 'Last scan:',
        'idx_db_empty': '--- Database empty, starting initial scan ---',
        'idx_db_full': '--- Database loaded, using persistent cache ---',
        'night_mode_start': 'Night mode started. Scanning...',
        # Language switcher
        'lang_switch_en': 'English',
        'lang_switch_tr': 'Türkçe',
    },
    'tr': {
        # Genel
        'lang_code': 'tr',
        'login_title': 'Giriş',
        'login_heading': '🔒 GİRİŞ',
        'username_placeholder': 'Kullanıcı Adı',
        'password_placeholder': 'Parola',
        'login_btn': 'GİRİŞ YAP',
        'logout_btn': 'Çıkış',
        'wrong_login': 'Hatalı giriş!',
        'error': 'Hata oluştu.',
        'fill_all': 'Tüm alanları doldurun.',
        # Kurulum
        'setup_title': 'Kurulum',
        'setup_heading': '🛠️ İLK KURULUM',
        'setup_notice': 'Admin hesabı oluşturun.',
        'share_name_label': 'Paylaşım Adı',
        'path_label': 'Yol',
        'complete_btn': 'TAMAMLA',
        'select_folder_btn': '📂 Seç',
        'select_folder_title': 'Klasör Seç',
        'select_btn': 'Seç',
        'cancel_btn': 'İptal',
        # Ana sayfa
        'files_title': 'Dosyalar',
        'search_placeholder': 'Ara...',
        'sort_name': 'A-Z',
        'sort_date': 'Tarih',
        'folder_placeholder': 'Klasör',
        # Admin paneli
        'admin_title': 'Yönetim',
        'back_btn': '⬅ Geri',
        'monitor_title': '📡 HDD Index Monitörü (Gece Modu)',
        'monitor_status': 'DURUM:',
        'monitor_processing': 'İŞLENEN:',
        'monitor_total': 'TOPLAM:',
        'users_heading': 'Kullanıcılar',
        'user_col': 'Kullanıcı',
        'role_col': 'Rol',
        'delete_col': 'Sil',
        'delete_btn': 'Sil',
        'add_btn': 'Ekle',
        'shares_heading': 'Paylaşımlar',
        'name_col': 'Ad',
        'path_col': 'Yol',
        'remove_col': 'Kaldır',
        'permissions_heading': 'İzinler',
        'user_folder_col': 'Kullanıcı \\ Klasör',
        'confirm_delete': 'Sil?',
        'loading': 'Yükleniyor...',
        # Gece modu tarayıcısı
        'idx_waiting': 'Bekleniyor...',
        'idx_scanning': '🚀 Gece Modu: Taranıyor...',
        'idx_ready': '✅ Hazır (Gece Bekleniyor)',
        'idx_ready_cache': '✅ Hazır (Önbellekten Yüklendi)',
        'idx_error': '❌ Hata',
        'idx_scanning_share': '📂 Taranıyor:',
        'idx_last_scan': 'Son tarama:',
        'idx_db_empty': '--- Veritabanı boş, ilk tarama başlatılıyor ---',
        'idx_db_full': '--- Veritabanı dolu, önceki kayıtlar kullanılıyor (Persistent Cache) ---',
        'night_mode_start': 'Gece modu saati geldi. Tarama başlıyor...',
        # Dil seçici
        'lang_switch_en': 'English',
        'lang_switch_tr': 'Türkçe',
    }
}

def get_lang():
    """Aktif dil paketini döndürür. Session'dan okur, yoksa 'en'."""
    return LANGUAGES.get(session.get('lang', 'en'), LANGUAGES['en'])

# --- OTO SERTİFİKA ---
def check_and_create_certs():
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE): return
    print("--- Sertifikalar oluşturuluyor... ---")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, u"localhost")])
    cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(datetime.utcnow()).not_valid_after(datetime.utcnow()+timedelta(days=3650)).add_extension(x509.SubjectAlternativeName([x509.DNSName(u"localhost")]), critical=False).sign(key, hashes.SHA256())
    with open(KEY_FILE, "wb") as f: f.write(key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.TraditionalOpenSSL, encryption_algorithm=serialization.NoEncryption()))
    with open(CERT_FILE, "wb") as f: f.write(cert.public_bytes(serialization.Encoding.PEM))
    if os.name == 'posix':
        try:
            os.chmod(KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)   # 600: özel anahtar sadece sahip
            os.chmod(CERT_FILE, stat.S_IRUSR | stat.S_IWUSR)  # 600: sertifika sadece sahip
        except Exception: pass

# --- DATABASE ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

# --- CSS/HTML ---
CSS_CODE = """:root{--bg:#fff;--fg:#111;--card:#f2f2f2;--accent:#2563eb;--danger:#dc2626;--success:#16a34a;} @media(prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#c9d1d9;--card:#161b22;}} body{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;} header{padding:15px;border-bottom:1px solid #30363d;display:flex;gap:15px;align-items:center;flex-wrap:wrap;} .logo{font-weight:bold;font-size:1.2rem;margin-right:auto;} .search-box input{background:var(--card);border:1px solid #30363d;color:var(--fg);padding:8px;border-radius:6px;outline:none;} .btn{padding:8px 12px;border-radius:6px;cursor:pointer;font-size:14px;border:none;color:#fff;text-decoration:none;display:inline-flex;align-items:center;gap:5px;} .btn-red{background:var(--danger);} .btn-blue{background:var(--accent);} .btn-gray{background:#4b5563;} .btn-green{background:var(--success);} .toolbar{padding:10px 15px;display:flex;gap:10px;align-items:center;overflow-x:auto;background:rgba(0,0,0,0.05);} .breadcrumb{display:flex;gap:5px;font-size:14px;white-space:nowrap;} .breadcrumb a{color:var(--accent);text-decoration:none;} .breadcrumb span{color:#666;} .alert-box{padding:12px;margin:10px 15px;border-radius:6px;text-align:center;font-weight:600;font-size:14px;border:1px solid transparent;display:none;position:relative;} .alert-error{background:#ffeded;color:#dc2626;border-color:#fecaca;} .alert-success{background:#dcfce7;color:#166534;border-color:#bbf7d0;} .close-btn{position:absolute;right:15px;top:50%;transform:translateY(-50%);cursor:pointer;font-size:18px;font-weight:bold;opacity:0.6;} .close-btn:hover{opacity:1;} .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;padding:15px;} .card{background:var(--card);border-radius:10px;overflow:hidden;position:relative;transition:transform .2s;} .card:hover{transform:translateY(-3px);box-shadow:0 4px 12px rgba(0,0,0,.2);} .thumb{width:100%;height:120px;display:flex;align-items:center;justify-content:center;font-size:40px;background:#222;overflow:hidden;position:relative;} .thumb img{width:100%;height:100%;object-fit:cover;transition:.3s;} .card:hover .thumb img{transform:scale(1.1);} .info{padding:10px;font-size:13px;} .name{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block;margin-bottom:4px;color:var(--fg);text-decoration:none;} .meta{font-size:11px;color:#888;display:flex;justify-content:space-between;} .actions{position:absolute;top:5px;right:5px;display:none;z-index:10;} .card:hover .actions{display:block;} .del-btn{background:rgba(220,38,38,.9);color:#fff;border:none;width:24px;height:24px;border-radius:4px;cursor:pointer;display:flex;align-items:center;justify-content:center;text-decoration:none;} .icon-dir{color:#fbbf24;} .icon-file{color:#9ca3af;} .icon-vid{color:#f87171;} .icon-doc{color:#60a5fa;} .icon-xls{color:#34d399;} .icon-ppt{color:#f97316;} .icon-pdf{color:#ef4444;} .monitor-box{background:#1e293b;color:#fff;padding:15px;margin:15px;border-radius:8px;font-family:monospace;border:1px solid #334155;} .monitor-row{display:flex;justify-content:space-between;margin-bottom:5px;} .monitor-bar{height:4px;background:#334155;width:100%;margin-top:10px;position:relative;overflow:hidden;} .monitor-bar-inner{height:100%;background:#3b82f6;width:100%;animation:pulse 2s infinite;} @keyframes pulse{0%{opacity:.5;} 50%{opacity:1;} 100%{opacity:.5;}} #viewer{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.95);display:none;z-index:9999;align-items:center;justify-content:center;flex-direction:column;} #viewer-content{max-width:90%;max-height:85%;display:flex;align-items:center;justify-content:center;} #viewer img,#viewer video{max-width:100%;max-height:80vh;box-shadow:0 0 20px #000;} .viewer-btn{position:absolute;top:50%;transform:translateY(-50%);font-size:3rem;color:#fff;background:0 0;border:none;cursor:pointer;padding:20px;z-index:10000;} .viewer-btn:hover{color:#2563eb;} #prev-btn{left:20px;} #next-btn{right:20px;} #close-btn{position:absolute;top:20px;right:30px;font-size:2rem;color:#fff;cursor:pointer;z-index:10001;}"""
HTML_LOGIN = """<!doctype html><html lang="{{ t.lang_code }}"><head><meta charset="utf-8"><title>{{ t.login_title }}</title><style>""" + CSS_CODE + """body{display:flex;justify-content:center;align-items:center;height:100vh;flex-direction:column;} .login-box{background:var(--card);padding:2rem;border:1px solid #30363d;border-radius:6px;width:300px;text-align:center;} input{width:100%;padding:10px;margin:10px 0;background:var(--bg);border:1px solid #30363d;color:var(--fg);border-radius:4px;box-sizing:border-box;}</style></head><body>{% with messages=get_flashed_messages(with_categories=true) %}{% if messages %}{% for c, m in messages %}<div class="alert-box alert-{{ c }}" style="display:block;">{{ m }}<span class="close-btn" onclick="this.parentElement.style.display='none';">&times;</span></div>{% endfor %}{% endif %}{% endwith %}<div class="login-box"><h2>{{ t.login_heading }}</h2><form method="post"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><input type="text" name="username" placeholder="{{ t.username_placeholder }}" required autofocus><input type="password" name="password" placeholder="{{ t.password_placeholder }}" required><button type="submit" class="btn btn-green" style="width:100%">{{ t.login_btn }}</button></form><div style="margin-top:12px;font-size:12px;color:#888;"><a href="/lang/en" style="color:var(--accent);text-decoration:none;">English</a> | <a href="/lang/tr" style="color:var(--accent);text-decoration:none;">Türkçe</a></div></div></body></html>"""
HTML_SETUP = """<!doctype html><html lang="{{ t.lang_code }}"><head><meta charset="utf-8"><title>{{ t.setup_title }}</title><style>""" + CSS_CODE + """body{display:flex;justify-content:center;align-items:center;height:100vh;} .box{background:var(--card);padding:2rem;border:1px solid #30363d;border-radius:8px;width:450px;} input{width:100%;padding:10px;margin:10px 0;background:var(--bg);border:1px solid #30363d;color:var(--fg);border-radius:4px;box-sizing:border-box;} .modal{display:none;position:fixed;z-index:999;left:0;top:0;width:100%;height:100%;overflow:auto;background-color:rgba(0,0,0,.8);} .modal-content{background-color:var(--card);color:var(--fg);margin:10% auto;padding:20px;border:1px solid #888;width:500px;border-radius:8px;} .file-list{list-style:none;padding:0;margin:10px 0;max-height:300px;overflow-y:auto;border:1px solid #30363d;} .file-list li{padding:8px;border-bottom:1px solid #30363d;cursor:pointer;display:flex;align-items:center;} .file-list li:hover{background-color:#1f6feb;color:#fff;}</style><script>let currentBrowsePath="/";function openFolderModal(){document.getElementById('folderModal').style.display='block';loadDirs(currentBrowsePath);}function closeModal(){document.getElementById('folderModal').style.display='none';}function loadDirs(path){const fd=new FormData();fd.append('path',path);fd.append('csrf_token',document.querySelector('input[name="csrf_token"]').value);document.getElementById('currentPathDisplay').innerText="{{ t.loading }}";fetch('/admin/list_dirs',{method:'POST',body:fd}).then(r=>r.json()).then(data=>{if(data.error){alert(data.error);return;}currentBrowsePath=data.current;document.getElementById('currentPathDisplay').innerText=currentBrowsePath;const list=document.getElementById('dirList');list.innerHTML="";data.dirs.forEach(d=>{const li=document.createElement('li');li.innerHTML=`📁 ${d.name}`;li.onclick=()=>loadDirs(d.path);list.appendChild(li);});});}function selectCurrentFolder(){document.getElementById('sharePathInput').value=currentBrowsePath;closeModal();}function updateMonitor(){fetch('/admin/indexing_status').then(r=>r.json()).then(data=>{document.getElementById('idx-status').innerText=data.status;document.getElementById('idx-path').innerText=data.current_path;document.getElementById('idx-count').innerText=data.total_files+" Files";if(data.status.includes('Scanning')||data.status.includes('Taranıyor')){document.getElementById('idx-bar').style.display='block';}else{document.getElementById('idx-bar').style.display='none';}});}setInterval(updateMonitor,1500);</script></head><body><div class="box"><h2>{{ t.setup_heading }}</h2><div style="font-size:12px;color:#f85149;margin-bottom:20px;text-align:center;border:1px solid #f85149;padding:5px;">{{ t.setup_notice }}</div><form method="post"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><label>{{ t.username_placeholder }}</label><input type="text" name="username" required><label>{{ t.password_placeholder }}</label><input type="password" name="password" required><hr><label>{{ t.share_name_label }}</label><input type="text" name="share_name" required><label>{{ t.path_label }}</label><div style="display:flex;gap:5px;"><input type="text" id="sharePathInput" name="share_path" required><button type="button" onclick="openFolderModal()" class="btn btn-gray">{{ t.select_folder_btn }}</button></div><button type="submit" class="btn btn-green" style="width:100%;margin-top:20px;">{{ t.complete_btn }}</button></form><div style="margin-top:12px;text-align:center;font-size:12px;color:#888;"><a href="/lang/en" style="color:var(--accent);text-decoration:none;">English</a> | <a href="/lang/tr" style="color:var(--accent);text-decoration:none;">Türkçe</a></div></div><div id="folderModal" class="modal"><div class="modal-content"><h3>{{ t.select_folder_title }}</h3><div id="currentPathDisplay" style="font-family:monospace;background:var(--bg);padding:8px;">/</div><ul id="dirList" class="file-list"></ul><div style="text-align:right;"><button onclick="selectCurrentFolder()" class="btn btn-green">{{ t.select_btn }}</button><button onclick="closeModal()" class="btn btn-red">{{ t.cancel_btn }}</button></div></div></div></body></html>"""
HTML_INDEX = """<!doctype html><html lang="{{ t.lang_code }}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{{ t.files_title }}</title><style>""" + CSS_CODE + """</style></head><body><header><div class="logo">USBHDD SYSTEM</div><form class="search-box" action="" method="get"><input type="text" name="q" placeholder="{{ t.search_placeholder }}" value="{{ q }}"></form><div style="display:flex;gap:5px;">{% if is_admin %}<a href="/admin" class="btn" style="background:#8957e5;">⚙️</a>{% endif %}<a href="?sort=name" class="btn btn-gray">{{ t.sort_name }}</a><a href="?sort=date" class="btn btn-gray">{{ t.sort_date }}</a><a href="/logout" class="btn btn-red">{{ t.logout_btn }}</a></div></header><div id="js-alert" class="alert-box alert-error"><span id="js-alert-msg"></span><span class="close-btn" onclick="this.parentElement.style.display='none';">&times;</span></div>{% with messages=get_flashed_messages(with_categories=true) %}{% if messages %}{% for c, m in messages %}<div class="alert-box alert-{{ c }}" style="display:block;">{{ m }}<span class="close-btn" onclick="this.parentElement.style.display='none';">&times;</span></div>{% endfor %}{% endif %}{% endwith %}<div class="toolbar"><div class="breadcrumb"><a href="/">🏠</a>{% for crumb in breadcrumbs %}<span>/</span> <a href="/{{ crumb.path }}">{{ crumb.name }}</a>{% endfor %}</div><div style="margin-left:auto;display:flex;gap:10px;"><form action="/mkdir/{{ path }}" method="post" style="display:flex;"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><input type="text" name="foldername" placeholder="{{ t.folder_placeholder }}" style="width:80px;padding:5px;" required><button type="submit" class="btn btn-blue">+</button></form><form action="/upload/{{ path }}" method="post" enctype="multipart/form-data"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><label class="btn btn-blue" style="cursor:pointer;">⬆ <input type="file" name="file" style="display:none" onchange="this.form.submit()"></label></form></div></div><div class="grid">{% if path %}{% set parts=path.split('/') %}<div class="card" onclick="location.href='/{{ parts[:-1]|join('/') }}'" style="cursor:pointer;display:flex;align-items:center;justify-content:center;background:#222;color:#fff;"><div style="font-size:30px;">⬅</div></div>{% endif %}{% for item in items %}<div class="card">{% if not item.is_drive %}<div class="actions"><a href="/delete/{{ item.path }}" onclick="return confirm('{{ t.confirm_delete }}')" class="del-btn">✕</a></div>{% endif %}<a href="/{{ item.path }}" {% if not item.is_dir %}data-file{% endif %}><div class="thumb">{% if item.is_drive %} 💾 {% elif item.is_dir %} <span class="icon-dir">📁</span>{% else %}{% set n=item.name.lower() %}{% if n.endswith(('.jpg','.jpeg','.png','.webp','.gif')) %}<img src="/thumb/{{ item.path }}" loading="lazy">{% elif n.endswith(('.mp4','.mov','.mkv','.avi')) %}<span class="icon-vid">🎬</span>{% elif n.endswith('.pdf') %}<span class="icon-pdf">📕</span>{% else %}<span class="icon-file">📄</span>{% endif %}{% endif %}</div></a><div class="info"><a href="/{{ item.path }}" class="name">{{ item.name }}</a><div class="meta"><span>{{ item.human_size if not item.is_dir else '' }}</span></div></div></div>{% endfor %}</div><div id="viewer"><div id="close-btn" onclick="closeViewer()">✕</div><div id="prev-btn" class="viewer-btn">◀</div><div id="viewer-content"><img id="viewer-img" style="display:none;"><video id="viewer-video" controls autoplay style="display:none;"></video></div><div id="next-btn" class="viewer-btn">▶</div></div><script>let currentIndex=0;let mediaList=[];document.addEventListener("DOMContentLoaded",()=>{const allLinks=document.querySelectorAll('a[data-file]');const allowedExts=['.jpg','.jpeg','.png','.gif','.webp','.mp4','.mov','.mkv','.avi'];allLinks.forEach((link)=>{const href=link.getAttribute('href');const lowerHref=href.toLowerCase();if(allowedExts.some(ext=>lowerHref.endsWith(ext))){link.addEventListener('click',(e)=>{e.preventDefault();openViewer(href);});mediaList.push(href);}});});function openViewer(src){currentIndex=mediaList.indexOf(src);updateViewer();document.getElementById('viewer').style.display='flex';}function closeViewer(){document.getElementById('viewer').style.display='none';document.getElementById('viewer-video').pause();}function updateViewer(){if(currentIndex<0)currentIndex=mediaList.length-1;if(currentIndex>=mediaList.length)currentIndex=0;const src=mediaList[currentIndex];const isVideo=src.match(/\.(mp4|mov|mkv|avi)$/i);const imgEl=document.getElementById('viewer-img');const vidEl=document.getElementById('viewer-video');if(isVideo){imgEl.style.display='none';vidEl.style.display='block';vidEl.src=src;}else{vidEl.style.display='none';vidEl.pause();imgEl.style.display='block';imgEl.src=src;}}document.getElementById('prev-btn').addEventListener('click',(e)=>{e.stopPropagation();currentIndex--;updateViewer();});document.getElementById('next-btn').addEventListener('click',(e)=>{e.stopPropagation();currentIndex++;updateViewer();});document.addEventListener('keydown',(e)=>{if(document.getElementById('viewer').style.display==='flex'){if(e.key==='ArrowLeft'){currentIndex--;updateViewer();}if(e.key==='ArrowRight'){currentIndex++;updateViewer();}if(e.key==='Escape')closeViewer();}});</script></body></html>"""
HTML_ADMIN = """<!doctype html><html lang="{{ t.lang_code }}"><head><meta charset="utf-8"><title>{{ t.admin_title }}</title><style>""" + CSS_CODE + """table{width:100%;border-collapse:collapse;margin-bottom:20px;border:1px solid #30363d;} th,td{padding:12px;border-bottom:1px solid #30363d;} .modal{display:none;position:fixed;z-index:999;left:0;top:0;width:100%;height:100%;overflow:auto;background-color:rgba(0,0,0,.8);} .modal-content{background-color:var(--card);color:var(--fg);margin:5% auto;padding:20px;border:1px solid #888;width:600px;border-radius:8px;} .file-list{list-style:none;padding:0;margin:10px 0;max-height:400px;overflow-y:auto;border:1px solid #30363d;} .file-list li{padding:8px;border-bottom:1px solid #30363d;cursor:pointer;} .file-list li:hover{background-color:#1f6feb;color:#fff;} script{font-family:monospace;}</style><script>function togglePerm(uid,sid,cb){const fd=new FormData();fd.append('user_id',uid);fd.append('share_id',sid);fd.append('action',cb.checked?'add':'remove');fd.append('csrf_token','{{ csrf_token() }}');fetch('/admin/toggle_perm',{method:'POST',body:fd});}let currentBrowsePath="/";function openFolderModal(){document.getElementById('folderModal').style.display='block';loadDirs(currentBrowsePath);}function closeModal(){document.getElementById('folderModal').style.display='none';}function loadDirs(path){const fd=new FormData();fd.append('path',path);fd.append('csrf_token','{{ csrf_token() }}');document.getElementById('currentPathDisplay').innerText="{{ t.loading }}";fetch('/admin/list_dirs',{method:'POST',body:fd}).then(r=>r.json()).then(data=>{if(data.error){alert(data.error);return;}currentBrowsePath=data.current;document.getElementById('currentPathDisplay').innerText=currentBrowsePath;const list=document.getElementById('dirList');list.innerHTML="";data.dirs.forEach(d=>{const li=document.createElement('li');li.innerHTML=`📁 ${d.name}`;li.onclick=()=>loadDirs(d.path);list.appendChild(li);});});}function selectCurrentFolder(){document.getElementById('sharePathInput').value=currentBrowsePath;closeModal();}function updateMonitor(){fetch('/admin/indexing_status').then(r=>r.json()).then(data=>{document.getElementById('idx-status').innerText=data.status;document.getElementById('idx-path').innerText=data.current_path;document.getElementById('idx-count').innerText=data.total_files+" Files";if(data.status.includes('Scanning')||data.status.includes('Taranıyor')){document.getElementById('idx-bar').style.display='block';}else{document.getElementById('idx-bar').style.display='none';}});}setInterval(updateMonitor,1500);</script></head><body><div class="container"><a href="/" class="btn btn-gray">{{ t.back_btn }}</a><div style="float:right;padding:10px;font-size:12px;"><a href="/lang/en" style="color:var(--accent);text-decoration:none;">English</a> | <a href="/lang/tr" style="color:var(--accent);text-decoration:none;">Türkçe</a></div><div class="monitor-box"><h3>{{ t.monitor_title }}</h3><div class="monitor-row"><span>{{ t.monitor_status }}</span> <b id="idx-status" style="color:#fbbf24">{{ t.loading }}</b></div><div class="monitor-row"><span>{{ t.monitor_processing }}</span> <b id="idx-path" style="font-size:12px;opacity:.8">...</b></div><div class="monitor-row"><span>{{ t.monitor_total }}</span> <b id="idx-count">0</b></div><div class="monitor-bar" id="idx-bar" style="display:none;"><div class="monitor-bar-inner"></div></div></div>{% with messages=get_flashed_messages(with_categories=true) %}{% if messages %}{% for c, m in messages %}<div style="padding:10px;margin:20px 0;background:var(--accent);color:#fff;">{{ m }}</div>{% endfor %}{% endif %}{% endwith %}<h2>{{ t.users_heading }}</h2><table><tr><th>{{ t.user_col }}</th><th>{{ t.role_col }}</th><th>{{ t.delete_col }}</th></tr>{% for u in users %}<tr><td>{{ u['username'] }}</td><td>{{ u['role'] }}</td><td>{% if u['role']!='admin' %}<a href="/admin/delete_user/{{ u['id'] }}" onclick="return confirm('{{ t.confirm_delete }}')" class="btn btn-red">{{ t.delete_btn }}</a>{% endif %}</td></tr>{% endfor %}<tr><form action="/admin/add_user" method="post"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><td><input type="text" name="username" placeholder="{{ t.user_col }}" required></td><td><input type="password" name="password" placeholder="{{ t.password_placeholder }}" required></td><td><button type="submit" class="btn btn-green">{{ t.add_btn }}</button></td></form></tr></table><h2>{{ t.shares_heading }}</h2><table><tr><th>{{ t.name_col }}</th><th>{{ t.path_col }}</th><th>{{ t.remove_col }}</th></tr>{% for s in shares %}<tr><td>{{ s['name'] }}</td><td>{{ s['path'] }}</td><td><a href="/admin/delete_share/{{ s['id'] }}" onclick="return confirm('{{ t.confirm_delete }}')" class="btn btn-red">{{ t.delete_btn }}</a></td></tr>{% endfor %}<tr><form action="/admin/add_share" method="post"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><td><input type="text" name="name" placeholder="{{ t.name_col }}" required></td><td style="display:flex;"><input type="text" id="sharePathInput" name="path" required><button type="button" onclick="openFolderModal()" class="btn btn-gray">{{ t.select_folder_btn }}</button></td><td><button type="submit" class="btn btn-blue">{{ t.add_btn }}</button></td></form></tr></table><h3>{{ t.permissions_heading }}</h3><div style="overflow-x:auto;"><table border="1"><tr><th>{{ t.user_folder_col }}</th>{% for s in shares %}<th>{{ s['name'] }}</th>{% endfor %}</tr>{% for u in users %}{% if u['role']!='admin' %}<tr><td><b>{{ u['username'] }}</b></td>{% for s in shares %}<td style="text-align:center;"><input type="checkbox" onchange="togglePerm({{ u['id'] }}, {{ s['id'] }}, this)" {% if u['id'] in permissions and s['id'] in permissions[u['id']] %}checked{% endif %}></td>{% endfor %}</tr>{% endif %}{% endfor %}</table></div><div id="folderModal" class="modal"><div class="modal-content"><h3>{{ t.select_folder_title }}</h3><div id="currentPathDisplay" style="background:var(--bg);padding:5px;">/</div><ul id="dirList" class="file-list"></ul><div style="text-align:right;"><button onclick="selectCurrentFolder()" class="btn btn-green">{{ t.select_btn }}</button><button onclick="closeModal()" class="btn btn-red">{{ t.cancel_btn }}</button></div></div></div></div></body></html>"""

# --- YARDIMCI FONKSİYONLAR ---
def init_db():
    # data/ klasörünü oluştur ve güvenli izinleri uygula (sadece sahip okuyabilir/yazabilir)
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    if os.name == 'posix':
        try:
            os.chmod(DATA_DIR, stat.S_IRWXU)             # 700: sadece sahip
            os.chmod(CACHE_DIR, stat.S_IRWXU)            # 700: sadece sahip
        except Exception: pass
    conn = get_db_connection()
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('CREATE TABLE IF NOT EXISTS bans (ip TEXT PRIMARY KEY, attempts INTEGER, timestamp REAL)')
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT DEFAULT "user")')
    conn.execute('CREATE TABLE IF NOT EXISTS shares (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, path TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS permissions (user_id INTEGER, share_id INTEGER, FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(share_id) REFERENCES shares(id))')
    conn.execute('CREATE TABLE IF NOT EXISTS file_index (share_id INTEGER, parent_hash TEXT, enc_name TEXT, enc_path TEXT, is_dir INTEGER)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_parent ON file_index(parent_hash)')
    conn.commit()
    conn.close()
    if os.name == 'posix':
        try: os.chmod(DB_FILE, stat.S_IRUSR | stat.S_IWUSR)   # 600: sadece sahip
        except: pass

def get_parent_hash(path):
    return hashlib.md5(path.encode('utf-8')).hexdigest()

def get_user_shares(user_id, role):
    shares = {}
    conn = get_db_connection()
    cur = conn.cursor()
    if role == 'admin': cur.execute("SELECT id, name, path FROM shares")
    else: cur.execute("SELECT s.id, s.name, s.path FROM shares s JOIN permissions p ON s.id = p.share_id WHERE p.user_id = ?", (user_id,))
    for row in cur.fetchall(): shares[row['name']] = {"path": row['path'], "id": row['id']}
    conn.close()
    return shares

def get_drive_info(path, user_id, role):
    shares = get_user_shares(user_id, role)
    parts = path.strip("/").split("/", 1)
    drive_name = parts[0]
    if drive_name not in shares: return None, None, None, None
    real_root = os.path.abspath(shares[drive_name]['path'])
    rel_path = parts[1] if len(parts) > 1 else ""
    abs_path = os.path.abspath(os.path.join(real_root, rel_path))
    if not abs_path.startswith(real_root): return None, None, None, None
    return drive_name, rel_path, abs_path, shares[drive_name]['id']

def allowed_file(filename): return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def human_size(size):
    for unit in ['B','KB','MB','GB','TB']:
        if size < 1024: return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"

def check_ban_status(ip):
    conn = get_db_connection()
    cur = conn.cursor(); cur.execute("SELECT attempts, timestamp FROM bans WHERE ip = ?", (ip,))
    row = cur.fetchone()
    if row and row[0] >= 5:
        if time.time() - row[1] < 900: conn.close(); return True
        else: conn.execute("DELETE FROM bans WHERE ip = ?", (ip,)); conn.commit()
    conn.close()
    return False

def record_failed_attempt(ip):
    now = time.time()
    conn = get_db_connection()
    cur = conn.cursor(); cur.execute("SELECT attempts FROM bans WHERE ip = ?", (ip,))
    if cur.fetchone(): conn.execute("UPDATE bans SET attempts = attempts + 1, timestamp = ? WHERE ip = ?", (now, ip))
    else: conn.execute("INSERT INTO bans (ip, attempts, timestamp) VALUES (?, ?, ?)", (ip, 1, now))
    conn.commit()
    conn.close()

def clear_ban(ip):
    conn = get_db_connection()
    conn.execute("DELETE FROM bans WHERE ip = ?", (ip,)); conn.commit()
    conn.close()

def is_setup_completed():
    try:
        conn = get_db_connection()
        cur = conn.cursor(); cur.execute("SELECT count(*) FROM users WHERE role='admin'")
        res = cur.fetchone()[0] > 0
        conn.close()
        return res
    except: return False

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_setup_completed(): return redirect(url_for('setup'))
        if 'user_id' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin': abort(403)
        return f(*args, **kwargs)
    return decorated_function

# --- INDEX MOTORU ---
def perform_full_scan():
    try:
        INDEX_STATUS["status"] = "🚀 Scanning..."
        INDEX_STATUS["total_files"] = 0
        conn = get_db_connection()
        conn.execute('DELETE FROM file_index')
        conn.commit()
        cur = conn.cursor()
        cur.execute("SELECT id, name, path FROM shares")
        all_shares = cur.fetchall()
        total_counter = 0
        for s_id, s_name, s_path in all_shares:
            INDEX_STATUS["status"] = f"📂 Scanning: {s_name}"
            if os.path.exists(s_path):
                for root, dirs, files in os.walk(s_path):
                    INDEX_STATUS["current_path"] = root
                    parent_h = get_parent_hash(root)
                    batch = []
                    for name in files + dirs:
                        full_p = os.path.join(root, name)
                        try:
                            e_name = INDEX_CIPHER.encrypt(name.encode()).decode()
                            e_path = INDEX_CIPHER.encrypt(full_p.encode()).decode()
                            is_d = 1 if os.path.isdir(full_p) else 0
                            batch.append((s_id, parent_h, e_name, e_path, is_d))
                            total_counter += 1
                        except: pass
                    if batch: conn.executemany('INSERT INTO file_index VALUES (?, ?, ?, ?, ?)', batch); conn.commit()
                    if total_counter % 50 == 0: INDEX_STATUS["total_files"] = total_counter
        conn.close()
        INDEX_STATUS["status"] = "✅ Ready"
        INDEX_STATUS["current_path"] = f"Last scan: {datetime.now().strftime('%H:%M')}"
    except Exception as e: INDEX_STATUS["status"] = f"❌ Error: {str(e)}"

def background_scanner_loop():
    conn = get_db_connection()
    try:
        cur = conn.cursor(); cur.execute("SELECT count(*) FROM file_index"); count = cur.fetchone()[0]
    except: count = 0
    conn.close()

    if count == 0:
        print("--- Database empty, starting initial scan ---")
        perform_full_scan()
    else:
        print("--- Database loaded, using persistent cache ---")
        INDEX_STATUS["status"] = "✅ Ready (Cached)"
        INDEX_STATUS["total_files"] = count

    while True:
        now = datetime.now()
        if 2 <= now.hour < 6:
            print(f"[{now}] Night mode started. Scanning...")
            perform_full_scan()
            time.sleep(14400)
        else:
            time.sleep(60)

threading.Thread(target=background_scanner_loop, daemon=True).start()

@app.route("/admin/indexing_status")
@login_required
@admin_required
def indexing_status_api(): return jsonify(INDEX_STATUS)

# --- ROTALAR ---
@app.route("/setup", methods=["GET", "POST"])
def setup():
    if is_setup_completed(): return redirect(url_for('login'))
    if request.method == "POST":
        u, p = request.form.get("username", "").strip(), request.form.get("password", "").strip()
        sn, sp = request.form.get("share_name", "").strip(), request.form.get("share_path", "").strip()
        if not (u and p and sn and sp):
            flash("Tüm alanları doldurun.", "error")
        else:
            try:
                conn = get_db_connection()
                conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'admin')", (u, generate_password_hash(p)))
                conn.execute("INSERT INTO shares (name, path) VALUES (?, ?)", (sn, sp))
                conn.commit()
                conn.close()
                try:
                    if os.name == 'posix': os.chmod(DB_FILE, stat.S_IRUSR | stat.S_IWUSR)
                except Exception: pass
                return redirect(url_for('login'))
            except Exception as e:
                print(f"[SETUP HATA] {e}")
                flash(f"Hata: {e}", "error")
    return render_template_string(HTML_SETUP, t=get_lang())

@app.route("/login", methods=["GET", "POST"])
def login():
    if not is_setup_completed(): return redirect(url_for('setup'))
    ip = request.remote_addr
    if check_ban_status(ip): return render_template_string(HTML_LOGIN, t=get_lang()), 403
    if request.method == "POST":
        u, p = request.form.get("username"), request.form.get("password")
        try:
            conn = get_db_connection()
            user = conn.execute("SELECT * FROM users WHERE username = ?", (u,)).fetchone()
            conn.close()
            if user and check_password_hash(user['password'], p):
                session['user_id'], session['username'], session['role'] = user['id'], user['username'], user['role']
                clear_ban(ip)
                return redirect(url_for('browse'))
            else:
                record_failed_attempt(ip); time.sleep(2); flash("Hatalı giriş!", "error")
        except: flash("Hata.", "error")
    return render_template_string(HTML_LOGIN, t=get_lang())

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for('login'))

@app.route("/lang/<string:code>")
def set_language(code):
    if code in LANGUAGES:
        session['lang'] = code
    return redirect(request.referrer or url_for('login'))

@app.route("/admin")
@login_required
@admin_required
def admin_panel():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    shares = conn.execute("SELECT * FROM shares").fetchall()
    perms = {}; rows = conn.execute("SELECT * FROM permissions").fetchall()
    for r in rows:
        if r['user_id'] not in perms: perms[r['user_id']] = []
        perms[r['user_id']].append(r['share_id'])
    conn.close()
    return render_template_string(HTML_ADMIN, users=users, shares=shares, permissions=perms, t=get_lang())

@app.route("/admin/list_dirs", methods=["POST"])
def list_dirs():
    if is_setup_completed() and (session.get('role') != 'admin'): return jsonify({'error': 'Yetkisiz'}), 403
    current_path = request.form.get('path', '/')
    if not os.path.exists(current_path): current_path = '/'
    dirs = []
    try:
        parent = os.path.dirname(current_path)
        if parent != current_path: dirs.append({'name': '..', 'path': parent})
        with os.scandir(current_path) as it:
            for entry in it:
                if entry.is_dir() and not entry.name.startswith('.'): dirs.append({'name': entry.name, 'path': entry.path})
        return jsonify({'current': current_path, 'dirs': sorted(dirs, key=lambda x: x['name'])})
    except: return jsonify({'error': 'Hata'})

@app.route("/admin/add_user", methods=["POST"])
@login_required
@admin_required
def add_user():
    u, p = request.form.get("username"), request.form.get("password")
    if u and p:
        conn = get_db_connection(); conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, generate_password_hash(p))); conn.commit(); conn.close()
    return redirect(url_for('admin_panel'))

@app.route("/admin/delete_user/<int:uid>")
@login_required
@admin_required
def delete_user(uid):
    if uid != session['user_id']:
        conn = get_db_connection(); conn.execute("DELETE FROM users WHERE id=?", (uid,)); conn.execute("DELETE FROM permissions WHERE user_id=?", (uid,)); conn.commit(); conn.close()
    return redirect(url_for('admin_panel'))

@app.route("/admin/add_share", methods=["POST"])
@login_required
@admin_required
def add_share():
    n, p = request.form.get("name"), request.form.get("path")
    if n and p:
        conn = get_db_connection(); conn.execute("INSERT INTO shares (name, path) VALUES (?, ?)", (n, p)); conn.commit(); conn.close()
    return redirect(url_for('admin_panel'))

@app.route("/admin/delete_share/<int:sid>")
@login_required
@admin_required
def delete_share(sid):
    conn = get_db_connection(); conn.execute("DELETE FROM shares WHERE id=?", (sid,)); conn.execute("DELETE FROM permissions WHERE share_id=?", (sid,)); conn.commit(); conn.close()
    return redirect(url_for('admin_panel'))

@app.route("/admin/toggle_perm", methods=["POST"])
@login_required
@admin_required
def toggle_perm():
    uid, sid, act = request.form.get("user_id"), request.form.get("share_id"), request.form.get("action")
    conn = get_db_connection()
    if act == 'add': conn.execute("INSERT OR IGNORE INTO permissions (user_id, share_id) VALUES (?, ?)", (uid, sid))
    else: conn.execute("DELETE FROM permissions WHERE user_id=? AND share_id=?", (uid, sid))
    conn.commit(); conn.close()
    return "OK"

@app.route("/thumb/<path:path>")
@login_required
def thumbnail(path):
    d, r, a, s = get_drive_info(path, session['user_id'], session['role'])
    if not a or not os.path.exists(a) or not allowed_file(a): abort(404)
    tp = os.path.join(CACHE_DIR, hashlib.md5(a.encode()).hexdigest() + ".enc")
    if os.path.exists(tp):
        try:
            with open(tp, "rb") as f: return send_file(io.BytesIO(CACHE_CIPHER.decrypt(f.read())), mimetype='image/jpeg')
        except: pass
    try:
        img = Image.open(a); img.thumbnail((300, 300)); img=img.convert("RGB")
        b=io.BytesIO(); img.save(b, format='JPEG', quality=70); data=b.getvalue()
        with open(tp, "wb") as f: f.write(CACHE_CIPHER.encrypt(data))
        return send_file(io.BytesIO(data), mimetype='image/jpeg')
    except: abort(404)

@app.route("/delete/<path:path>")
@login_required
def delete_item(path):
    d, r, a, s = get_drive_info(path, session['user_id'], session['role'])
    if not a: abort(403)
    if os.path.isdir(a): shutil.rmtree(a)
    else: os.remove(a)
    try:
        e_path = INDEX_CIPHER.encrypt(a.encode()).decode()
        conn = get_db_connection(); conn.execute("DELETE FROM file_index WHERE enc_path = ?", (e_path,)); conn.commit(); conn.close()
    except: pass
    return redirect(url_for('browse', path=os.path.dirname(path)))

@app.route("/mkdir/<path:path>", methods=["POST"])
@login_required
def mkdir(path):
    d, r, a, s = get_drive_info(path, session['user_id'], session['role'])
    f = request.form.get("foldername")
    if a and f: 
        new_path = os.path.join(a, secure_filename(f))
        try: os.makedirs(new_path)
        except: pass
    return redirect(url_for('browse', path=path))

@app.route("/upload/<path:path>", methods=["POST"])
@login_required
def upload(path):
    d, r, a, s = get_drive_info(path, session['user_id'], session['role'])
    f = request.files.get('file')
    if a and f and allowed_file(f.filename):
        f.save(os.path.join(a, secure_filename(f.filename)))
    return redirect(url_for('browse', path=path))

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
@login_required
def browse(path):
    q = request.args.get("q", "").lower()
    shares = get_user_shares(session['user_id'], session['role'])
    if not path:
        items = [{"name": k, "path": k, "is_dir": True, "is_drive": True} for k in shares]
        return render_template_string(HTML_INDEX, items=items, path="", breadcrumbs=[], is_admin=(session['role']=='admin'), q=q, t=get_lang())
    
    d_name, rel_p, abs_p, s_id = get_drive_info(path, session['user_id'], session['role'])
    if not abs_p: abort(404)
    if os.path.isfile(abs_p): return send_from_directory(os.path.dirname(abs_p), os.path.basename(abs_p))

    items = []
    current_hash = get_parent_hash(abs_p)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT enc_name, enc_path, is_dir FROM file_index WHERE parent_hash = ?", (current_hash,))
        for row in cur.fetchall():
            try:
                name = INDEX_CIPHER.decrypt(row['enc_name'].encode()).decode()
                if q and q not in name.lower(): continue
                items.append({"name": name, "path": os.path.join(path, name).replace("\\", "/"), "is_dir": bool(row['is_dir']), "human_size": ""})
            except: continue
    finally: conn.close()

    if not items and not q:
        if os.path.exists(abs_p):
            with os.scandir(abs_p) as it:
                for entry in it:
                    if entry.name.startswith('.'): continue
                    items.append({"name": entry.name, "path": os.path.join(path, entry.name).replace("\\", "/"), "is_dir": entry.is_dir(), "human_size": ""})

    parts = path.split("/")
    breadcrumbs = []
    acc = ""
    for part in parts:
        acc = (acc + "/" + part).strip("/")
        breadcrumbs.append({"name": part, "path": acc})

    return render_template_string(HTML_INDEX, items=items, path=path, breadcrumbs=breadcrumbs, q=q, is_admin=(session['role']=='admin'), t=get_lang())

# --- OTO PORT ---
def find_available_port(start_port):
    port = start_port
    while port < 65535:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try: sock.bind(('0.0.0.0', port)); return port
            except OSError: port += 1
    return start_port

# Gunicorn veya doğrudan çalıştırma fark etmeksizin her zaman başlat
init_db()
check_and_create_certs()

if __name__ == "__main__":
    port = find_available_port(8143)
    print(f"--- SUNUCU BAŞLATILIYOR: https://localhost:{port} ---")
    app.run(host='0.0.0.0', port=port, ssl_context=(CERT_FILE, KEY_FILE))
