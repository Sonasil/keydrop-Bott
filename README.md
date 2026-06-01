# Keydrop Çekiliş İzleyici

---

## TÜRKÇE

### Ne işe yarar?

Keydrop sitesindeki **amateur** seviye çekilişleri sürekli takip eder. Yeni bir çekiliş açıldığında sesli bildirim verir ve ekrana yazar. Çekilişe katılmak tamamen sana kalmış, program sadece seni haberdar eder.

---

### Kurulum

İlk kullanımdan önce klasördeki `kurulum.bat` dosyasını çalıştır. Kısa bir kurulum ekranı açılıp kapanacak, gerekli her şey otomatik yüklenecek. Bunu bir kez yapman yeterli.

---

### Kullanım

`baslat.bat` dosyasını çalıştır. Karşına çıkan pencerede şu adımları izle:

1. **Başlat** butonuna bas. Bir Chrome penceresi açılır ve Keydrop'a gider.
2. Açılan tarayıcıda Steam hesabınla giriş yap. Bu adım yalnızca ilk seferde gereklidir, sonrasında oturum hatırlanır.
3. Giriş yaptıktan sonra programdaki **"Giriş yaptım → İzlemeyi başlat"** butonuna bas.
4. Program artık çalışıyor. Yeni bir amateur çekilişi açıldığında sesli uyarı alır, pencerede kırmızı bir satır görürsün.
5. Durdurmak istediğinde **Durdur** butonuna basman yeterli.

---

### Ayarlar

Pencerenin üst kısmında bazı seçenekler bulunuyor. Varsayılan haliyle gayet çalışır ama istersen değiştirebilirsin:

| Ayar | Açıklama |
|---|---|
| Kontrol aralığı | Sitenin kaç saniyede bir kontrol edileceği. 25 saniye önerilen değerdir. |
| Seviye seçimi | Hangi çekiliş tiplerinin izleneceği — amateur, contender, challenger, champion |
| Ses | Sesli bildirimi açar veya kapar |
| DEBUG | Sorun yaşanırsa açık bırak, arka planda veri kaydeder |

---

### Sorun giderme

Ekranda "Hiç amateur kaydı yakalanamadı" gibi bir uyarı görürsen büyük ihtimalle sitenin veri yapısında küçük bir uyumsuzluk vardır. DEBUG modunu açık bırakarak programı bir kez çalıştır, klasörde `debug_payloads.json` adında bir dosya oluşacak. Bu dosyayı inceleyerek ya da bir geliştirici ile paylaşarak sorunu tespit edebilirsin.

---

### Güvenlik

Steam şifren veya oturum bilgilerinden herhangi biri hiçbir yere kaydedilmez. Program yalnızca senin kendi açtığın tarayıcı oturumunu yeniden kullanır.

---
---

## ENGLISH

### What does it do?

It continuously monitors Keydrop for new **amateur** tier giveaways. When one opens up, it plays an alert sound and logs it on screen. Whether or not you join is entirely up to you — the program just keeps you informed.

---

### Setup

Before the first use, run `kurulum.bat` from the folder. A short setup window will open and close automatically, installing everything the program needs. You only need to do this once.

---

### Usage

Run `baslat.bat`. In the window that appears, follow these steps:

1. Click **Başlat (Start)**. A Chrome window will open and navigate to Keydrop.
2. Log into Keydrop using your Steam account in that browser window. This is only required the first time — your session will be remembered afterward.
3. Once logged in, click **"Giriş yaptım → İzlemeyi başlat"** (I'm logged in → Start monitoring) in the program window.
4. The program is now running. When a new amateur giveaway opens, you'll hear an alert and see a red line appear in the log.
5. When you want to stop, just hit the **Durdur (Stop)** button.

---

### Settings

There are a few options at the top of the window. The defaults work fine, but feel free to adjust:

| Setting | Description |
|---|---|
| Check interval | How frequently the site is checked, in seconds. 25 is the recommended value. |
| Tier selection | Which giveaway tiers to monitor — amateur, contender, challenger, champion |
| Sound | Enables or disables the audio alert |
| DEBUG | Leave this on if something isn't working — it saves raw data in the background |

---

### Troubleshooting

If you see a message like "No amateur entries found", there's likely a minor mismatch between the program and how the site currently structures its data. Run the program once with DEBUG enabled — a file called `debug_payloads.json` will appear in the folder. Reviewing that file or sharing it with a developer should point you to the issue.

---

### Security

Your Steam password and session data are never saved anywhere. The program simply reuses the browser session that you opened yourself, nothing more.
