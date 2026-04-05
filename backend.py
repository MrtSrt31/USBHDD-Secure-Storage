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
        'theme_light': 'Light',
        'theme_auto': 'Auto',
        'theme_dark': 'Dark',
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
        'theme_light': 'Açık',
        'theme_auto': 'Otomatik',
        'theme_dark': 'Koyu',
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
CSS_CODE = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
:root{
  --bg:#0f1117;--bg2:#161b27;--bg3:#1e2435;--border:#2a3149;
  --fg:#e2e8f0;--fg2:#94a3b8;--fg3:#64748b;
  --accent:#6366f1;--accent-hover:#818cf8;--accent-dim:rgba(99,102,241,.15);
  --danger:#ef4444;--danger-hover:#f87171;--danger-dim:rgba(239,68,68,.15);
  --success:#22c55e;--success-hover:#4ade80;--success-dim:rgba(34,197,94,.15);
  --warn:#f59e0b;
  --shadow:0 4px 24px rgba(0,0,0,.4);
  --radius:10px;--radius-sm:6px;
}
body{background:var(--bg);color:var(--fg);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:14px;line-height:1.6;min-height:100vh;}
a{color:inherit;text-decoration:none;}
hr{border:none;border-top:1px solid var(--border);margin:16px 0;}

/* ── NAVBAR ── */
.navbar{display:flex;align-items:center;gap:12px;padding:0 20px;height:56px;background:var(--bg2);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100;backdrop-filter:blur(8px);}
.navbar-brand{display:flex;align-items:center;gap:8px;font-weight:700;font-size:15px;color:var(--fg);letter-spacing:.5px;flex-shrink:0;}
.navbar-brand svg{width:22px;height:22px;color:var(--accent);}
.navbar-search{flex:1;max-width:320px;}
.navbar-search input{width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--fg);padding:7px 12px 7px 34px;border-radius:20px;font-size:13px;outline:none;transition:border-color .2s;}
.navbar-search{position:relative;}
.navbar-search::before{content:"⌕";position:absolute;left:11px;top:50%;transform:translateY(-50%);color:var(--fg3);font-size:16px;pointer-events:none;}
.navbar-search input:focus{border-color:var(--accent);}
.navbar-actions{display:flex;align-items:center;gap:6px;margin-left:auto;}
.lang-switch{display:flex;align-items:center;gap:4px;background:var(--bg3);border:1px solid var(--border);border-radius:20px;padding:3px 10px;font-size:12px;color:var(--fg2);}
.lang-switch a{color:var(--fg3);padding:1px 4px;border-radius:4px;transition:color .15s;}
.lang-switch a:hover,.lang-switch a.active{color:var(--accent);}
.lang-switch span{color:var(--border);}

/* ── BUTTONS ── */
.btn{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border-radius:var(--radius-sm);border:none;cursor:pointer;font-size:13px;font-weight:500;transition:all .15s;white-space:nowrap;text-decoration:none;}
.btn:hover{filter:brightness(1.15);}
.btn-primary{background:var(--accent);color:#fff;}
.btn-danger{background:var(--danger-dim);color:var(--danger);border:1px solid rgba(239,68,68,.3);}
.btn-danger:hover{background:var(--danger);color:#fff;}
.btn-ghost{background:transparent;color:var(--fg2);border:1px solid var(--border);}
.btn-ghost:hover{background:var(--bg3);color:var(--fg);}
.btn-success{background:var(--success-dim);color:var(--success);border:1px solid rgba(34,197,94,.3);}
.btn-success:hover{background:var(--success);color:#fff;}
.btn-icon{padding:6px;border-radius:var(--radius-sm);background:transparent;border:1px solid var(--border);color:var(--fg2);cursor:pointer;transition:all .15s;}
.btn-icon:hover{background:var(--bg3);color:var(--fg);}
/* legacy compat */
.btn-red{background:var(--danger-dim);color:var(--danger);border:1px solid rgba(239,68,68,.3);}
.btn-red:hover{background:var(--danger);color:#fff;}
.btn-blue{background:var(--accent);color:#fff;}
.btn-gray{background:var(--bg3);color:var(--fg2);border:1px solid var(--border);}
.btn-green{background:var(--success-dim);color:var(--success);border:1px solid rgba(34,197,94,.3);}
.btn-green:hover{background:var(--success);color:#fff;}

/* ── ALERTS ── */
.alert-box{display:none;padding:10px 16px;margin:10px 20px;border-radius:var(--radius-sm);font-size:13px;font-weight:500;position:relative;}
.alert-box[style*="block"]{display:flex!important;align-items:center;justify-content:space-between;}
.alert-error{background:var(--danger-dim);color:var(--danger);border:1px solid rgba(239,68,68,.25);}
.alert-success{background:var(--success-dim);color:var(--success);border:1px solid rgba(34,197,94,.25);}
.close-btn{cursor:pointer;font-size:16px;opacity:.6;margin-left:12px;flex-shrink:0;background:none;border:none;color:inherit;}
.close-btn:hover{opacity:1;}

/* ── TOOLBAR / BREADCRUMB ── */
.toolbar{display:flex;align-items:center;gap:10px;padding:10px 20px;border-bottom:1px solid var(--border);background:var(--bg2);overflow-x:auto;flex-wrap:wrap;}
.breadcrumb{display:flex;align-items:center;gap:4px;font-size:13px;color:var(--fg3);flex:1;min-width:0;white-space:nowrap;overflow:hidden;}
.breadcrumb a{color:var(--accent);padding:2px 4px;border-radius:4px;transition:background .15s;}
.breadcrumb a:hover{background:var(--accent-dim);}
.breadcrumb .sep{color:var(--fg3);margin:0 2px;}
.toolbar-actions{display:flex;align-items:center;gap:6px;flex-shrink:0;}
.toolbar-actions input[type=text]{background:var(--bg3);border:1px solid var(--border);color:var(--fg);padding:6px 10px;border-radius:var(--radius-sm);font-size:13px;width:100px;outline:none;}
.toolbar-actions input[type=text]:focus{border-color:var(--accent);}

/* ── FILE GRID ── */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;padding:20px;}
.card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;position:relative;transition:border-color .2s,box-shadow .2s,transform .15s;cursor:pointer;}
.card:hover{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent),var(--shadow);transform:translateY(-2px);}
.thumb{width:100%;height:110px;display:flex;align-items:center;justify-content:center;font-size:38px;background:var(--bg3);overflow:hidden;}
.thumb img{width:100%;height:100%;object-fit:cover;transition:transform .3s;}
.card:hover .thumb img{transform:scale(1.08);}
.card-info{padding:8px 10px;}
.card-name{font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--fg);display:block;margin-bottom:2px;}
.card-meta{font-size:11px;color:var(--fg3);}
.card-actions{position:absolute;top:6px;right:6px;opacity:0;transition:opacity .15s;}
.card:hover .card-actions{opacity:1;}
.del-btn{background:rgba(239,68,68,.85);color:#fff;border:none;width:22px;height:22px;border-radius:4px;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:12px;text-decoration:none;transition:background .15s;}
.del-btn:hover{background:var(--danger);}
.back-card{background:var(--bg3);border:1px dashed var(--border);display:flex;align-items:center;justify-content:center;font-size:28px;color:var(--fg3);}
.back-card:hover{border-color:var(--accent);color:var(--accent);}

/* ── ICON COLORS ── */
.icon-dir{color:#fbbf24;}
.icon-vid{color:#f87171;}
.icon-doc{color:#60a5fa;}
.icon-xls{color:#34d399;}
.icon-ppt{color:#f97316;}
.icon-pdf{color:#ef4444;}
.icon-img{color:#a78bfa;}
.icon-file{color:var(--fg3);}

/* ── MEDIA VIEWER ── */
#viewer{position:fixed;inset:0;background:rgba(0,0,0,.96);display:none;z-index:9999;align-items:center;justify-content:center;flex-direction:column;}
#viewer-content{max-width:90vw;max-height:85vh;display:flex;align-items:center;justify-content:center;}
#viewer img,#viewer video{max-width:100%;max-height:80vh;border-radius:4px;box-shadow:0 0 40px rgba(0,0,0,.8);}
.viewer-btn{position:absolute;top:50%;transform:translateY(-50%);font-size:2.5rem;color:rgba(255,255,255,.5);background:0 0;border:none;cursor:pointer;padding:20px;z-index:10000;transition:color .15s;}
.viewer-btn:hover{color:#fff;}
#prev-btn{left:10px;}
#next-btn{right:10px;}
#vclose-btn{position:absolute;top:16px;right:20px;font-size:1.8rem;color:rgba(255,255,255,.6);cursor:pointer;z-index:10001;background:none;border:none;transition:color .15s;}
#vclose-btn:hover{color:#fff;}

/* ── AUTH PAGES ── */
.auth-page{min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--bg);background-image:radial-gradient(ellipse at 50% 0,rgba(99,102,241,.12) 0,transparent 60%);}
.auth-card{width:380px;background:var(--bg2);border:1px solid var(--border);border-radius:16px;padding:36px 32px;box-shadow:var(--shadow);}
.auth-logo{display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:28px;}
.auth-logo-icon{width:40px;height:40px;background:var(--accent-dim);border:1px solid var(--accent);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;}
.auth-logo-text{font-size:18px;font-weight:700;letter-spacing:.5px;}
.auth-title{font-size:22px;font-weight:700;margin-bottom:6px;text-align:center;}
.auth-sub{font-size:13px;color:var(--fg3);text-align:center;margin-bottom:24px;}
.form-group{margin-bottom:14px;}
.form-label{display:block;font-size:12px;font-weight:600;color:var(--fg2);margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px;}
.form-input{width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--fg);padding:10px 13px;border-radius:var(--radius-sm);font-size:14px;outline:none;transition:border-color .2s;}
.form-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-dim);}
.form-input::placeholder{color:var(--fg3);}
.auth-btn{width:100%;padding:11px;border-radius:var(--radius-sm);border:none;background:var(--accent);color:#fff;font-size:14px;font-weight:600;cursor:pointer;transition:background .2s;margin-top:6px;}
.auth-btn:hover{background:var(--accent-hover);}
.auth-footer{text-align:center;margin-top:20px;font-size:12px;color:var(--fg3);}
.auth-footer a{color:var(--accent);}
.setup-section{border-top:1px solid var(--border);padding-top:16px;margin-top:6px;}
.setup-section-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--fg3);margin-bottom:12px;}
.setup-notice{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.2);border-radius:var(--radius-sm);padding:8px 12px;font-size:12px;color:var(--danger);margin-bottom:16px;text-align:center;}
.input-with-btn{display:flex;gap:6px;}
.input-with-btn .form-input{flex:1;}

/* ── ADMIN PANEL ── */
.admin-wrap{max-width:1100px;margin:0 auto;padding:24px 20px;}
.admin-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;gap:12px;}
.admin-header h1{font-size:20px;font-weight:700;}
.section-card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);margin-bottom:20px;overflow:hidden;}
.section-head{padding:14px 18px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
.section-head h2{font-size:15px;font-weight:600;color:var(--fg);}
.data-table{width:100%;border-collapse:collapse;}
.data-table th{padding:10px 16px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--fg3);border-bottom:1px solid var(--border);}
.data-table td{padding:10px 16px;border-bottom:1px solid var(--border);font-size:13px;color:var(--fg2);}
.data-table tr:last-child td{border-bottom:none;}
.data-table tbody tr:hover td{background:var(--bg3);}
.data-table .add-row td{background:var(--bg);}
.data-table .add-row input{background:var(--bg3);border:1px solid var(--border);color:var(--fg);padding:7px 10px;border-radius:var(--radius-sm);font-size:13px;width:100%;outline:none;}
.data-table .add-row input:focus{border-color:var(--accent);}
.perm-table{width:100%;border-collapse:collapse;font-size:13px;}
.perm-table th,.perm-table td{padding:9px 12px;border:1px solid var(--border);text-align:center;}
.perm-table th{background:var(--bg3);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--fg3);}
.perm-table td:first-child{text-align:left;font-weight:500;}
.perm-table input[type=checkbox]{width:16px;height:16px;accent-color:var(--accent);cursor:pointer;}
.role-badge{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;}
.role-admin{background:var(--accent-dim);color:var(--accent);}
.role-user{background:var(--bg3);color:var(--fg3);}

/* ── MONITOR BOX ── */
.monitor-box{background:#0a0f1e;border:1px solid #1e3a5f;border-radius:var(--radius);padding:16px 20px;margin-bottom:20px;font-family:monospace;}
.monitor-box h3{font-size:13px;font-weight:600;color:#60a5fa;margin-bottom:12px;display:flex;align-items:center;gap:6px;}
.monitor-row{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;font-size:12px;}
.monitor-row .lbl{color:#475569;}
.monitor-row .val{color:#e2e8f0;}
.monitor-bar{height:3px;background:#1e2d3d;width:100%;margin-top:10px;border-radius:2px;overflow:hidden;}
.monitor-bar-inner{height:100%;background:linear-gradient(90deg,#3b82f6,#6366f1);width:100%;animation:scan 1.5s ease-in-out infinite;}
@keyframes scan{0%{opacity:.3;transform:scaleX(.3);}50%{opacity:1;transform:scaleX(1);}100%{opacity:.3;transform:scaleX(.3);}}

/* ── MODAL ── */
.modal{display:none;position:fixed;inset:0;z-index:999;background:rgba(0,0,0,.7);backdrop-filter:blur(4px);}
.modal-content{background:var(--bg2);border:1px solid var(--border);margin:6% auto;padding:24px;width:500px;max-width:90%;border-radius:14px;box-shadow:var(--shadow);}
.modal-content h3{font-size:15px;font-weight:600;margin-bottom:14px;}
.modal-path{font-family:monospace;background:var(--bg);border:1px solid var(--border);padding:8px 10px;border-radius:var(--radius-sm);font-size:12px;color:var(--accent);margin-bottom:10px;}
.file-list{list-style:none;max-height:280px;overflow-y:auto;border:1px solid var(--border);border-radius:var(--radius-sm);}
.file-list li{padding:8px 12px;border-bottom:1px solid var(--border);cursor:pointer;font-size:13px;transition:background .1s;}
.file-list li:last-child{border-bottom:none;}
.file-list li:hover{background:var(--accent-dim);color:var(--accent);}
.modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:14px;}

/* ── LIGHT THEME ── */
[data-theme="light"]{
  --bg:#ffffff;--bg2:#f8fafc;--bg3:#f1f5f9;--border:#e2e8f0;
  --fg:#0f172a;--fg2:#334155;--fg3:#64748b;
  --accent:#6366f1;--accent-hover:#4f46e5;--accent-dim:rgba(99,102,241,.12);
  --danger:#dc2626;--danger-hover:#b91c1c;--danger-dim:rgba(220,38,38,.1);
  --success:#16a34a;--success-hover:#15803d;--success-dim:rgba(22,163,74,.1);
  --shadow:0 4px 24px rgba(0,0,0,.08);
}
[data-theme="light"] .monitor-box{background:#eef2ff;border-color:#c7d2fe;}
[data-theme="light"] .monitor-box h3{color:#4338ca;}
[data-theme="light"] .monitor-row .lbl{color:#6b7280;}
[data-theme="light"] .monitor-row .val{color:#111827;}
[data-theme="light"] .monitor-bar{background:#e0e7ff;}
[data-theme="light"] .monitor-bar-inner{background:linear-gradient(90deg,#6366f1,#818cf8);}
[data-theme="light"] #viewer{background:rgba(0,0,0,.92);}
[data-theme="light"] .auth-page{background-image:radial-gradient(ellipse at 50% 0,rgba(99,102,241,.06) 0,transparent 60%);}
/* ── THEME SWITCHER ── */
.theme-switch{display:flex;align-items:center;gap:2px;background:var(--bg3);border:1px solid var(--border);border-radius:20px;padding:3px 6px;}
.theme-switch button{background:none;border:none;cursor:pointer;padding:2px 7px;border-radius:14px;font-size:13px;line-height:1.5;color:var(--fg3);transition:all .15s;}
.theme-switch button:hover{color:var(--fg);background:rgba(148,163,184,.15);}
.theme-switch button.active{background:var(--accent-dim);color:var(--accent);}
"""

HTML_LOGIN = """<!doctype html><html lang="{{ t.lang_code }}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ t.login_title }} – USBHDD</title><script>(function(){var t=localStorage.getItem('usbhdd-theme')||'system';if(t==='light'||(t==='system'&&window.matchMedia&&window.matchMedia('(prefers-color-scheme:light)').matches))document.documentElement.setAttribute('data-theme','light');}());</script><style>""" + CSS_CODE + """</style></head><body class="auth-page">{% with messages=get_flashed_messages(with_categories=true) %}{% if messages %}<div style="position:fixed;top:16px;left:50%;transform:translateX(-50%);z-index:999;width:360px;">{% for c, m in messages %}<div class="alert-box alert-{{ c }}" style="display:flex;margin-bottom:6px;">{{ m }}<button class="close-btn" onclick="this.parentElement.remove()">&times;</button></div>{% endfor %}</div>{% endif %}{% endwith %}<div class="auth-card"><div class="auth-logo"><div class="auth-logo-icon">💾</div><div class="auth-logo-text">USBHDD</div></div><h1 class="auth-title">{{ t.login_heading }}</h1><p class="auth-sub">Secure Storage System</p><form method="post"><div class="form-group"><label class="form-label">{{ t.username_placeholder }}</label><input class="form-input" type="text" name="username" required autofocus><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"></div><div class="form-group"><label class="form-label">{{ t.password_placeholder }}</label><input class="form-input" type="password" name="password" required></div><button class="auth-btn" type="submit">{{ t.login_btn }}</button></form><div class="auth-footer"><div style="display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:wrap;margin-top:16px;"><div class="lang-switch"><a href="/lang/en" class="{{ 'active' if t.lang_code=='en' else '' }}">EN</a><span>|</span><a href="/lang/tr" class="{{ 'active' if t.lang_code=='tr' else '' }}">TR</a></div><div class="theme-switch"><button id="th-light" onclick="setTheme('light')" title="{{ t.theme_light }}">☀</button><button id="th-system" onclick="setTheme('system')" title="{{ t.theme_auto }}">⊙</button><button id="th-dark" onclick="setTheme('dark')" title="{{ t.theme_dark }}">☽</button></div></div></div></div><script>function setTheme(m){localStorage.setItem('usbhdd-theme',m);if(m==='light'){document.documentElement.setAttribute('data-theme','light');}else if(m==='dark'){document.documentElement.removeAttribute('data-theme');}else{var mq=window.matchMedia&&window.matchMedia('(prefers-color-scheme:light)');if(mq&&mq.matches)document.documentElement.setAttribute('data-theme','light');else document.documentElement.removeAttribute('data-theme');}document.querySelectorAll('.theme-switch button').forEach(function(b){b.classList.remove('active');});var b=document.getElementById('th-'+m);if(b)b.classList.add('active');}(function(){var t=localStorage.getItem('usbhdd-theme')||'system';var b=document.getElementById('th-'+t);if(b)b.classList.add('active');})();</script></body></html>"""

HTML_SETUP = """<!doctype html><html lang="{{ t.lang_code }}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ t.setup_title }} – USBHDD</title><script>(function(){var t=localStorage.getItem('usbhdd-theme')||'system';if(t==='light'||(t==='system'&&window.matchMedia&&window.matchMedia('(prefers-color-scheme:light)').matches))document.documentElement.setAttribute('data-theme','light');}());</script><style>""" + CSS_CODE + """.auth-card{width:460px;max-width:95vw;max-height:92vh;overflow-y:auto;}</style></head><body class="auth-page">{% with messages=get_flashed_messages(with_categories=true) %}{% if messages %}<div style="position:fixed;top:16px;left:50%;transform:translateX(-50%);z-index:999;width:420px;">{% for c, m in messages %}<div class="alert-box alert-{{ c }}" style="display:flex;margin-bottom:6px;">{{ m }}<button class="close-btn" onclick="this.parentElement.remove()">&times;</button></div>{% endfor %}</div>{% endif %}{% endwith %}<div class="auth-card"><div class="auth-logo"><div class="auth-logo-icon">🛠️</div><div class="auth-logo-text">USBHDD</div></div><h1 class="auth-title">{{ t.setup_heading }}</h1><div class="setup-notice">{{ t.setup_notice }}</div><form method="post"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><div class="form-group"><label class="form-label">{{ t.username_placeholder }}</label><input class="form-input" type="text" name="username" required></div><div class="form-group"><label class="form-label">{{ t.password_placeholder }}</label><input class="form-input" type="password" name="password" required></div><div class="setup-section"><div class="setup-section-title">{{ t.share_name_label }}</div><div class="form-group"><label class="form-label">{{ t.share_name_label }}</label><input class="form-input" type="text" name="share_name" required></div><div class="form-group"><label class="form-label">{{ t.path_label }}</label><div class="input-with-btn"><input class="form-input" type="text" id="sharePathInput" name="share_path" required><button type="button" onclick="openFolderModal()" class="btn btn-ghost">{{ t.select_folder_btn }}</button></div></div></div><button class="auth-btn" type="submit" style="margin-top:10px;">{{ t.complete_btn }}</button></form><div class="auth-footer"><div style="display:flex;align-items:center;justify-content:center;gap:10px;margin-top:16px;"><div class="lang-switch"><a href="/lang/en" class="{{ 'active' if t.lang_code=='en' else '' }}">EN</a><span>|</span><a href="/lang/tr" class="{{ 'active' if t.lang_code=='tr' else '' }}">TR</a></div><div class="theme-switch"><button id="th-light" onclick="setTheme('light')" title="{{ t.theme_light }}">☀</button><button id="th-system" onclick="setTheme('system')" title="{{ t.theme_auto }}">⊙</button><button id="th-dark" onclick="setTheme('dark')" title="{{ t.theme_dark }}">☽</button></div></div></div></div><div id="folderModal" class="modal"><div class="modal-content"><h3>{{ t.select_folder_title }}</h3><div class="modal-path" id="currentPathDisplay">/</div><ul id="dirList" class="file-list"></ul><div class="modal-actions"><button onclick="selectCurrentFolder()" class="btn btn-success">{{ t.select_btn }}</button><button onclick="closeModal()" class="btn btn-ghost">{{ t.cancel_btn }}</button></div></div></div><script>let currentBrowsePath="/";function openFolderModal(){document.getElementById('folderModal').style.display='block';loadDirs(currentBrowsePath);}function closeModal(){document.getElementById('folderModal').style.display='none';}function loadDirs(path){const fd=new FormData();fd.append('path',path);fd.append('csrf_token',document.querySelector('input[name="csrf_token"]').value);document.getElementById('currentPathDisplay').innerText="{{ t.loading }}";fetch('/admin/list_dirs',{method:'POST',body:fd}).then(r=>r.json()).then(data=>{if(data.error){alert(data.error);return;}currentBrowsePath=data.current;document.getElementById('currentPathDisplay').innerText=currentBrowsePath;const list=document.getElementById('dirList');list.innerHTML="";data.dirs.forEach(d=>{const li=document.createElement('li');li.textContent="📁 "+d.name;li.onclick=()=>loadDirs(d.path);list.appendChild(li);});});}function selectCurrentFolder(){document.getElementById('sharePathInput').value=currentBrowsePath;closeModal();}function setTheme(m){localStorage.setItem('usbhdd-theme',m);if(m==='light'){document.documentElement.setAttribute('data-theme','light');}else if(m==='dark'){document.documentElement.removeAttribute('data-theme');}else{var mq=window.matchMedia&&window.matchMedia('(prefers-color-scheme:light)');if(mq&&mq.matches)document.documentElement.setAttribute('data-theme','light');else document.documentElement.removeAttribute('data-theme');}document.querySelectorAll('.theme-switch button').forEach(function(b){b.classList.remove('active');});var b=document.getElementById('th-'+m);if(b)b.classList.add('active');}(function(){var t=localStorage.getItem('usbhdd-theme')||'system';var b=document.getElementById('th-'+t);if(b)b.classList.add('active');})();</script></body></html>"""

HTML_INDEX = """<!doctype html><html lang="{{ t.lang_code }}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ t.files_title }} – USBHDD</title><script>(function(){var t=localStorage.getItem('usbhdd-theme')||'system';if(t==='light'||(t==='system'&&window.matchMedia&&window.matchMedia('(prefers-color-scheme:light)').matches))document.documentElement.setAttribute('data-theme','light');}());</script><style>""" + CSS_CODE + """</style></head><body><nav class="navbar"><div class="navbar-brand"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="7" cy="12" r="1.5" fill="currentColor"/><line x1="12" y1="9" x2="19" y2="9"/><line x1="12" y1="12" x2="19" y2="12"/><line x1="12" y1="15" x2="19" y2="15"/></svg>USBHDD</div><div class="navbar-search"><form action="" method="get"><input type="text" name="q" placeholder="{{ t.search_placeholder }}" value="{{ q }}"></form></div><div class="navbar-actions">{% if is_admin %}<a href="/admin" class="btn btn-ghost" style="border-color:var(--accent);color:var(--accent);">⚙ Admin</a>{% endif %}<a href="?sort=name" class="btn btn-ghost">↑A-Z</a><a href="?sort=date" class="btn btn-ghost">📅</a><div class="lang-switch"><a href="/lang/en" class="{{ 'active' if t.lang_code=='en' else '' }}">EN</a><span>|</span><a href="/lang/tr" class="{{ 'active' if t.lang_code=='tr' else '' }}">TR</a></div><div class="theme-switch"><button id="th-light" onclick="setTheme('light')" title="{{ t.theme_light }}">☀</button><button id="th-system" onclick="setTheme('system')" title="{{ t.theme_auto }}">⊙</button><button id="th-dark" onclick="setTheme('dark')" title="{{ t.theme_dark }}">☽</button></div><a href="/logout" class="btn btn-danger">{{ t.logout_btn }}</a></div></nav><div id="js-alert" class="alert-box alert-error"><span id="js-alert-msg"></span><button class="close-btn" onclick="this.parentElement.style.display='none'">&times;</button></div>{% with messages=get_flashed_messages(with_categories=true) %}{% if messages %}{% for c, m in messages %}<div class="alert-box alert-{{ c }}" style="display:flex;">{{ m }}<button class="close-btn" onclick="this.parentElement.remove()">&times;</button></div>{% endfor %}{% endif %}{% endwith %}<div class="toolbar"><div class="breadcrumb"><a href="/">🏠</a>{% for crumb in breadcrumbs %}<span class="sep">/</span><a href="/{{ crumb.path }}">{{ crumb.name }}</a>{% endfor %}</div><div class="toolbar-actions"><form action="/mkdir/{{ path }}" method="post" style="display:flex;gap:6px;"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><input type="text" name="foldername" placeholder="{{ t.folder_placeholder }}" required><button type="submit" class="btn btn-ghost">+ {{ t.folder_placeholder }}</button></form><form action="/upload/{{ path }}" method="post" enctype="multipart/form-data"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><label class="btn btn-primary" style="cursor:pointer;">⬆ Upload<input type="file" name="file" style="display:none" onchange="this.form.submit()"></label></form></div></div><div class="grid">{% if path %}{% set parts=path.split('/') %}<div class="card back-card" onclick="location.href='/{{ parts[:-1]|join('/') }}'"><span>⬅</span></div>{% endif %}{% for item in items %}<div class="card" onclick="{% if item.is_dir %}location.href='/{{ item.path }}'{% endif %}">{% if not item.is_drive %}<div class="card-actions"><a href="/delete/{{ item.path }}" onclick="event.stopPropagation();return confirm('{{ t.confirm_delete }}')" class="del-btn">✕</a></div>{% endif %}<a href="/{{ item.path }}" {% if not item.is_dir %}data-file{% endif %} onclick="event.stopPropagation()"><div class="thumb">{% if item.is_drive %}<span class="icon-dir">💾</span>{% elif item.is_dir %}<span class="icon-dir">📁</span>{% else %}{% set n=item.name.lower() %}{% if n.endswith(('.jpg','.jpeg','.png','.webp','.gif')) %}<img src="/thumb/{{ item.path }}" loading="lazy">{% elif n.endswith(('.mp4','.mov','.mkv','.avi')) %}<span class="icon-vid">🎬</span>{% elif n.endswith('.pdf') %}<span class="icon-pdf">📄</span>{% elif n.endswith(('.doc','.docx')) %}<span class="icon-doc">📝</span>{% elif n.endswith(('.xls','.xlsx','.csv')) %}<span class="icon-xls">📊</span>{% else %}<span class="icon-file">📎</span>{% endif %}{% endif %}</div></a><div class="card-info"><span class="card-name">{{ item.name }}</span><span class="card-meta">{{ item.human_size if not item.is_dir else '' }}</span></div></div>{% endfor %}</div><div id="viewer"><button id="vclose-btn" onclick="closeViewer()">✕</button><button id="prev-btn" class="viewer-btn">‹</button><div id="viewer-content"><img id="viewer-img" style="display:none;"><video id="viewer-video" controls autoplay style="display:none;"></video></div><button id="next-btn" class="viewer-btn">›</button></div><script>let currentIndex=0,mediaList=[];document.addEventListener("DOMContentLoaded",()=>{const links=document.querySelectorAll('a[data-file]'),exts=['.jpg','.jpeg','.png','.gif','.webp','.mp4','.mov','.mkv','.avi'];links.forEach(l=>{const h=l.getAttribute('href');if(exts.some(e=>h.toLowerCase().endsWith(e))){l.addEventListener('click',ev=>{ev.preventDefault();openViewer(h);});mediaList.push(h);}});});function openViewer(src){currentIndex=mediaList.indexOf(src);updateViewer();document.getElementById('viewer').style.display='flex';}function closeViewer(){document.getElementById('viewer').style.display='none';document.getElementById('viewer-video').pause();}function updateViewer(){if(currentIndex<0)currentIndex=mediaList.length-1;if(currentIndex>=mediaList.length)currentIndex=0;const src=mediaList[currentIndex],isVid=src.match(/\\.(mp4|mov|mkv|avi)$/i),img=document.getElementById('viewer-img'),vid=document.getElementById('viewer-video');if(isVid){img.style.display='none';vid.style.display='block';vid.src=src;}else{vid.style.display='none';vid.pause();img.style.display='block';img.src=src;}}document.getElementById('prev-btn').addEventListener('click',e=>{e.stopPropagation();currentIndex--;updateViewer();});document.getElementById('next-btn').addEventListener('click',e=>{e.stopPropagation();currentIndex++;updateViewer();});document.addEventListener('keydown',e=>{if(document.getElementById('viewer').style.display==='flex'){if(e.key==='ArrowLeft'){currentIndex--;updateViewer();}if(e.key==='ArrowRight'){currentIndex++;updateViewer();}if(e.key==='Escape')closeViewer();}});function setTheme(m){localStorage.setItem('usbhdd-theme',m);if(m==='light'){document.documentElement.setAttribute('data-theme','light');}else if(m==='dark'){document.documentElement.removeAttribute('data-theme');}else{var mq=window.matchMedia&&window.matchMedia('(prefers-color-scheme:light)');if(mq&&mq.matches)document.documentElement.setAttribute('data-theme','light');else document.documentElement.removeAttribute('data-theme');}document.querySelectorAll('.theme-switch button').forEach(function(b){b.classList.remove('active');});var b=document.getElementById('th-'+m);if(b)b.classList.add('active');}(function(){var t=localStorage.getItem('usbhdd-theme')||'system';var b=document.getElementById('th-'+t);if(b)b.classList.add('active');})();</script></body></html>"""

HTML_ADMIN = """<!doctype html><html lang="{{ t.lang_code }}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ t.admin_title }} – USBHDD</title><script>(function(){var t=localStorage.getItem('usbhdd-theme')||'system';if(t==='light'||(t==='system'&&window.matchMedia&&window.matchMedia('(prefers-color-scheme:light)').matches))document.documentElement.setAttribute('data-theme','light');}());</script><style>""" + CSS_CODE + """</style></head><body><nav class="navbar"><div class="navbar-brand"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="7" cy="12" r="1.5" fill="currentColor"/><line x1="12" y1="9" x2="19" y2="9"/><line x1="12" y1="12" x2="19" y2="12"/><line x1="12" y1="15" x2="19" y2="15"/></svg>USBHDD <span style="color:var(--accent);font-size:12px;font-weight:700;letter-spacing:.5px;">ADMIN</span></div><div class="navbar-actions"><a href="/" class="btn btn-ghost">{{ t.back_btn }}</a><div class="lang-switch"><a href="/lang/en" class="{{ 'active' if t.lang_code=='en' else '' }}">EN</a><span>|</span><a href="/lang/tr" class="{{ 'active' if t.lang_code=='tr' else '' }}">TR</a></div><div class="theme-switch"><button id="th-light" onclick="setTheme('light')" title="{{ t.theme_light }}">☀</button><button id="th-system" onclick="setTheme('system')" title="{{ t.theme_auto }}">⊙</button><button id="th-dark" onclick="setTheme('dark')" title="{{ t.theme_dark }}">☽</button></div><a href="/logout" class="btn btn-danger">{{ t.logout_btn }}</a></div></nav><div class="admin-wrap">{% with messages=get_flashed_messages(with_categories=true) %}{% if messages %}{% for c,m in messages %}<div class="alert-box alert-{{ c }}" style="display:flex;margin-bottom:12px;">{{ m }}<button class="close-btn" onclick="this.parentElement.remove()">&times;</button></div>{% endfor %}{% endif %}{% endwith %}<div class="monitor-box"><h3>📡 {{ t.monitor_title }}</h3><div class="monitor-row"><span class="lbl">{{ t.monitor_status }}</span><span class="val" id="idx-status">{{ t.loading }}</span></div><div class="monitor-row"><span class="lbl">{{ t.monitor_processing }}</span><span class="val" id="idx-path" style="font-size:11px;max-width:60%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">...</span></div><div class="monitor-row"><span class="lbl">{{ t.monitor_total }}</span><span class="val" id="idx-count">0 files</span></div><div class="monitor-bar" id="idx-bar" style="display:none;"><div class="monitor-bar-inner"></div></div></div><div class="section-card"><div class="section-head"><h2>👤 {{ t.users_heading }}</h2></div><table class="data-table"><thead><tr><th>{{ t.user_col }}</th><th>{{ t.role_col }}</th><th style="width:80px;"></th></tr></thead><tbody>{% for u in users %}<tr><td style="font-weight:500;">{{ u['username'] }}</td><td><span class="role-badge role-{{ u['role'] }}">{{ u['role'] }}</span></td><td>{% if u['role']!='admin' %}<a href="/admin/delete_user/{{ u['id'] }}" onclick="return confirm('{{ t.confirm_delete }}')" class="btn btn-danger" style="padding:4px 10px;font-size:12px;">{{ t.delete_btn }}</a>{% endif %}</td></tr>{% endfor %}<tr class="add-row"><form action="/admin/add_user" method="post"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><td><input type="text" name="username" placeholder="{{ t.user_col }}" required></td><td><input type="password" name="password" placeholder="{{ t.password_placeholder }}" required></td><td><button type="submit" class="btn btn-success" style="padding:4px 10px;font-size:12px;">+ {{ t.add_btn }}</button></td></form></tr></tbody></table></div><div class="section-card"><div class="section-head"><h2>📁 {{ t.shares_heading }}</h2></div><table class="data-table"><thead><tr><th>{{ t.name_col }}</th><th>{{ t.path_col }}</th><th style="width:80px;"></th></tr></thead><tbody>{% for s in shares %}<tr><td style="font-weight:500;">{{ s['name'] }}</td><td style="font-family:monospace;font-size:12px;color:var(--fg3);">{{ s['path'] }}</td><td><a href="/admin/delete_share/{{ s['id'] }}" onclick="return confirm('{{ t.confirm_delete }}')" class="btn btn-danger" style="padding:4px 10px;font-size:12px;">{{ t.delete_btn }}</a></td></tr>{% endfor %}<tr class="add-row"><form action="/admin/add_share" method="post"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><td><input type="text" name="name" placeholder="{{ t.name_col }}" required></td><td><div style="display:flex;gap:6px;"><input type="text" id="sharePathInput" name="path" required><button type="button" onclick="openFolderModal()" class="btn btn-ghost" style="padding:5px 10px;font-size:12px;flex-shrink:0;">{{ t.select_folder_btn }}</button></div></td><td><button type="submit" class="btn btn-primary" style="padding:4px 10px;font-size:12px;">+ {{ t.add_btn }}</button></td></form></tr></tbody></table></div>{% if users and shares %}<div class="section-card"><div class="section-head"><h2>🔒 {{ t.permissions_heading }}</h2></div><div style="padding:16px;overflow-x:auto;"><table class="perm-table"><thead><tr><th>{{ t.user_folder_col }}</th>{% for s in shares %}<th>{{ s['name'] }}</th>{% endfor %}</tr></thead><tbody>{% for u in users %}{% if u['role']!='admin' %}<tr><td>{{ u['username'] }}</td>{% for s in shares %}<td><input type="checkbox" onchange="togglePerm({{ u['id'] }},{{ s['id'] }},this)" {% if u['id'] in permissions and s['id'] in permissions[u['id']] %}checked{% endif %}></td>{% endfor %}</tr>{% endif %}{% endfor %}</tbody></table></div></div>{% endif %}</div><div id="folderModal" class="modal"><div class="modal-content"><h3>{{ t.select_folder_title }}</h3><div class="modal-path" id="currentPathDisplay">/</div><ul id="dirList" class="file-list"></ul><div class="modal-actions"><button onclick="selectCurrentFolder()" class="btn btn-success">{{ t.select_btn }}</button><button onclick="closeModal()" class="btn btn-ghost">{{ t.cancel_btn }}</button></div></div></div><script>function togglePerm(uid,sid,cb){const fd=new FormData();fd.append('user_id',uid);fd.append('share_id',sid);fd.append('action',cb.checked?'add':'remove');fd.append('csrf_token','{{ csrf_token() }}');fetch('/admin/toggle_perm',{method:'POST',body:fd});}let currentBrowsePath="/";function openFolderModal(){document.getElementById('folderModal').style.display='block';loadDirs(currentBrowsePath);}function closeModal(){document.getElementById('folderModal').style.display='none';}function loadDirs(path){const fd=new FormData();fd.append('path',path);fd.append('csrf_token','{{ csrf_token() }}');document.getElementById('currentPathDisplay').innerText="{{ t.loading }}";fetch('/admin/list_dirs',{method:'POST',body:fd}).then(r=>r.json()).then(data=>{if(data.error){alert(data.error);return;}currentBrowsePath=data.current;document.getElementById('currentPathDisplay').innerText=currentBrowsePath;const list=document.getElementById('dirList');list.innerHTML="";data.dirs.forEach(d=>{const li=document.createElement('li');li.textContent="📁 "+d.name;li.onclick=()=>loadDirs(d.path);list.appendChild(li);});});}function selectCurrentFolder(){document.getElementById('sharePathInput').value=currentBrowsePath;closeModal();}function updateMonitor(){fetch('/admin/indexing_status').then(r=>r.json()).then(data=>{document.getElementById('idx-status').innerText=data.status;document.getElementById('idx-path').innerText=data.current_path;document.getElementById('idx-count').innerText=data.total_files+" files";if(data.status.includes('Scanning')){document.getElementById('idx-bar').style.display='block';}else{document.getElementById('idx-bar').style.display='none';}});}setInterval(updateMonitor,2000);function setTheme(m){localStorage.setItem('usbhdd-theme',m);if(m==='light'){document.documentElement.setAttribute('data-theme','light');}else if(m==='dark'){document.documentElement.removeAttribute('data-theme');}else{var mq=window.matchMedia&&window.matchMedia('(prefers-color-scheme:light)');if(mq&&mq.matches)document.documentElement.setAttribute('data-theme','light');else document.documentElement.removeAttribute('data-theme');}document.querySelectorAll('.theme-switch button').forEach(function(b){b.classList.remove('active');});var b=document.getElementById('th-'+m);if(b)b.classList.add('active');}(function(){var t=localStorage.getItem('usbhdd-theme')||'system';var b=document.getElementById('th-'+t);if(b)b.classList.add('active');})();</script></body></html>"""

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
    conn = None
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
        INDEX_STATUS["status"] = "✅ Ready"
        INDEX_STATUS["current_path"] = f"Last scan: {datetime.now().strftime('%H:%M')}"
    except Exception as e:
        INDEX_STATUS["status"] = f"❌ Error: {str(e)}"
    finally:
        if conn: conn.close()

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

# NOT: Thread init_db()'den sonra başlatılıyor (aşağıda)

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

# init_db her zaman çalışır (hem doğrudan hem gunicorn)
init_db()
check_and_create_certs()
# Thread init_db'den SONRA başlatılıyor (race condition önlenir)
threading.Thread(target=background_scanner_loop, daemon=True).start()

if __name__ == "__main__":
    port = find_available_port(8143)
    print(f"--- SUNUCU BAŞLATILIYOR: https://localhost:{port} ---")
    app.run(host='0.0.0.0', port=port, ssl_context=(CERT_FILE, KEY_FILE))
