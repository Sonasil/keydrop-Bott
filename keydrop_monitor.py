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
# Bir cekilisin detay (katilma) sayfasi. {org}=organizator, {id}=cekilis id.
DETAIL_URL = "https://keydrop.com/tr/giveaways/{org}/{id}"
# Yeni katilinabilir cekiliste detay sayfasini ayri sekmede otomatik ac.
OPEN_DETAIL_PAGE = True

# True yaparsan yakalanan ham veriyi debug_payloads.json'a doker.
# Ilk calistirmada True birak, dosyayi bana yolla; eslestirmeyi siteye gore netlestirelim.
DEBUG = True

# JSON icinde ID olabilecek anahtarlar.
ID_KEYS = ("id", "giveawayId", "uuid", "slug", "code", "_id", "hash")
# JSON icinde seviye/tier olabilecek anahtarlar.
TIER_KEYS = ("frequency", "category", "type", "tier", "name", "level", "rank", "kind", "group")
# Bu durumlardaki cekilise artik katilamazsin (bitmis/iptal).
FINISHED_STATUSES = {"ended", "finished", "cancelled", "canceled", "closed", "drawn"}

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


def collect_giveaways(payloads, ws_frames):
    """Yakalanan API yanitlarindan izlenen seviyedeki (WATCH_TIERS) cekilisleri toplar.

    Once yapisi bilinen /giveaway/list yanitini okur (body['data'] listesi);
    her kaydin 'frequency' (seviye), 'status', 'haveIJoined' alanlari burada gelir.
    Hicbir yapili veri yoksa semadan bagimsiz taramaya (find_giveaways) duser.
    """
    found = {}

    def consider(node):
        if not isinstance(node, dict):
            return
        freq = node.get("frequency")
        if not isinstance(freq, str):
            return
        tier = freq.strip().lower()
        if tier not in WATCH_TIERS:
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

    if not found and not structured:
        for _url, body in payloads:
            find_giveaways(body, found)
        for frame in ws_frames:
            find_giveaways(frame, found)

    return found


def detail_url(data, gid):
    """Cekilisin detay/katilma sayfasi adresi. Organizator alanindan turetilir,
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

        notified = set()   # zaten "katilabilirsin" diye haber verdigimiz id'ler
        detail_page = None  # detay sayfasini gosterdigimiz ayri sekme
        log(f"Izleme basliyor. Seviyeler={WATCH_TIERS}, aralik={CHECK_INTERVAL}s")

        while True:
            payloads.clear()
            ws_frames.clear()
            try:
                await page.goto(GIVEAWAYS_URL, wait_until="domcontentloaded")
            except Exception as e:
                log(f"Sayfa yenilenemedi: {e}")
            await asyncio.sleep(4)  # arka plan isteklerinin bitmesini bekle

            found = collect_giveaways(list(payloads), list(ws_frames))

            if DEBUG:
                try:
                    with open("debug_payloads.json", "w", encoding="utf-8") as f:
                        json.dump(
                            {"http": payloads, "ws": ws_frames},
                            f, ensure_ascii=False, indent=2, default=str,
                        )
                except Exception:
                    pass

            if not found:
                log("UYARI: Hic kayit yakalanamadi. DEBUG=True ile "
                    "debug_payloads.json'i kontrol et / bana yolla.")
            else:
                joinable = {g: i for g, i in found.items() if is_joinable(i["data"])}
                joined = [g for g, i in found.items() if i["data"].get("haveIJoined") is True]
                new_joinable = [g for g in joinable if g not in notified]

                for gid in new_joinable:
                    info = joinable[gid]
                    log(f"KATILABILIRSIN! {info['tier'].upper()} | {summarize(info['data'])}")
                    alert_sound()
                    notified.add(gid)

                # Yeni katilinabilir cekilis varsa detay sayfasini ayri sekmede ac.
                # Izleme ana sekmede surer; katilma butonuna basmak sana kalir.
                if new_joinable and OPEN_DETAIL_PAGE:
                    gid = new_joinable[0]
                    url = detail_url(joinable[gid]["data"], gid)
                    try:
                        if detail_page is None or detail_page.is_closed():
                            detail_page = await ctx.new_page()
                        await detail_page.goto(url, wait_until="domcontentloaded")
                        await detail_page.bring_to_front()
                        log(f"Detay sayfasi acildi (katilmak senin elinde): {url}")
                    except Exception as e:
                        log(f"Detay sayfasi acilamadi: {e}")

                if not new_joinable:
                    log(f"Yeni katilinabilir cekilis yok. "
                        f"(Katilabilir: {len(joinable)}, katildiklarin: {len(joined)}, "
                        f"toplam izlenen: {len(found)})")

            await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDurduruldu.")
