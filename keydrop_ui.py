"""
Key-Drop cekilis izleyici - BASIT ARAYUZ (UI).

Terminal yerine bu pencereden kontrol edersin:
  - Baslat / Durdur dugmeleri
  - "Giris yaptim -> Izlemeyi baslat" dugmesi
  - Canli log ekrani
  - Kontrol araligi ve izlenecek seviye secimi

Yeni bir secili-seviye cekilisi acilinca: SES calar + log'a kirmizi satir duser.
Senin yerine Join'e BASMAZ.

Calistirma:  python keydrop_ui.py
(Once: pip install -r requirements.txt  ve  python -m playwright install chromium)
"""

import asyncio
import json
import queue
import threading
from datetime import datetime

import tkinter as tk
from tkinter import ttk, scrolledtext

from playwright.async_api import async_playwright

# --------------------------- SABITLER ------------------------------

USER_DATA_DIR = "./keydrop_profile"
GIVEAWAYS_URL = "https://keydrop.com/tr/giveaways/list"
# Bir cekilisin detay (katilma) sayfasi. {org} = organizator, {id} = cekilis id.
# Key-Drop'un kendi cekilisleri (amateur/contender/...) icin organizator 'keydrop'.
DETAIL_URL = "https://keydrop.com/tr/giveaways/{org}/{id}"
ID_KEYS = ("id", "giveawayId", "uuid", "slug", "code", "_id", "hash")
TIER_KEYS = ("frequency", "category", "type", "tier", "name", "level", "rank", "kind", "group")
ALL_TIERS = ["amateur", "contender", "challenger", "champion"]
# Bu durumlardaki cekilise artik katilamazsin (bitmis/iptal).
FINISHED_STATUSES = {"ended", "finished", "cancelled", "canceled", "closed", "drawn"}

# UI <-> worker iletisim kanallari
ui_queue = queue.Queue()
stop_event = threading.Event()
proceed_event = threading.Event()
worker_thread = None

# --------------------------- SES -----------------------------------

try:
    import winsound

    def alert_sound():
        for _ in range(3):
            winsound.Beep(1100, 220)
            winsound.Beep(1500, 220)
except Exception:
    def alert_sound():
        import sys
        for _ in range(3):
            sys.stdout.write("\a")
            sys.stdout.flush()


# ----------------- SEMADAN BAGIMSIZ CEKILIS BULUCU -----------------

def find_giveaways(node, found, watch_tiers):
    if isinstance(node, dict):
        matched = None
        for k, v in node.items():
            if isinstance(v, str) and v.strip().lower() in watch_tiers:
                if k.lower() in TIER_KEYS:
                    matched = v.strip().lower()
        if matched:
            gid = None
            for idk in ID_KEYS:
                if idk in node and isinstance(node[idk], (str, int)):
                    gid = str(node[idk])
                    break
            if gid is None:
                gid = str(abs(hash(json.dumps(node, sort_keys=True, default=str))))
            found[gid] = {"tier": matched, "data": node}
        for v in node.values():
            find_giveaways(v, found, watch_tiers)
    elif isinstance(node, list):
        for item in node:
            find_giveaways(item, found, watch_tiers)
    return found


def _fmt_deadline(ms):
    try:
        secs = int(ms) / 1000 - datetime.now().timestamp()
        if secs <= 0:
            return "suresi doldu"
        m, s = divmod(int(secs), 60)
        h, m = divmod(m, 60)
        return f"{h}sa {m}dk" if h else f"{m}dk {s}sn"
    except Exception:
        return str(ms)


def summarize(data):
    bits = []
    if "frequency" in data:
        bits.append(f"seviye={data['frequency']}")
    if "status" in data:
        bits.append(f"durum={data['status']}")
    if "participantCount" in data:
        mx = data.get("maxUsers", "?")
        bits.append(f"katilimci={data['participantCount']}/{mx}")
    if "deadlineTimestamp" in data:
        bits.append(f"kalan={_fmt_deadline(data['deadlineTimestamp'])}")
    if "depositAmountRequired" in data and data["depositAmountRequired"]:
        bits.append(f"depozito={data['depositAmountRequired']}{data.get('depositAmountCurrency','')}")
    if "haveIJoined" in data:
        bits.append(f"katildim={data['haveIJoined']}")
    # bilinen alan yoksa eski genel yontem
    if not bits:
        for k in ("id", "slug", "code", "name", "title", "prize"):
            if k in data and not isinstance(data[k], (dict, list)):
                bits.append(f"{k}={data[k]}")
    return ", ".join(bits) if bits else "(detay icin debug_payloads.json)"


def collect_giveaways(payloads, ws_frames, watch_tiers):
    """Yakalanan API yanitlarindan izlenen seviyedeki cekilisleri toplar.

    Once yapisi bilinen /giveaway/list yanitini okur (body['data'] listesi);
    her kaydin 'frequency' (seviye), 'status', 'haveIJoined' alanlari burada gelir.
    Hicbir yapili veri bulunamazsa semadan bagimsiz taramaya (find_giveaways) duser.
    """
    found = {}

    def consider(node):
        if not isinstance(node, dict):
            return
        freq = node.get("frequency")
        if not isinstance(freq, str):
            return
        tier = freq.strip().lower()
        if tier not in watch_tiers:
            return
        gid = None
        for idk in ID_KEYS:
            val = node.get(idk)
            if isinstance(val, (str, int)):
                gid = str(val)
                break
        if gid is None:
            gid = str(abs(hash(json.dumps(node, sort_keys=True, default=str))))
        found[gid] = {"tier": tier, "data": node}

    structured = False
    for _url, body in payloads:
        if isinstance(body, dict) and isinstance(body.get("data"), list):
            structured = True
            for item in body["data"]:
                consider(item)

    # Yedek plan: API yapisi degismisse eski genel tarama
    if not found and not structured:
        for _url, body in payloads:
            find_giveaways(body, found, watch_tiers)
        for frame in ws_frames:
            find_giveaways(frame, found, watch_tiers)

    return found


def detail_url(data, gid):
    """Cekilisin detay/katilma sayfasinin adresi. Organizator alanindan turetilir,
    yoksa Key-Drop'un kendi cekilisi varsayilir ('keydrop')."""
    org = "keydrop"
    o = data.get("organizer")
    if isinstance(o, dict):
        for k in ("slug", "name", "code"):
            v = o.get(k)
            if isinstance(v, str) and v.strip():
                org = v.strip().lower()
                break
    elif isinstance(o, str) and o.strip():
        org = o.strip().lower()
    return DETAIL_URL.format(org=org, id=gid)


def is_joinable(data):
    """Bu cekilise SU AN katilabilir miyim? (aktif + henuz katilmamis + suresi dolmamis)"""
    status = str(data.get("status", "")).strip().lower()
    if status in FINISHED_STATUSES:
        return False
    if data.get("haveIJoined") is True:
        return False
    dl = data.get("deadlineTimestamp")
    if isinstance(dl, (int, float)) and dl > 0:
        if dl / 1000 <= datetime.now().timestamp():
            return False
    return True


def q_log(text):
    ui_queue.put(("log", text))


def q_alert(text):
    ui_queue.put(("alert", text))


def q_status(text):
    ui_queue.put(("status", text))


# --------------------------- WORKER (async) ------------------------

async def monitor(config):
    watch_tiers = config["tiers"]
    interval = config["interval"]
    debug = config["debug"]
    sound = config["sound"]
    open_page = config.get("open_page", True)

    payloads = []
    ws_frames = []

    async def handle_response(response):
        try:
            if "giveaway" in response.url.lower():
                if "json" in response.headers.get("content-type", "").lower():
                    payloads.append((response.url, await response.json()))
        except Exception:
            pass

    def handle_ws(ws):
        def on_frame(payload):
            try:
                ws_frames.append(json.loads(payload))
            except Exception:
                pass
        ws.on("framereceived", on_frame)

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        page.on("response", lambda r: asyncio.create_task(handle_response(r)))
        page.on("websocket", handle_ws)

        try:
            await page.goto(GIVEAWAYS_URL, wait_until="domcontentloaded")
        except Exception as e:
            q_log(f"Sayfa acilamadi: {e}")

        q_log("Tarayici acildi. Gerekirse Steam ile GIRIS YAP, listeyi gor.")
        ui_queue.put(("ready_for_login", None))
        q_status("Giris bekleniyor...")

        # Giris kapisi: kullanici 'Izlemeyi baslat' diyene kadar bekle
        while not proceed_event.is_set():
            if stop_event.is_set():
                await ctx.close()
                return
            await asyncio.sleep(0.3)

        # Kullanici 'Izlemeyi baslat' dedi: onu otomatik olarak cekilis
        # listesine geri goturuyoruz (giris sonrasi baska sayfada kalmis olabilir).
        q_log("Cekilis listesine yonlendiriliyor...")
        try:
            await page.goto(GIVEAWAYS_URL, wait_until="domcontentloaded")
        except Exception as e:
            q_log(f"Yonlendirme hatasi: {e}")

        notified = set()   # zaten "katilabilirsin" diye haber verdigimiz id'ler
        detail_page = None  # detay sayfasini gosterdigimiz ayri sekme
        q_status("Izleniyor")
        q_log(f"Izleme basladi. Seviyeler={sorted(watch_tiers)}, aralik={interval}s")

        while not stop_event.is_set():
            payloads.clear()
            ws_frames.clear()
            try:
                await page.goto(GIVEAWAYS_URL, wait_until="domcontentloaded")
            except Exception as e:
                q_log(f"Yenileme hatasi: {e}")
            await asyncio.sleep(4)

            found = collect_giveaways(list(payloads), list(ws_frames), watch_tiers)

            if debug:
                try:
                    with open("debug_payloads.json", "w", encoding="utf-8") as f:
                        json.dump({"http": payloads, "ws": ws_frames}, f,
                                  ensure_ascii=False, indent=2, default=str)
                except Exception:
                    pass

            if not found:
                q_log("UYARI: Hic kayit yakalanamadi. DEBUG'i acip "
                      "debug_payloads.json'i paylas.")
            else:
                joinable = {g: i for g, i in found.items() if is_joinable(i["data"])}
                joined = [g for g, i in found.items() if i["data"].get("haveIJoined") is True]
                new_joinable = [g for g in joinable if g not in notified]

                for gid in new_joinable:
                    info = joinable[gid]
                    q_alert(f"KATILABILIRSIN!  {info['tier'].upper()}  |  "
                            f"{summarize(info['data'])}")
                    if sound:
                        alert_sound()
                    notified.add(gid)

                # Yeni katilinabilir cekilis varsa, detay (katilma) sayfasini AYRI
                # sekmede ac. Izleme ana sekmede devam eder; katilma butonuna basmak
                # kullaniciya kalir. Katilmaz, sadece sayfayi onune getirir.
                if new_joinable and open_page:
                    gid = new_joinable[0]
                    url = detail_url(joinable[gid]["data"], gid)
                    try:
                        if detail_page is None or detail_page.is_closed():
                            detail_page = await ctx.new_page()
                        await detail_page.goto(url, wait_until="domcontentloaded")
                        await detail_page.bring_to_front()
                        q_log(f"Detay sayfasi acildi (katilmak senin elinde): {url}")
                    except Exception as e:
                        q_log(f"Detay sayfasi acilamadi: {e}")

                if not new_joinable:
                    q_log(f"Yeni katilinabilir cekilis yok. "
                          f"(Katilabilir: {len(joinable)}, katildiklarin: {len(joined)}, "
                          f"toplam izlenen: {len(found)})")

            # kesintiye uygun bekleme
            waited = 0.0
            while waited < interval and not stop_event.is_set():
                await asyncio.sleep(0.5)
                waited += 0.5

        await ctx.close()
        q_status("Durduruldu")


def worker_main(config):
    try:
        asyncio.run(monitor(config))
    except Exception as e:
        q_log(f"HATA: {e}")
    finally:
        ui_queue.put(("stopped", None))


# ------------------------------- UI --------------------------------

class App:
    def __init__(self, root):
        self.root = root
        root.title("Key-Drop Cekilis Izleyici")
        root.geometry("720x560")
        root.minsize(620, 480)

        pad = {"padx": 8, "pady": 6}

        # Ust: durum
        top = ttk.Frame(root)
        top.pack(fill="x", **pad)
        ttk.Label(top, text="Durum:").pack(side="left")
        self.status_var = tk.StringVar(value="Hazir")
        self.status_lbl = ttk.Label(top, textvariable=self.status_var,
                                    font=("Segoe UI", 10, "bold"))
        self.status_lbl.pack(side="left", padx=6)

        # Ayarlar
        cfg = ttk.LabelFrame(root, text="Ayarlar")
        cfg.pack(fill="x", **pad)

        ttk.Label(cfg, text="Kontrol araligi (sn):").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.interval_var = tk.IntVar(value=25)
        ttk.Spinbox(cfg, from_=10, to=300, increment=5, width=6,
                    textvariable=self.interval_var).grid(row=0, column=1, sticky="w")

        ttk.Label(cfg, text="Seviyeler:").grid(row=0, column=2, sticky="w", padx=12)
        self.tier_vars = {}
        col = 3
        for t in ALL_TIERS:
            v = tk.BooleanVar(value=(t == "amateur"))
            self.tier_vars[t] = v
            ttk.Checkbutton(cfg, text=t, variable=v).grid(row=0, column=col, sticky="w", padx=2)
            col += 1

        self.sound_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(cfg, text="Ses", variable=self.sound_var).grid(row=1, column=1, sticky="w", pady=4)
        self.openpage_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(cfg, text="Yeni cekiliste detay sayfasini ac",
                        variable=self.openpage_var).grid(row=1, column=2, columnspan=3, sticky="w")
        self.debug_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(cfg, text="DEBUG (debug_payloads.json yaz)",
                        variable=self.debug_var).grid(row=2, column=2, columnspan=3, sticky="w")

        # Dugmeler
        btns = ttk.Frame(root)
        btns.pack(fill="x", **pad)
        self.start_btn = ttk.Button(btns, text="Baslat", command=self.on_start)
        self.start_btn.pack(side="left")
        self.proceed_btn = ttk.Button(btns, text="Giris yaptim -> Izlemeyi baslat",
                                      command=self.on_proceed, state="disabled")
        self.proceed_btn.pack(side="left", padx=6)
        self.stop_btn = ttk.Button(btns, text="Durdur", command=self.on_stop, state="disabled")
        self.stop_btn.pack(side="left")
        ttk.Button(btns, text="Logu temizle", command=self.clear_log).pack(side="right")

        # Log
        logf = ttk.LabelFrame(root, text="Log")
        logf.pack(fill="both", expand=True, **pad)
        self.log = scrolledtext.ScrolledText(logf, height=15, wrap="word",
                                             font=("Consolas", 9), state="disabled")
        self.log.pack(fill="both", expand=True, padx=4, pady=4)
        self.log.tag_config("alert", foreground="#c00000",
                            font=("Consolas", 9, "bold"))
        self.log.tag_config("info", foreground="#222222")

        self.append("Hazir. 'Baslat' -> tarayici acilir -> Steam giris -> "
                    "'Izlemeyi baslat'.", "info")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(150, self.poll_queue)

    # --- log yardimcilari ---
    def append(self, text, tag="info"):
        line = f"[{datetime.now():%H:%M:%S}] {text}\n"
        self.log.configure(state="normal")
        self.log.insert("end", line, tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # --- dugme aksiyonlari ---
    def on_start(self):
        global worker_thread
        tiers = {t for t, v in self.tier_vars.items() if v.get()}
        if not tiers:
            self.append("En az bir seviye sec.", "alert")
            return
        stop_event.clear()
        proceed_event.clear()
        config = {
            "tiers": tiers,
            "interval": max(10, int(self.interval_var.get())),
            "sound": self.sound_var.get(),
            "debug": self.debug_var.get(),
            "open_page": self.openpage_var.get(),
        }
        worker_thread = threading.Thread(target=worker_main, args=(config,), daemon=True)
        worker_thread.start()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_var.set("Baslatiliyor...")
        self.append("Baslatiliyor, tarayici aciliyor...", "info")

    def on_proceed(self):
        proceed_event.set()
        self.proceed_btn.config(state="disabled")
        self.append("Izleme onaylandi.", "info")

    def on_stop(self):
        stop_event.set()
        self.stop_btn.config(state="disabled")
        self.status_var.set("Durduruluyor...")
        self.append("Durdurma istendi...", "info")

    def on_close(self):
        stop_event.set()
        self.root.after(300, self.root.destroy)

    # --- kuyruk dinleyici ---
    def poll_queue(self):
        try:
            while True:
                kind, payload = ui_queue.get_nowait()
                if kind == "log":
                    self.append(payload, "info")
                elif kind == "alert":
                    self.append(payload, "alert")
                elif kind == "status":
                    self.status_var.set(payload)
                elif kind == "ready_for_login":
                    self.proceed_btn.config(state="normal")
                elif kind == "stopped":
                    self.start_btn.config(state="normal")
                    self.stop_btn.config(state="disabled")
                    self.proceed_btn.config(state="disabled")
                    if not self.status_var.get().startswith("Durdur"):
                        self.status_var.set("Durdu")
        except queue.Empty:
            pass
        self.root.after(150, self.poll_queue)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
