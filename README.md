# Keydrop Çekiliş İzleyici

---

## TÜRKÇE

Keydrop sitesindeki amateur çekilişlerini otomatik olarak takip eden küçük bir araç. Henüz katılmadığın ve hâlâ aktif olan bir çekiliş bulduğunda ekrana düşürüyor, çekilişin sayfasını açıyor ve ücretsiz çekilişlere senin yerine katılıyor; böylece "katılabileceğin" çekilişleri kaçırmıyorsun.

---

### Kurulum

Klasördeki `kurulum.bat` dosyasını bir kez çalıştır. Gerekli her şeyi kendi yükleyecek. Bu adımı tekrar yapman gerekmez.

---

### Kullanım

`baslat.bat` dosyasını çalıştır. Açılan pencerede **Başlat** butonuna bas, Chrome otomatik olarak Keydrop'a gidecek. Eğer daha önce giriş yapmadıysan Steam hesabınla o sayfadan giriş yap — program bunu bir kez yaptıktan sonra hatırlıyor. Giriş yaptıktan sonra penceredeki **"Giriş yaptım → İzlemeyi başlat"** butonuna bas, izleme başlasın.

Katılabileceğin (aktif olan ve henüz katılmadığın) bir amateur çekilişi bulununca pencerede kırmızı bir satır göreceksin. Aynı anda program **aynı sekmede** o çekilişin detay sayfasına gider ve **ücretsiz (depozito = 0)** çekilişlerde "çekilişe katıl" butonuna senin yerine basar. Depozito isteyen çekilişlerde sayfayı açar ama katılmaz — kararı sana bırakır. İşi bitince çekiliş listesine geri döner ve izlemeye kaldığı yerden devam eder. Zaten katıldığın veya süresi dolmuş çekilişler için tekrar tekrar uyarı vermez. Durdurmak istediğinde **Durdur** butonuna basman yeterli.

---

### Ayarlar

Pencerenin üst kısmında birkaç seçenek var. Varsayılan değerleriyle gayet iyi çalışıyor ama istersen değiştirebilirsin. Kontrol aralığı sitenin kaç saniyede bir kontrol edileceğini belirliyor — 25 saniye yeterli, daha aşağıya çekmene gerek yok. Seviye seçiminden amateur dışında başka çekiliş tiplerini de ekleyebilirsin. "Yeni çekilişte detay sayfasını aç" seçeneği o sayfayı otomatik açma davranışını, "Otomatik katıl" seçeneği ise ücretsiz çekilişlere otomatik katılmayı açıp kapatır. DEBUG seçeneği de orada.

---

### Sorun yaşarsan

"Hiç amateur kaydı yakalanamadı" gibi bir uyarı görürsen DEBUG modunu açık bırakarak programı bir kez çalıştır. Klasörde `debug_payloads.json` adında bir dosya oluşur, bu dosya sorunun nereden kaynaklandığını anlamak için kullanılabilir.

---

### Klasör içeriği

Günlük kullanımda sana lazım olan iki dosya kök klasörde duruyor: kurulumu yapan `kurulum.bat` ve programı açan `baslat.bat`. Bir de okuduğun bu `README.md`. Programın asıl kodları `kaynak/` klasöründe (`keydrop_ui.py`, `keydrop_monitor.py`, `requirements.txt`) — bunlara dokunmana gerek yok. Çalışırken oluşan `keydrop_profile/` (tarayıcı oturumun) ve `debug_payloads.json` dosyaları kişisel verindir, GitHub'a gönderilmez.

---

### Güvenlik

Steam oturum bilgilerin hiçbir yere gönderilmiyor. Program yalnızca senin kendi açtığın tarayıcı oturumunu kullanıyor.

---
---

## ENGLISH

A lightweight tool that monitors Keydrop for amateur giveaways. When it finds one that's still active and that you haven't joined yet, it logs it on screen, navigates to the giveaway's detail page, and joins **free (deposit = 0)** giveaways for you automatically. For giveaways that require a deposit, it opens the page but never joins — that's left to you.

---

### Setup

Run `kurulum.bat` from the folder once. It will handle all the necessary installations automatically. You won't need to do this again.

---

### Usage

Run `baslat.bat`. In the window that opens, click **Başlat (Start)** and Chrome will automatically navigate to Keydrop. If you haven't logged in before, sign in with your Steam account on that page — the program remembers it after the first time. Once you're logged in, click **"Giriş yaptım → İzlemeyi başlat"** (I'm logged in → Start monitoring) and you're good to go.

When a joinable amateur giveaway (active and not yet joined) is found, a red line will appear in the log. At the same time the program navigates to that giveaway's detail page **in the same tab** and, for **free (deposit = 0)** giveaways, clicks the join button for you. For giveaways requiring a deposit it opens the page but won't join — that's your call. When it's done it returns to the giveaway list and keeps monitoring where it left off. It won't keep alerting you about giveaways you've already joined or ones that have expired. Hit **Durdur (Stop)** whenever you want to stop.

---

### Settings

There are a few options at the top of the window. It works fine out of the box, but you can adjust them if needed. The check interval controls how frequently the site is checked — 25 seconds is plenty, no need to go lower. You can add other giveaway tiers alongside amateur if you want. The "open detail page on new giveaway" option toggles auto-opening that page, and "auto join" toggles automatically joining free giveaways. The DEBUG toggle is there as well.

---

### Troubleshooting

If you see something like "No amateur entries found", run the program once with DEBUG enabled. A file called `debug_payloads.json` will appear in the folder, which can be used to figure out what's going wrong.

---

### Folder contents

For everyday use, the only files you need live in the root folder: `kurulum.bat` (one-time setup), `baslat.bat` (launches the program), and this `README.md`. The actual program code sits in the `kaynak/` folder (`keydrop_ui.py`, `keydrop_monitor.py`, `requirements.txt`) — you don't need to touch it. The `keydrop_profile/` (your browser session) and `debug_payloads.json` files are created while running; they're personal data and are never pushed to GitHub.

---

### Security

Your Steam session data is never sent anywhere. The program simply reuses the browser session you opened yourself.
