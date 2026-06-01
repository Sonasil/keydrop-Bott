# Keydrop Çekiliş İzleyici

---

## TÜRKÇE

Keydrop sitesindeki amateur çekilişlerini otomatik olarak takip eden küçük bir araç. Yeni bir çekiliş açıldığında sesli uyarı veriyor ve ekrana düşürüyor. Çekilişe katılıp katılmamak tamamen sana bırakılmış.

---

### Kurulum

Klasördeki `kurulum.bat` dosyasını bir kez çalıştır. Gerekli her şeyi kendi yükleyecek. Bu adımı tekrar yapman gerekmez.

---

### Kullanım

`baslat.bat` dosyasını çalıştır. Açılan pencerede **Başlat** butonuna bas, Chrome otomatik olarak Keydrop'a gidecek. Eğer daha önce giriş yapmadıysan Steam hesabınla o sayfadan giriş yap — program bunu bir kez yaptıktan sonra hatırlıyor. Giriş yaptıktan sonra penceredeki **"Giriş yaptım → İzlemeyi başlat"** butonuna bas, izleme başlasın.

Yeni bir amateur çekilişi açıldığında sesli uyarı duyacak ve pencerede kırmızı bir satır göreceksin. Durdurmak istediğinde **Durdur** butonuna basman yeterli.

---

### Ayarlar

Pencerenin üst kısmında birkaç seçenek var. Varsayılan değerleriyle gayet iyi çalışıyor ama istersen değiştirebilirsin. Kontrol aralığı sitenin kaç saniyede bir kontrol edileceğini belirliyor — 25 saniye yeterli, daha aşağıya çekmene gerek yok. Seviye seçiminden amateur dışında başka çekiliş tiplerini de ekleyebilirsin. Ses ve DEBUG seçenekleri de orada.

---

### Sorun yaşarsan

"Hiç amateur kaydı yakalanamadı" gibi bir uyarı görürsen DEBUG modunu açık bırakarak programı bir kez çalıştır. Klasörde `debug_payloads.json` adında bir dosya oluşur, bu dosya sorunun nereden kaynaklandığını anlamak için kullanılabilir.

---

### Güvenlik

Steam oturum bilgilerin hiçbir yere gönderilmiyor. Program yalnızca senin kendi açtığın tarayıcı oturumunu kullanıyor.

---
---

## ENGLISH

A lightweight tool that monitors Keydrop for new amateur giveaways. When one opens, it plays an alert sound and logs it on screen. Joining or not is completely up to you.

---

### Setup

Run `kurulum.bat` from the folder once. It will handle all the necessary installations automatically. You won't need to do this again.

---

### Usage

Run `baslat.bat`. In the window that opens, click **Başlat (Start)** and Chrome will automatically navigate to Keydrop. If you haven't logged in before, sign in with your Steam account on that page — the program remembers it after the first time. Once you're logged in, click **"Giriş yaptım → İzlemeyi başlat"** (I'm logged in → Start monitoring) and you're good to go.

When a new amateur giveaway opens, you'll hear an alert sound and a red line will appear in the log. Hit **Durdur (Stop)** whenever you want to stop.

---

### Settings

There are a few options at the top of the window. It works fine out of the box, but you can adjust them if needed. The check interval controls how frequently the site is checked — 25 seconds is plenty, no need to go lower. You can add other giveaway tiers alongside amateur if you want. Sound and DEBUG toggles are there as well.

---

### Troubleshooting

If you see something like "No amateur entries found", run the program once with DEBUG enabled. A file called `debug_payloads.json` will appear in the folder, which can be used to figure out what's going wrong.

---

### Security

Your Steam session data is never sent anywhere. The program simply reuses the browser session you opened yourself.
