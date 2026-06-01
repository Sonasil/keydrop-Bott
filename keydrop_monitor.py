"""
Key-Drop "amateur" cekilis izleyici (monitor).

NE YAPAR:
  - Giris yapilmis bir tarayici oturumu ile /tr/giveaways/list sayfasini izler.
  - Belirli araliklarla katilabilecegin (aktif + henuz katilmadigin) cekilis var mi diye bakar.
  - Boyle bir cekilis bulununca konsola yazar ve detay sayfasini ayri sekmede acar.
  - UCRETSIZ (depozito=0) cekilise otomatik katilir ('cekilise katil' butonuna basar).

NE YAPMAZ:
  - Depozito (para) isteyen cekilise ASLA otomatik katilmaz; karar sana birakilir.
  - 'tekrar katil' gibi para isteyen butonlara ASLA basmaz.
  - Otomatik giris yapmaz; Steam girisini bir kere sen elle yaparsin, oturum saklanir.

KURULUM:  README.md dosyasina bak.
"""

import asyncio
import json
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
# Detay sayfasinda UCRETSIZ (depozito=0) cekilise otomatik katil ('cekilise katil').
# 'tekrar katil' (parali) butonuna ASLA basmaz; depozitolu cekilise hic dokunmaz.
AUTO_JOIN_FREE = True

# True yaparsan yakalanan ham veriyi debug_payloads.json'a doker.
# Ilk calistirmada True birak, dosyayi bana yolla; eslestirmeyi siteye gore netlestirelim.
DEBUG = True

# JSON icinde ID olabilecek anahtarlar.
ID_KEYS = ("id", "giveawayId", "uuid", "slug", "code", "_id", "hash")
# JSON icinde seviye/tier olabilecek anahtarlar.
TIER_KEYS = ("frequency", "category", "type", "tier", "name", "level", "rank", "kind", "group")
# Bu durumlardaki cekilise artik katilamazsin (bitmis/iptal).
FINISHED_STATUSES = {"ended", "finished", "cancelled", "canceled", "closed", "drawn"}

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


def _norm(s):
    """Turkce karakterleri ascii'ye indirger ve kucuk harfe cevirir (guvenli eslesme icin)."""
    for a, b in (("İ", "i"), ("I", "i"), ("ı", "i"), ("Ş", "s"), ("ş", "s"),
                 ("Ç", "c"), ("ç", "c"), ("Ğ", "g"), ("ğ", "g"),
                 ("Ü", "u"), ("ü", "u"), ("Ö", "o"), ("ö", "o")):
        s = s.replace(a, b)
    return s.lower()

# Asla basilmayacak butonlar (parali / risk). 'tekrar katil' para ister.
_BLOCKED_BUTTON_WORDS = ("tekrar", "yeniden", "again", "2x", "sans")


async def try_join_free(detail_page):
    """Detay sayfasinda YALNIZCA ucretsiz 'cekilise katil' butonuna basar.
    'tekrar katil' (parali) ve benzeri butonlara ASLA basmaz.
    Tikladiysa butonun metnini, basmadiysa None doner."""
    for el in await detail_page.query_selector_all("button, [role=button]"):
        try:
            if not (await el.is_visible() and await el.is_enabled()):
                continue
            raw = (await el.inner_text()).strip()
        except Exception:
            continue
        if not raw or len(raw) > 45:
            continue
        t = _norm(raw)
        if any(bad in t for bad in _BLOCKED_BUTTON_WORDS):
            continue
        if "katil" in t and "cekilis" in t:   # "cekilise katil"
            await el.click()
            return raw
    return None


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
                    notified.add(gid)

                # Yeni katilinabilir cekilis varsa detay sayfasini ayri sekmede ac.
                # Izleme ana sekmede surer; katilma butonuna basmak sana kalir.
                if new_joinable and OPEN_DETAIL_PAGE:
                    gid = new_joinable[0]
                    data = joinable[gid]["data"]
                    url = detail_url(data, gid)
                    deposit = data.get("depositAmountRequired")
                    try:
                        if detail_page is None or detail_page.is_closed():
                            detail_page = await ctx.new_page()
                        await detail_page.goto(url, wait_until="domcontentloaded")
                        await detail_page.bring_to_front()
                        log(f"Detay sayfasi acildi: {url}")

                        if AUTO_JOIN_FREE and deposit == 0:
                            await asyncio.sleep(3)  # katil butonu render olsun
                            clicked = await try_join_free(detail_page)
                            if clicked:
                                log(f"OTOMATIK KATILDIN (ucretsiz): {clicked!r}")
                            else:
                                log("Ucretsiz 'cekilise katil' butonu bulunamadi "
                                    "(zaten katilmis ya da sayfa farkli olabilir).")
                        elif AUTO_JOIN_FREE and deposit != 0:
                            log(f"Depozito istiyor (depo={deposit}"
                                f"{data.get('depositAmountCurrency','')}); "
                                f"otomatik katilim ATLANDI, karar senin.")
                    except Exception as e:
                        log(f"Detay sayfasi/katilim hatasi: {e}")

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
