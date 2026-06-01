# Key-Drop amateur cekilis izleyici

Yeni bir **amateur** cekilisi acildiginda **ses calar + konsola yazar**.
Senin yerine "Join/Katil" butonuna **basmaz** — katilmayi sen yaparsin.

## Kurulum (bir kere)

PowerShell'i bu klasorde ac ve sirayla:

```powershell
# 1) Sanal ortam (opsiyonel ama onerilir)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Gerekli paket
pip install -r requirements.txt

# 3) Tarayiciyi indir
python -m playwright install chromium
```

## Calistirma — ARAYUZ (onerilen)

```powershell
python keydrop_ui.py
```

Pencere acilir. Kullanim:
1. **Baslat** -> bir Chrome penceresi acilir, keydrop listesine gider.
2. Gerekirse **Steam ile giris yap** ve listeyi gor.
3. Arayuzde **"Giris yaptim -> Izlemeyi baslat"** dugmesine bas.
4. Yeni cekilis acilinca **ses calar** ve log'a **kirmizi** satir duser.
5. **Durdur** ile istedigin an durdurabilirsin.

Ayarlar (pencerenin ustunde): kontrol araligi (sn), izlenecek seviyeler
(amateur/contender/challenger/champion), ses ac/kapa, DEBUG ac/kapa.

## Calistirma — TERMINAL (alternatif)

```powershell
python keydrop_monitor.py
```

1. Bir Chrome penceresi acilir ve keydrop cekilis listesine gider.
2. Gerekirse **Steam ile giris yap** ve cekilis listesini gor.
   (Giris bilgisi `keydrop_profile/` klasorunde saklanir; bir dahaki sefere tekrar giris gerekmez.)
3. Listeyi gorunce, **bu terminal penceresinde ENTER'a bas**.
4. Bot izlemeye baslar. Yeni amateur cekilisi acilinca bip sesi calar ve satir yazar.

Durdurmak icin terminalde **Ctrl + C**.

## Ayarlar (`keydrop_monitor.py` ust kismi)

- `CHECK_INTERVAL` — kac saniyede bir kontrol (varsayilan 25; cok dusurme).
- `WATCH_TIERS` — izlenecek seviyeler (varsayilan `{"amateur"}`). Ileride
  `{"amateur", "contender"}` gibi genisletebiliriz.
- `DEBUG` — `True` iken yakalanan ham veriyi `debug_payloads.json`'a yazar.

## ILK CALISTIRMA NOTU (onemli)

Site verisini giris yapmadan goremedigim icin bot, gelen veride "amateur"
etiketli kayitlari **kendi tarayarak** bulur. Ilk calistirmada eger
"Hic amateur kaydi yakalanamadi" uyarisi gorursen, olusan **`debug_payloads.json`**
dosyasini paylas; eslestirmeyi siteye birebir oturtalim.

## Sinirlar / dogru kullanim

- Sadece **izleme + bildirim** yapar; otomatik katilim (auto-join) yoktur.
- Kontrol araligini makul tut (sunucuyu gereksiz yorma).
- Steam girisini her zaman sen elle yaparsin; bot sifre/oturum calmaz, sadece
  senin actigin oturumu yeniden kullanir.
