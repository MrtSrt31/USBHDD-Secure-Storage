import backend
import os
import sys
import socket
from gunicorn.app.base import BaseApplication

# --- KAYNAK YOLU ---
def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- PORT BULUCU ---
def find_free_port(start_port):
    port = start_port
    while port < start_port + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('0.0.0.0', port)) != 0: return port
            port += 1
    return None

# --- GELİŞMİŞ IP TARAYICI (Ethernet + Wi-Fi) ---
def get_all_local_ips():
    ip_list = []
    try:
        # Yöntem 1: Hostname üzerinden tüm arayüzleri çek
        host_name = socket.gethostname()
        # Makineye ait tüm IP'leri (Aliaslar dahil) al
        ips = socket.gethostbyname_ex(host_name)[2]
        for ip in ips:
            if not ip.startswith("127."):  # Localhost'u listeye ekleme, onu zaten biliyoruz
                ip_list.append(ip)
    except: pass

    try:
        # Yöntem 2: Dışarıya "ping" atar gibi yapıp ana çıkış kapısını bul (Garantidir)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        main_ip = s.getsockname()[0]
        s.close()
        if main_ip not in ip_list and not main_ip.startswith("127."):
            ip_list.append(main_ip)
    except: pass

    # Benzersizleri döndür
    return list(set(ip_list))

class StandaloneApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()
    def load_config(self):
        for key, value in self.options.items(): self.cfg.set(key.lower(), value)
    def load(self): return self.application

if __name__ == "__main__":
    # --- SERTİFİKA KONTROLÜ (Doğru Yerde Mi?) ---
    cert_path = os.path.join(backend.APP_ROOT, "cert.pem")
    key_path = os.path.join(backend.APP_ROOT, "key.pem")

    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print("⚠️ Sertifika oluşturuluyor...")
        os.system(f'openssl req -x509 -newkey rsa:4096 -nodes -out "{cert_path}" -keyout "{key_path}" -days 365 -subj "/C=TR/ST=Turkey/L=Istanbul/O=USBHDD/OU=IT/CN=localhost" > /dev/null 2>&1')

    # --- PORT VE IP HAZIRLIĞI ---
    target_port = find_free_port(8143)
    if target_port is None: sys.exit(1)
    
    # Tüm IP'leri bul
    available_ips = get_all_local_ips()

    options = {
        'bind': f'0.0.0.0:{target_port}', # TÜM AĞLARA YAYIN YAP (ÖNEMLİ)
        'workers': 1,
        'certfile': cert_path,
        'keyfile': key_path,
        'timeout': 120,
        'loglevel': 'warning'
    }
    
    # --- EKRAN ÇIKTISI (KULLANICI DOSTU) ---
    print("\n" + "="*60)
    print(f"🚀 USBHDD SUNUCUSU BAŞLADI (Port: {target_port})")
    print("-" * 60)
    print(f"💻 SADECE BEN (Bu cihaz):")
    print(f"   👉 https://127.0.0.1:{target_port}")
    print("-" * 60)
    
    if available_ips:
        print(f"🌍 DİĞER CİHAZLAR İÇİN (Aynı Ağdakiler):")
        for i, ip in enumerate(available_ips, 1):
            print(f"   👉 Adres {i}: https://{ip}:{target_port}")
            if ip.startswith("192.168."): print("      (Ev/Ofis Ağı için genelde bu kullanılır)")
            if ip.startswith("10."): print("      (Kurumsal Ağ/VPN olabilir)")
            if ip.startswith("172."): print("      (Hotspot veya Özel Ağ olabilir)")
    else:
        print("⚠️ Ağ bağlantısı bulunamadı veya IP alınamadı.")
        
    print("="*60 + "\n")
    
    StandaloneApplication(backend.app, options).run()
