# -*- coding: utf-8 -*-
"""
Key-Drop giveaway monitor - SIMPLE UI.

Control everything from this window instead of the terminal:
  - Start / Stop buttons
  - "I'm logged in -> Start monitoring" button
  - Live log screen
  - Check interval and watched tier selection
  - TR / EN language toggle (top-right). Default language: English.

When a joinable (active + not yet joined) giveaway is found, a red line appears
in the log, the detail page opens and it auto-joins FREE (deposit=0) giveaways.
It never auto-joins giveaways that require a deposit.

Run:  python keydrop_ui.py
(First: pip install -r requirements.txt  and  python -m playwright install chromium)
"""

import asyncio
import json
import queue
import threading
from datetime import datetime

import tkinter as tk
from tkinter import ttk, scrolledtext

from playwright.async_api import async_playwright

# --------------------------- CONSTANTS ------------------------------

USER_DATA_DIR = "./keydrop_profile"
GIVEAWAYS_URL = "https://keydrop.com/tr/giveaways/list"
# A giveaway's detail (join) page. {org} = organizer, {id} = giveaway id.
# For Key-Drop's own giveaways (amateur/contender/...) the organizer is 'keydrop'.
DETAIL_URL = "https://keydrop.com/tr/giveaways/{org}/{id}"
ID_KEYS = ("id", "giveawayId", "uuid", "slug", "code", "_id", "hash")
TIER_KEYS = ("frequency", "category", "type", "tier", "name", "level", "rank", "kind", "group")
ALL_TIERS = ["amateur", "contender", "challenger", "champion"]
# You can no longer join giveaways in these states (ended/cancelled).
FINISHED_STATUSES = {"ended", "finished", "cancelled", "canceled", "closed", "drawn"}
# Max seconds to wait for list data on each attempt.
LIST_LOAD_TIMEOUT = 10
# If the list doesn't load (internet etc.) retry this many times.
LIST_LOAD_RETRIES = 3

# UI <-> worker communication channels
ui_queue = queue.Queue()
stop_event = threading.Event()
proceed_event = threading.Event()
worker_thread = None

# --------------------------- I18N (TR / EN) ------------------------------

# Active language. Default English. Toggled from the UI (top-right button).
_LANG = {"v": "en"}

TXT = {
    # window / chrome
    "win_title":     {"en": "Key-Drop Giveaway Monitor", "tr": "Key-Drop Çekiliş İzleyici"},
    "status_label":  {"en": "Status:", "tr": "Durum:"},
    "lang_btn":      {"en": "Türkçe", "tr": "English"},  # button shows the language you switch TO

    # settings
    "settings":  {"en": "Settings", "tr": "Ayarlar"},
    "interval":  {"en": "Check interval (s):", "tr": "Kontrol aralığı (sn):"},
    "tiers":     {"en": "Tiers:", "tr": "Seviyeler:"},
    "open_page": {"en": "Open detail page on new giveaway",
                  "tr": "Yeni çekilişte detay sayfasını aç"},
    "auto_join": {"en": "Auto-join (FREE only, deposit = 0)",
                  "tr": "Otomatik katıl (yalnızca ÜCRETSİZ, depozito = 0)"},
    "debug":     {"en": "DEBUG (write debug_payloads.json)",
                  "tr": "DEBUG (debug_payloads.json yaz)"},

    # buttons
    "start":     {"en": "Start", "tr": "Başlat"},
    "proceed":   {"en": "I'm logged in → Start monitoring",
                  "tr": "Giriş yaptım → İzlemeyi başlat"},
    "stop":      {"en": "Stop", "tr": "Durdur"},
    "clear_log": {"en": "Clear log", "tr": "Logu temizle"},
    "log":       {"en": "Log", "tr": "Log"},

    # statuses (single live field)
    "st_ready":      {"en": "Ready", "tr": "Hazır"},
    "st_wait_login": {"en": "Waiting for login...", "tr": "Giriş bekleniyor..."},
    "st_monitoring": {"en": "Monitoring", "tr": "İzleniyor"},
    "st_starting":   {"en": "Starting...", "tr": "Başlatılıyor..."},
    "st_stopping":   {"en": "Stopping...", "tr": "Durduruluyor..."},
    "st_stopped":    {"en": "Stopped", "tr": "Durduruldu"},

    # log messages
    "log_ready": {"en": "Ready. 'Start' → browser opens → Steam login → 'Start monitoring'.",
                  "tr": "Hazır. 'Başlat' → tarayıcı açılır → Steam giriş → 'İzlemeyi başlat'."},
    "log_page_fail": {"en": "Could not open page: {e}", "tr": "Sayfa açılamadı: {e}"},
    "log_browser_opened": {"en": "Browser opened. Log in with Steam if needed and view the list.",
                           "tr": "Tarayıcı açıldı. Gerekirse Steam ile GİRİŞ YAP, listeyi gör."},
    "log_redirecting": {"en": "Redirecting to the giveaway list...",
                        "tr": "Çekiliş listesine yönlendiriliyor..."},
    "log_redirect_err": {"en": "Redirect error: {e}", "tr": "Yönlendirme hatası: {e}"},
    "log_monitor_start": {"en": "Monitoring started. Tiers={tiers}, interval={interval}s",
                          "tr": "İzleme başladı. Seviyeler={tiers}, aralık={interval}s"},
    "log_page_fail_try": {"en": "Could not open page (attempt {a}/{n}): {e}",
                          "tr": "Sayfa açılamadı (deneme {a}/{n}): {e}"},
    "log_list_retry": {"en": "List didn't load, retrying... ({a}/{n})",
                       "tr": "Liste yüklenemedi, yeniden deneniyor... ({a}/{n})"},
    "log_list_fail": {"en": "List failed to load after several attempts (connection issue?); "
                            "will retry next round.",
                      "tr": "Liste birkaç denemede de yüklenemedi (bağlantı sorunu olabilir); "
                            "bir sonraki turda tekrar denenecek."},
    "log_no_records": {"en": "WARNING: No records captured. Enable DEBUG and share "
                             "debug_payloads.json.",
                       "tr": "UYARI: Hiç kayıt yakalanamadı. DEBUG'i açıp "
                             "debug_payloads.json'i paylaş."},
    "alert_joinable": {"en": "YOU CAN JOIN!  {tier}  |  {summary}",
                       "tr": "KATILABİLİRSİN!  {tier}  |  {summary}"},
    "log_detail_open": {"en": "Detail page opened: {url}", "tr": "Detay sayfası açıldı: {url}"},
    "alert_auto_joined": {"en": "AUTO-JOINED (free): {clicked}",
                          "tr": "OTOMATİK KATILDIN (ücretsiz): {clicked}"},
    "log_join_btn_missing": {"en": "Free 'join giveaway' button not found "
                                   "(maybe already joined or the page differs).",
                             "tr": "Ücretsiz 'çekilişe katıl' butonu bulunamadı "
                                   "(zaten katılmış ya da sayfa farklı olabilir)."},
    "log_deposit_skip": {"en": "Requires deposit (deposit={dep}{cur}); auto-join SKIPPED, your call.",
                         "tr": "Depozito istiyor (depo={dep}{cur}); otomatik katılım ATLANDI, "
                               "karar senin."},
    "log_back_to_list": {"en": "Returned to the giveaway list.",
                         "tr": "Çekiliş listesine geri dönüldü."},
    "log_detail_err": {"en": "Detail page/join error: {e}", "tr": "Detay sayfası/katılım hatası: {e}"},
    "log_no_new": {"en": "No new joinable giveaways. "
                         "(Joinable: {joinable}, joined: {joined}, total watched: {total})",
                   "tr": "Yeni katılınabilir çekiliş yok. "
                         "(Katılabilir: {joinable}, katıldıkların: {joined}, toplam izlenen: {total})"},
    "log_pick_tier": {"en": "Select at least one tier.", "tr": "En az bir seviye seç."},
    "log_starting": {"en": "Starting, opening browser...", "tr": "Başlatılıyor, tarayıcı açılıyor..."},
    "log_monitor_ok": {"en": "Monitoring confirmed.", "tr": "İzleme onaylandı."},
    "log_stop_req": {"en": "Stop requested...", "tr": "Durdurma istendi..."},
    "log_error": {"en": "ERROR: {e}", "tr": "HATA: {e}"},

    # summarize() field labels
    "sum_tier":         {"en": "tier", "tr": "seviye"},
    "sum_status":       {"en": "status", "tr": "durum"},
    "sum_participants": {"en": "participants", "tr": "katılımcı"},
    "sum_remaining":    {"en": "remaining", "tr": "kalan"},
    "sum_deposit":      {"en": "deposit", "tr": "depozito"},
    "sum_joined":       {"en": "joined", "tr": "katıldım"},
    "sum_none":         {"en": "(see debug_payloads.json for details)",
                         "tr": "(detay için debug_payloads.json)"},
    "dl_expired":       {"en": "expired", "tr": "süresi doldu"},
}


def t(key, **kw):
    """Return the text for `key` in the active language, formatted with kwargs."""
    entry = TXT.get(key, {})
    s = entry.get(_LANG["v"]) or entry.get("en") or key
    if kw:
        try:
            s = s.format(**kw)
        except Exception:
            pass
    return s


# ----------------- SCHEMA-AGNOSTIC GIVEAWAY FINDER -----------------

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
            return t("dl_expired")
        m, s = divmod(int(secs), 60)
        h, m = divmod(m, 60)
        if _LANG["v"] == "tr":
            return f"{h}sa {m}dk" if h else f"{m}dk {s}sn"
        return f"{h}h {m}m" if h else f"{m}m {s}s"
    except Exception:
        return str(ms)


def summarize(data):
    bits = []
    if "frequency" in data:
        bits.append(f"{t('sum_tier')}={data['frequency']}")
    if "status" in data:
        bits.append(f"{t('sum_status')}={data['status']}")
    if "participantCount" in data:
        mx = data.get("maxUsers", "?")
        bits.append(f"{t('sum_participants')}={data['participantCount']}/{mx}")
    if "deadlineTimestamp" in data:
        bits.append(f"{t('sum_remaining')}={_fmt_deadline(data['deadlineTimestamp'])}")
    if "depositAmountRequired" in data and data["depositAmountRequired"]:
        bits.append(f"{t('sum_deposit')}={data['depositAmountRequired']}"
                    f"{data.get('depositAmountCurrency','')}")
    if "haveIJoined" in data:
        bits.append(f"{t('sum_joined')}={data['haveIJoined']}")
    # fall back to the old generic method if no known field is present
    if not bits:
        for k in ("id", "slug", "code", "name", "title", "prize"):
            if k in data and not isinstance(data[k], (dict, list)):
                bits.append(f"{k}={data[k]}")
    return ", ".join(bits) if bits else t("sum_none")


def collect_giveaways(payloads, ws_frames, watch_tiers):
    """Collect watched-tier giveaways from captured API responses.

    First reads the known /giveaway/list response (body['data'] list);
    each record's 'frequency' (tier), 'status', 'haveIJoined' fields live there.
    If no structured data is found, falls back to schema-agnostic scanning.
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

    # Fallback: if the API structure changed, use the old generic scan
    if not found and not structured:
        for _url, body in payloads:
            find_giveaways(body, found, watch_tiers)
        for frame in ws_frames:
            find_giveaways(frame, found, watch_tiers)

    return found


def _norm(s):
    """Reduce Turkish characters to ascii and lowercase (for safe matching)."""
    for a, b in (("İ", "i"), ("I", "i"), ("ı", "i"), ("Ş", "s"), ("ş", "s"),
                 ("Ç", "c"), ("ç", "c"), ("Ğ", "g"), ("ğ", "g"),
                 ("Ü", "u"), ("ü", "u"), ("Ö", "o"), ("ö", "o")):
        s = s.replace(a, b)
    return s.lower()

# Buttons that must never be clicked (paid / risky). 'join again' costs money.
_BLOCKED_BUTTON_WORDS = ("tekrar", "yeniden", "again", "2x", "sans")


async def try_join_free(detail_page):
    """On the detail page, click ONLY the free 'join giveaway' button.
    NEVER clicks 'join again' (paid) or similar buttons.
    Returns the button text if clicked, otherwise None."""
    for el in await detail_page.query_selector_all("button, [role=button]"):
        try:
            if not (await el.is_visible() and await el.is_enabled()):
                continue
            raw = (await el.inner_text()).strip()
        except Exception:
            continue
        if not raw or len(raw) > 45:
            continue
        tb = _norm(raw)
        if any(bad in tb for bad in _BLOCKED_BUTTON_WORDS):
            continue
        if "katil" in tb and "cekilis" in tb:   # "cekilise katil" (join giveaway)
            await el.click()
            return raw
    return None


def detail_url(data, gid):
    """Address of the giveaway's detail/join page. Derived from the organizer field;
    if missing, assumes it's Key-Drop's own giveaway ('keydrop')."""
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


def got_list_data(payloads):
    """Did the giveaway list API response arrive? (sign the page actually loaded)"""
    for _url, body in payloads:
        if isinstance(body, dict) and isinstance(body.get("data"), list):
            return True
    return False


def is_joinable(data):
    """Can I join this giveaway RIGHT NOW? (active + not yet joined + not expired)"""
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


def q_status(key):
    """Send a status KEY (translated in the UI so it follows language changes)."""
    ui_queue.put(("status", key))


# --------------------------- WORKER (async) ------------------------

async def monitor(config):
    watch_tiers = config["tiers"]
    interval = config["interval"]
    debug = config["debug"]
    open_page = config.get("open_page", True)
    auto_join = config.get("auto_join", False)

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
            q_log(t("log_page_fail", e=e))

        q_log(t("log_browser_opened"))
        ui_queue.put(("ready_for_login", None))
        q_status("st_wait_login")

        # Login gate: wait until the user clicks 'Start monitoring'
        while not proceed_event.is_set():
            if stop_event.is_set():
                await ctx.close()
                return
            await asyncio.sleep(0.3)

        # User clicked 'Start monitoring': bring them back to the giveaway list
        # automatically (they may have ended up elsewhere after logging in).
        q_log(t("log_redirecting"))
        try:
            await page.goto(GIVEAWAYS_URL, wait_until="domcontentloaded")
        except Exception as e:
            q_log(t("log_redirect_err", e=e))

        notified = set()   # ids we already announced as "you can join"
        q_status("st_monitoring")
        q_log(t("log_monitor_start", tiers=sorted(watch_tiers), interval=interval))

        while not stop_event.is_set():
            # Load the list page. If it doesn't load (internet etc.) retry a few times.
            loaded = False
            for attempt in range(1, LIST_LOAD_RETRIES + 1):
                payloads.clear()
                ws_frames.clear()
                try:
                    await page.goto(GIVEAWAYS_URL, wait_until="domcontentloaded")
                except Exception as e:
                    q_log(t("log_page_fail_try", a=attempt, n=LIST_LOAD_RETRIES, e=e))
                # Wait for giveaway data (max LIST_LOAD_TIMEOUT s).
                waited = 0.0
                while (waited < LIST_LOAD_TIMEOUT and not got_list_data(payloads)
                       and not stop_event.is_set()):
                    await asyncio.sleep(0.5)
                    waited += 0.5
                if got_list_data(payloads):
                    loaded = True
                    break
                if stop_event.is_set():
                    break
                q_log(t("log_list_retry", a=attempt, n=LIST_LOAD_RETRIES))
                await asyncio.sleep(2)

            if stop_event.is_set():
                break
            if not loaded:
                q_log(t("log_list_fail"))

            found = collect_giveaways(list(payloads), list(ws_frames), watch_tiers)

            if debug:
                try:
                    with open("debug_payloads.json", "w", encoding="utf-8") as f:
                        json.dump({"http": payloads, "ws": ws_frames}, f,
                                  ensure_ascii=False, indent=2, default=str)
                except Exception:
                    pass

            if not found:
                q_log(t("log_no_records"))
            else:
                joinable = {g: i for g, i in found.items() if is_joinable(i["data"])}
                joined = [g for g, i in found.items() if i["data"].get("haveIJoined") is True]
                new_joinable = [g for g in joinable if g not in notified]

                for gid in new_joinable:
                    info = joinable[gid]
                    q_alert(t("alert_joinable", tier=info['tier'].upper(),
                              summary=summarize(info['data'])))
                    notified.add(gid)

                # If there's a new joinable giveaway: go to the detail page, (if free)
                # join it, then RETURN to the giveaway list so monitoring continues.
                if new_joinable and (open_page or auto_join):
                    gid = new_joinable[0]
                    data = joinable[gid]["data"]
                    url = detail_url(data, gid)
                    deposit = data.get("depositAmountRequired")
                    try:
                        await page.goto(url, wait_until="domcontentloaded")
                        q_log(t("log_detail_open", url=url))

                        if auto_join and deposit == 0:
                            await asyncio.sleep(3)  # let the join button render
                            clicked = await try_join_free(page)
                            if clicked:
                                q_alert(t("alert_auto_joined", clicked=repr(clicked)))
                            else:
                                q_log(t("log_join_btn_missing"))
                        elif auto_join and deposit != 0:
                            q_log(t("log_deposit_skip", dep=deposit,
                                    cur=data.get('depositAmountCurrency', '')))

                        # Done -> go back to the giveaway list.
                        if auto_join:
                            await asyncio.sleep(1)
                            await page.goto(GIVEAWAYS_URL, wait_until="domcontentloaded")
                            q_log(t("log_back_to_list"))
                    except Exception as e:
                        q_log(t("log_detail_err", e=e))

                if not new_joinable:
                    q_log(t("log_no_new", joinable=len(joinable),
                            joined=len(joined), total=len(found)))

            # interruptible wait
            waited = 0.0
            while waited < interval and not stop_event.is_set():
                await asyncio.sleep(0.5)
                waited += 0.5

        await ctx.close()
        q_status("st_stopped")


def worker_main(config):
    try:
        asyncio.run(monitor(config))
    except Exception as e:
        q_log(t("log_error", e=e))
    finally:
        ui_queue.put(("stopped", None))


# ------------------------------- UI --------------------------------

class App:
    def __init__(self, root):
        self.root = root
        root.geometry("720x560")
        root.minsize(620, 480)

        # current status key (so the live status follows language changes)
        self.status_key = "st_ready"

        pad = {"padx": 8, "pady": 6}

        # Top: status (left) + language toggle (right)
        top = ttk.Frame(root)
        top.pack(fill="x", **pad)
        self.status_caption = ttk.Label(top, text="")
        self.status_caption.pack(side="left")
        self.status_var = tk.StringVar()
        self.status_lbl = ttk.Label(top, textvariable=self.status_var,
                                    font=("Segoe UI", 10, "bold"))
        self.status_lbl.pack(side="left", padx=6)
        self.lang_btn = ttk.Button(top, text="", width=10, command=self.toggle_lang)
        self.lang_btn.pack(side="right")

        # Settings
        self.cfg = ttk.LabelFrame(root, text="")
        self.cfg.pack(fill="x", **pad)

        self.interval_lbl = ttk.Label(self.cfg, text="")
        self.interval_lbl.grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.interval_var = tk.IntVar(value=25)
        ttk.Spinbox(self.cfg, from_=10, to=300, increment=5, width=6,
                    textvariable=self.interval_var).grid(row=0, column=1, sticky="w")

        self.tiers_lbl = ttk.Label(self.cfg, text="")
        self.tiers_lbl.grid(row=0, column=2, sticky="w", padx=12)
        self.tier_vars = {}
        col = 3
        for tier in ALL_TIERS:
            v = tk.BooleanVar(value=(tier == "amateur"))
            self.tier_vars[tier] = v
            ttk.Checkbutton(self.cfg, text=tier, variable=v).grid(row=0, column=col,
                                                                  sticky="w", padx=2)
            col += 1

        self.openpage_var = tk.BooleanVar(value=True)
        self.openpage_chk = ttk.Checkbutton(self.cfg, text="", variable=self.openpage_var)
        self.openpage_chk.grid(row=1, column=1, columnspan=4, sticky="w", pady=4)
        self.autojoin_var = tk.BooleanVar(value=True)
        self.autojoin_chk = ttk.Checkbutton(self.cfg, text="", variable=self.autojoin_var)
        self.autojoin_chk.grid(row=2, column=1, columnspan=4, sticky="w")
        self.debug_var = tk.BooleanVar(value=True)
        self.debug_chk = ttk.Checkbutton(self.cfg, text="", variable=self.debug_var)
        self.debug_chk.grid(row=3, column=1, columnspan=4, sticky="w")

        # Buttons
        btns = ttk.Frame(root)
        btns.pack(fill="x", **pad)
        self.start_btn = ttk.Button(btns, text="", command=self.on_start)
        self.start_btn.pack(side="left")
        self.proceed_btn = ttk.Button(btns, text="", command=self.on_proceed, state="disabled")
        self.proceed_btn.pack(side="left", padx=6)
        self.stop_btn = ttk.Button(btns, text="", command=self.on_stop, state="disabled")
        self.stop_btn.pack(side="left")
        self.clear_btn = ttk.Button(btns, text="", command=self.clear_log)
        self.clear_btn.pack(side="right")

        # Log
        self.logf = ttk.LabelFrame(root, text="")
        self.logf.pack(fill="both", expand=True, **pad)
        self.log = scrolledtext.ScrolledText(self.logf, height=15, wrap="word",
                                             font=("Consolas", 9), state="disabled")
        self.log.pack(fill="both", expand=True, padx=4, pady=4)
        self.log.tag_config("alert", foreground="#c00000", font=("Consolas", 9, "bold"))
        self.log.tag_config("info", foreground="#222222")

        self.retranslate()
        self.append(t("log_ready"), "info")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(150, self.poll_queue)

    # --- language ---
    def toggle_lang(self):
        _LANG["v"] = "tr" if _LANG["v"] == "en" else "en"
        self.retranslate()

    def retranslate(self):
        """Re-apply every static widget's text in the active language."""
        self.root.title(t("win_title"))
        self.status_caption.config(text=t("status_label"))
        self.lang_btn.config(text=t("lang_btn"))
        self.cfg.config(text=t("settings"))
        self.interval_lbl.config(text=t("interval"))
        self.tiers_lbl.config(text=t("tiers"))
        self.openpage_chk.config(text=t("open_page"))
        self.autojoin_chk.config(text=t("auto_join"))
        self.debug_chk.config(text=t("debug"))
        self.start_btn.config(text=t("start"))
        self.proceed_btn.config(text=t("proceed"))
        self.stop_btn.config(text=t("stop"))
        self.clear_btn.config(text=t("clear_log"))
        self.logf.config(text=t("log"))
        self.status_var.set(t(self.status_key))

    def set_status(self, key):
        self.status_key = key
        self.status_var.set(t(key))

    # --- log helpers ---
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

    # --- button actions ---
    def on_start(self):
        global worker_thread
        tiers = {tier for tier, v in self.tier_vars.items() if v.get()}
        if not tiers:
            self.append(t("log_pick_tier"), "alert")
            return
        stop_event.clear()
        proceed_event.clear()
        config = {
            "tiers": tiers,
            "interval": max(10, int(self.interval_var.get())),
            "debug": self.debug_var.get(),
            "open_page": self.openpage_var.get(),
            "auto_join": self.autojoin_var.get(),
        }
        worker_thread = threading.Thread(target=worker_main, args=(config,), daemon=True)
        worker_thread.start()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.set_status("st_starting")
        self.append(t("log_starting"), "info")

    def on_proceed(self):
        proceed_event.set()
        self.proceed_btn.config(state="disabled")
        self.append(t("log_monitor_ok"), "info")

    def on_stop(self):
        stop_event.set()
        self.stop_btn.config(state="disabled")
        self.set_status("st_stopping")
        self.append(t("log_stop_req"), "info")

    def on_close(self):
        stop_event.set()
        self.root.after(300, self.root.destroy)

    # --- queue listener ---
    def poll_queue(self):
        try:
            while True:
                kind, payload = ui_queue.get_nowait()
                if kind == "log":
                    self.append(payload, "info")
                elif kind == "alert":
                    self.append(payload, "alert")
                elif kind == "status":
                    self.set_status(payload)
                elif kind == "ready_for_login":
                    self.proceed_btn.config(state="normal")
                elif kind == "stopped":
                    self.start_btn.config(state="normal")
                    self.stop_btn.config(state="disabled")
                    self.proceed_btn.config(state="disabled")
                    if self.status_key not in ("st_stopping", "st_stopped"):
                        self.set_status("st_stopped")
        except queue.Empty:
            pass
        self.root.after(150, self.poll_queue)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
