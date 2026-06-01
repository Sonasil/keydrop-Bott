# Keydrop Çekiliş İzleyici

---

## TÜRKÇE

### Kurulum (sadece bir kere yapılır)

**1. Adım — Klasörü aç**

`kurulum.bat` dosyasına **çift tıkla.** Gerisini o halleder.

Siyah bir ekran açılır, birkaç şey indirir, kapanır. Bitti.

---

**2. Adım — Çalıştır**

`baslat.bat` dosyasına **çift tıkla.**

Bir pencere açılır. Devam et:

1. **Başlat** butonuna bas → Chrome açılır, Keydrop'a gider.
2. Açılan Chrome'da **Steam ile giriş yap** (sadece ilk seferde gerekli, sonra hatırlar).
3. Giriş yaptıktan sonra **"Giriş yaptım → İzlemeyi başlat"** butonuna bas.
4. Bot çalışmaya başlar. Yeni amateur çekilişi çıkınca **bip sesi** duyarsın ve kırmızı satır belirir.
5. Durdurmak istersen **Durdur** butonuna bas.

---

### Ayarlar (isteğe bağlı)

Pencerenin üstünde birkaç seçenek var:

| Ayar | Ne yapar |
|---|---|
| Kontrol aralığı | Kaç saniyede bir siteyi kontrol etsin (25 sn önerilen, çok düşürme) |
| Seviye seçimi | Hangi çekiliş seviyelerini izlesin (amateur, contender, challenger, champion) |
| Ses | Bip sesini açar/kapar |
| DEBUG | Geliştirici modu — sorun varsa açık bırak |

---

### Sorun mu var?

Eğer "Hiç amateur kaydı yakalanamadı" gibi bir uyarı görürsen:
- `DEBUG` açık olduğundan emin ol
- Botta bir tur çalıştır, `debug_payloads.json` dosyası oluşur
- O dosyayı bana gönder, düzeltiriz

---

### Notlar

- Steam şifren **hiçbir yere kaydedilmez.** Bot sadece senin açtığın oturumu yeniden kullanır.
- Çekilişe otomatik girmez. İnsan eliyle katılım zorunlu.
- Sunucuyu yormamak için kontrol aralığını çok düşürme.

---
---

## ENGLISH


### Setup (one time only)

**Step 1 — Open the folder**

Double-click `kurulum.bat`. It handles everything.

A black window opens, downloads a few things, then closes. Done.

---

**Step 2 — Run it**

Double-click `baslat.bat`.

A window opens. Then:

1. Click **Başlat (Start)** → Chrome opens and goes to Keydrop.
2. In Chrome, **log in with Steam** (only needed the first time — it remembers after that).
3. Once logged in, click **"Giriş yaptım → İzlemeyi başlat"** (I'm logged in → Start monitoring).
4. The bot starts running. When a new amateur giveaway appears, you'll hear a **beep** and see a red line.
5. To stop, click the **Durdur (Stop)** button.

---

### Settings (optional)

A few options at the top of the window:

| Setting | What it does |
|---|---|
| Check interval | How often it checks the site in seconds (25s recommended, don't go too low) |
| Tier selection | Which giveaway tiers to watch (amateur, contender, challenger, champion) |
| Sound | Toggle the beep on/off |
| DEBUG | Developer mode — leave on if something seems off |

---

### Something not working?

If you see a warning like "No amateur entries found":
- Make sure DEBUG is on
- Let the bot run one cycle — it will create a `debug_payloads.json` file
- Send that file over and we'll fix the matching

---

### Notes

- Your Steam password is **never stored anywhere.** The bot only reuses the session you opened yourself.
- It does not auto-join giveaways. Manual action is required.
- Don't set the check interval too low — no need to hammer the server.
