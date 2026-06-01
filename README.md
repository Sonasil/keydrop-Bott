# Keydrop Çekiliş İzleyici

---

## TÜRKÇE

Keydrop sitesindeki amateur çekilişlerini otomatik olarak takip eden küçük bir araç. Henüz katılmadığın ve hâlâ aktif olan bir çekiliş bulduğunda sesli uyarı veriyor ve ekrana düşürüyor; böylece "katılabileceğin" çekilişleri kaçırmıyorsun. Çekilişe gidip katılmak tamamen sana bırakılmış.

---

### Kurulum

Klasördeki `kurulum.bat` dosyasını bir kez çalıştır. Gerekli her şeyi kendi yükleyecek. Bu adımı tekrar yapman gerekmez.

---

### Kullanım

`baslat.bat` dosyasını çalıştır. Açılan pencerede **Başlat** butonuna bas, Chrome otomatik olarak Keydrop'a gidecek. Eğer daha önce giriş yapmadıysan Steam hesabınla o sayfadan giriş yap — program bunu bir kez yaptıktan sonra hatırlıyor. Giriş yaptıktan sonra penceredeki **"Giriş yaptım → İzlemeyi başlat"** butonuna bas, izleme başlasın.

Katılabileceğin (aktif olan ve henüz katılmadığın) bir amateur çekilişi bulununca sesli uyarı duyacak ve pencerede kırmızı bir satır göreceksin. Aynı anda program o çekilişin detay (katılma) sayfasını **ayrı bir sekmede** otomatik açar; böylece tek yapman gereken o sayfadaki katılma butonuna basmak olur. İzleme arka planda devam eder, seni sayfadan koparmaz. Zaten katıldığın veya süresi dolmuş çekilişler için tekrar tekrar uyarı vermez. Durdurmak istediğinde **Durdur** butonuna basman yeterli.

---

### Ayarlar

Pencerenin üst kısmında birkaç seçenek var. Varsayılan değerleriyle gayet iyi çalışıyor ama istersen değiştirebilirsin. Kontrol aralığı sitenin kaç saniyede bir kontrol edileceğini belirliyor — 25 saniye yeterli, daha aşağıya çekmene gerek yok. Seviye seçiminden amateur dışında başka çekiliş tiplerini de ekleyebilirsin. "Yeni çekilişte detay sayfasını aç" seçeneği, çekiliş bulununca o sayfayı otomatik açma davranışını kapatıp açmana yarar. Ses ve DEBUG seçenekleri de orada.

---

### Sorun yaşarsan

"Hiç amateur kaydı yakalanamadı" gibi bir uyarı görürsen DEBUG modunu açık bırakarak programı bir kez çalıştır. Klasörde `debug_payloads.json` adında bir dosya oluşur, bu dosya sorunun nereden kaynaklandığını anlamak için kullanılabilir.

---

### Güvenlik

Steam oturum bilgilerin hiçbir yere gönderilmiyor. Program yalnızca senin kendi açtığın tarayıcı oturumunu kullanıyor.

---
---

## ENGLISH

A lightweight tool that monitors Keydrop for amateur giveaways. When it finds one that's still active and that you haven't joined yet, it plays an alert sound and logs it on screen — so you don't miss giveaways you could still enter. Actually going and joining is entirely up to you.

---

### Setup

Run `kurulum.bat` from the folder once. It will handle all the necessary installations automatically. You won't need to do this again.

---

### Usage

Run `baslat.bat`. In the window that opens, click **Başlat (Start)** and Chrome will automatically navigate to Keydrop. If you haven't logged in before, sign in with your Steam account on that page — the program remembers it after the first time. Once you're logged in, click **"Giriş yaptım → İzlemeyi başlat"** (I'm logged in → Start monitoring) and you're good to go.

When a joinable amateur giveaway (active and not yet joined) is found, you'll hear an alert sound and a red line will appear in the log. At the same time the program automatically opens that giveaway's detail (join) page in a **separate tab**, so all you have to do is click the join button there. Monitoring keeps running in the background and won't pull you away from the page. It won't keep alerting you about giveaways you've already joined or ones that have expired. Hit **Durdur (Stop)** whenever you want to stop.

---

### Settings

There are a few options at the top of the window. It works fine out of the box, but you can adjust them if needed. The check interval controls how frequently the site is checked — 25 seconds is plenty, no need to go lower. You can add other giveaway tiers alongside amateur if you want. The "open detail page on new giveaway" option lets you turn the auto-open behavior on or off. Sound and DEBUG toggles are there as well.

---

### Troubleshooting

If you see something like "No amateur entries found", run the program once with DEBUG enabled. A file called `debug_payloads.json` will appear in the folder, which can be used to figure out what's going wrong.

---

### Security

Your Steam session data is never sent anywhere. The program simply reuses the browser session you opened yourself.
