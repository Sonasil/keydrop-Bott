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
ID_KEYS = ("id", "giveawayId", "uuid", "slug", "code", "_id", "hash")
TIER_KEYS = ("frequency", "category", "type", "tier", "name", "level", "rank", "kind", "group")
ALL_TIERS = ["amateur", "contender", "challenger", "champion"]

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

        seen = set()
        baseline_done = False
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

            found = {}
            for _u, data in list(payloads):
                find_giveaways(data, found, watch_tiers)
            for frame in list(ws_frames):
                find_giveaways(frame, found, watch_tiers)

            if debug:
                try:
                    with open("debug_payloads.json", "w", encoding="utf-8") as f:
                        json.dump({"http": payloads, "ws": ws_frames}, f,
                                  ensure_ascii=False, indent=2, default=str)
                except Exception:
                    pass

            new_ids = [g for g in found if g not in seen]

            if not baseline_done:
                seen.update(found.keys())
                baseline_done = True
                q_log(f"Baslangic: {len(found)} kayit bulundu (mevcutlar 'gorulmus' sayildi).")
                if not found:
                    q_log("UYARI: Hic kayit yakalanamadi. DEBUG'i acip "
                          "debug_payloads.json'i paylas.")
            else:
                for gid in new_ids:
                    info = found[gid]
                    q_alert(f"YENI {info['tier'].upper()} CEKILIS!  id={gid}  |  "
                            f"{summarize(info['data'])}")
                    if sound:
                        alert_sound()
                    seen.add(gid)
                if not new_ids:
                    q_log(f"Yeni yok. (Takipteki: {len(seen)})")

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
        self.debug_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(cfg, text="DEBUG (debug_payloads.json yaz)",
                        variable=self.debug_var).grid(row=1, column=2, columnspan=3, sticky="w")

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
