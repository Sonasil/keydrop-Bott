"""
Key-Drop "amateur" cekilis izleyici (monitor).

NE YAPAR:
  - Giris yapilmis bir tarayici oturumu ile /tr/giveaways/list sayfasini izler.
  - Belirli araliklarla yeni "amateur" cekilisi var mi diye bakar.
  - YENI bir amateur cekilisi acildiginda: ses calar + konsola yazar.

NE YAPMAZ:
  - Senin yerine "Join" / "Katil" butonuna BASMAZ. Katilma karari ve aksiyonu sana ait.
  - Otomatik giris yapmaz; Steam giriskini bir kere sen elle yaparsin, oturum saklanir.

KURULUM:  README.md dosyasina bak.
"""

import asyncio
import json
import sys
from datetime import datetime

from playwright.async_api import async_playwright

# ----------------------------- AYARLAR -----------------------------

# Izlenecek cekilis seviyeleri (kucuk harf). Simdilik sadece amateur.
WATCH_TIERS = {"amateur"}

# Kac saniyede bir kontrol edilsin (sunucuyu yormamak icin 20+ onerilir).
CHECK_INTERVAL = 25

# Tarayici profilinin saklanacagi klasor (giris bilgisi burada kalir).
USER_DATA_DIR = "./keydrop_profile"

GIVEAWAYS_URL = "https://keydrop.com/tr/giveaways/list"

# True yaparsan yakalanan ham veriyi debug_payloads.json'a doker.
# Ilk calistirmada True birak, dosyayi bana yolla; eslestirmeyi siteye gore netlestirelim.
DEBUG = True

# JSON icinde ID olabilecek anahtarlar.
ID_KEYS = ("id", "giveawayId", "uuid", "slug", "code", "_id", "hash")
# JSON icinde seviye/tier olabilecek anahtarlar.
TIER_KEYS = ("frequency", "category", "type", "tier", "name", "level", "rank", "kind", "group")

# ------------------------- BILDIRIM (SES) --------------------------

try:
    import winsound

    def alert_sound():
        # Dikkat cekmek icin birkac bip.
        for _ in range(3):
            winsound.Beep(1100, 250)
            winsound.Beep(1500, 250)
except Exception:  # winsound yoksa (Windows disi) terminal zili
    def alert_sound():
        for _ in range(3):
            sys.stdout.write("\a")
            sys.stdout.flush()


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


# ------------------ SEMADAN BAGIMSIZ CEKILIS BULUCU -----------------

def find_giveaways(node, found):
    """JSON agacini gezip 'amateur' (WATCH_TIERS) etiketli kayitlari toplar."""
    if isinstance(node, dict):
        matched_tier = None
        for k, v in node.items():
            if isinstance(v, str) and v.strip().lower() in WATCH_TIERS:
                # anahtar da tier anlamina geliyorsa daha guvenli bir eslesme
                if k.lower() in TIER_KEYS:
                    matched_tier = v.strip().lower()
        if matched_tier:
            gid = None
            for idk in ID_KEYS:
                if idk in node and isinstance(node[idk], (str, int)):
                    gid = str(node[idk])
                    break
            if gid is None:
                gid = str(abs(hash(json.dumps(node, sort_keys=True, default=str))))
            found[gid] = {"tier": matched_tier, "data": node}
        for v in node.values():
            find_giveaways(v, found)
    elif isinstance(node, list):
        for item in node:
            find_giveaways(item, found)
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
    """Bildirimde gostermek icin kayittan ise yarar alanlari cikar."""
    bits = []
    if "frequency" in data:
        bits.append(f"seviye={data['frequency']}")
    if "status" in data:
        bits.append(f"durum={data['status']}")
    if "participantCount" in data:
        bits.append(f"katilimci={data['participantCount']}/{data.get('maxUsers','?')}")
    if "deadlineTimestamp" in data:
        bits.append(f"kalan={_fmt_deadline(data['deadlineTimestamp'])}")
    if "depositAmountRequired" in data and data["depositAmountRequired"]:
        bits.append(f"depozito={data['depositAmountRequired']}{data.get('depositAmountCurrency','')}")
    if "haveIJoined" in data:
        bits.append(f"katildim={data['haveIJoined']}")
    if not bits:
        for k in ("id", "slug", "code", "name", "title", "prize"):
            if k in data and not isinstance(data[k], (dict, list)):
                bits.append(f"{k}={data[k]}")
    return ", ".join(bits) if bits else "(detay icin debug_payloads.json'a bak)"


# ------------------------------ ANA AKIS ----------------------------

async def main():
    payloads = []          # HTTP yanitlarindan gelen JSON'lar
    ws_frames = []         # websocket frame'lerinden gelen JSON'lar

    async def handle_response(response):
        try:
            url = response.url
            if "giveaway" in url.lower():
                ctype = response.headers.get("content-type", "")
                if "json" in ctype.lower():
                    payloads.append((url, await response.json()))
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
            headless=False,                       # giris yapabilmen icin gorunur
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        page.on("response", lambda r: asyncio.create_task(handle_response(r)))
        page.on("websocket", handle_ws)

        await page.goto(GIVEAWAYS_URL, wait_until="domcontentloaded")

        # --- Tek seferlik giris kapisi ---
        log("Tarayici acildi. Gerekirse Steam ile GIRIS YAP ve cekilis listesini gor.")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, input,
            ">>> Giris yapip listeyi gordukten sonra bu pencerede ENTER'a bas...\n"
        )

        seen = set()
        baseline_done = False
        log(f"Izleme basliyor. Seviyeler={WATCH_TIERS}, aralik={CHECK_INTERVAL}s")

        while True:
            payloads.clear()
            ws_frames.clear()
            try:
                await page.goto(GIVEAWAYS_URL, wait_until="domcontentloaded")
            except Exception as e:
                log(f"Sayfa yenilenemedi: {e}")
            await asyncio.sleep(4)  # arka plan isteklerinin bitmesini bekle

            found = {}
            for _url, data in list(payloads):
                find_giveaways(data, found)
            for frame in list(ws_frames):
                find_giveaways(frame, found)

            if DEBUG:
                try:
                    with open("debug_payloads.json", "w", encoding="utf-8") as f:
                        json.dump(
                            {"http": payloads, "ws": ws_frames},
                            f, ensure_ascii=False, indent=2, default=str,
                        )
                except Exception:
                    pass

            new_ids = [gid for gid in found if gid not in seen]

            if not baseline_done:
                seen.update(found.keys())
                baseline_done = True
                log(f"Baslangic taramasi: {len(found)} amateur kayit bulundu "
                    f"(mevcut olanlar 'gorulmus' sayildi, bildirim verilmedi).")
                if not found:
                    log("UYARI: Hic amateur kaydi yakalanamadi. DEBUG=True ile "
                        "debug_payloads.json'i kontrol et / bana yolla.")
            else:
                for gid in new_ids:
                    info = found[gid]
                    log(f"YENI AMATEUR CEKILIS! id={gid} | {summarize(info['data'])}")
                    alert_sound()
                    seen.add(gid)
                if not new_ids:
                    log(f"Yeni yok. (Takip edilen amateur sayisi: {len(seen)})")

            await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDurduruldu.")
