# AREV video indirme güncellemesi

## Neden Nashi çalışırken AREV hata verebiliyor?

İncelenen kaynaklar: Nashi `Sources/NashiCore/WebDownloadEngine.swift`, `ExternalToolSetup.swift`; AREV `server/media/media_worker.py`, `worker.ts`, `routes.ts` ve mobil istemci.

| Konu | Nashi | Yüklenen AREV | Bu güncelleme |
|---|---|---|---|
| İndirme bağlantısı | Bilgisayarın interneti | API sunucusunun interneti | Bu mimari korundu; kendi bilgisayarında servis çalıştırma tarifi eklendi |
| yt-dlp | Hazır macOS dosyası, 2026.08.19 | Python paketi, 2026.10.26 | Aynı sürüm korundu, `default` bağımlılık grubu eklendi |
| EJS | Resmî hazır dosyada paketli | requirements dosyasında yok | Uyumlu EJS bağımlılığı artık kurulumda geliyor |
| Deno | Nashi açıkça yolunu geçiriyor | Yalnızca AREV_DENO tanımlıysa açıkça ayarlanıyor | AREV_DENO veya PATH üzerinden bulunuyor |
| MP4 sesi | Önce M4A tercih ediliyor | En yüksek bitrate, kodek fark etmeksizin | Önce M4A tercih ediliyor |
| HEAD isteği başarısızlığı | Çıkarıcıya devam edebiliyor | Çıkarıcıdan önce kesilebiliyor | Medya bulunamadıysa çıkarıcı deneniyor; özel ağ engeli korunuyor |
| İndirme aşaması hataları | Ayrıntılı hata sınıflandırma | Genel download_failed | Bot doğrulaması ve oturum hataları incelemeyle aynı sınıflandırılıyor |
| Servis testi | Yerel araç durumu | API ayakta mı? | yt-dlp, EJS, Deno, FFmpeg ve ffprobe denetleniyor |

Aldığınız `source_blocked` hatası gerçek bir YouTube bot/hesap doğrulaması yanıtından üretiliyor; keyfî olarak verilen bir uygulama engeli değil. EJS eksikliği ayrı ve somut bir kurulum sorunu. EJS düzeltmesi her sunucu bağlantısındaki hesap doğrulamasını ortadan kaldırmaz. Paylaşılan kodlardan çalışan dağıtımınızın ağını veya yüklü paketlerini gözlemlemek mümkün değil.

Resmî belge: https://github.com/yt-dlp/yt-dlp/wiki/EJS — hazır yt-dlp dosyaları EJS içerir; pip kurulumunda `yt-dlp[default]` gerekir.

## Mevcut sunucuyu güncelleme

Güncellenmiş kaynakları sunucunuza aktarın. Sadece mobil/web arayüzünü yeniden yayınlamak Python bağımlılığını düzeltmez.

Docker kullanıyorsanız mevcut dağıtımınızın Dockerfile'ını bu sürümle yeniden oluşturup konteyneri yeniden dağıtın. Dockerfile artık EJS içe aktarmasını ve Deno/FFmpeg/ffprobe çalışmasını derleme sırasında kontrol eder.

Docker dışı kurulum (Linux/macOS örneği):

```bash
corepack enable
corepack prepare pnpm@9.12.0 --activate
pnpm install --frozen-lockfile
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-media.txt
# Sistemde Deno, ffmpeg ve ffprobe da kurulmuş olmalı.
pnpm build
AREV_MEDIA_PYTHON="$PWD/.venv/bin/python" pnpm start
```

Deno PATH üzerinde değilse `AREV_DENO` değişkenine çalıştırılabilir dosyanın tam yolunu verin. Windows'ta Python yolu `.venv\Scripts\python.exe` olur; ortam değişkenlerini kullandığınız kabuğa göre tanımlayın. Docker en az elle kurulum gerektiren seçenektir.

Ön yüzü kendi yayınlama yönteminize göre yeniden oluşturun; mobilde güncellenmiş derlemeyi kurun. Ayarlar → **Medya motorunu test et** seçeneğini çalıştırın. Hazır yanıtı araçların çalıştığını gösterir; bir video bağlantısına erişimi garanti etmez.

## Nashi gibi bilgisayarınızın bağlantısını kullanma

Docker Desktop/Docker Engine kurulu bilgisayarınızda proje klasöründen:

```bash
docker compose -f compose.local.yml up --build -d
```

Bu servis yalnızca `127.0.0.1:3000` üzerinde dinler. Bilgisayarın doğrudan internet çıkışını kullanır. Mobil cihazdan erişim için bu servise yönlendiren, geçerli sertifikalı bir HTTPS adresi sağlayın (kendi ters vekiliniz veya kendi HTTPS tüneliniz). AREV Ayarlar alanına o adresi yazıp kaydedin. `localhost`, telefonda bilgisayarınızı ifade etmez. Mevcut HTTPS API adresinizde bu kaynakları dağıtmak da mümkündür.

Web arayüzünüz farklı bir sitedeyse izin verilen origin'i ekleyin; origin'e dizin yolu yazmayın:

```bash
AREV_ALLOWED_ORIGINS=https://kendi-siteniz.example docker compose -f compose.local.yml up --build -d
```

Bilgisayarınız açık kalmalı. Bu seçenek mobil uygulamanın içinde yerel yt-dlp çalıştırmaz; telefon kendi bilgisayarınızdaki servisi kullanır. Telefon üzerinde tamamen bağımsız indirme için ayrı Android/iOS yerel motor entegrasyonu gerekir; Expo JS arayüzü tek başına bunu sağlamaz. Sunucu URL ayarı web sürümünde de geçerlidir.

## Tanılama

API: `GET /api/media/diagnostics`, diğer medya istekleri gibi `x-arev-client` başlığı ister. Yanıt kurulu araç sürümlerini, eksikleri ve `sourceAccessVerified: false` bilgisini verir. Yol, hesap bilgisi veya ham kaynak hata metni döndürmez. İstemci/adres başına dakikada 5 kontrol sınırı vardır.

Sunucuda doğrudan kontrol:

```bash
printf '%s\n' '{"command":"diagnostics"}' | .venv/bin/python server/media/media_worker.py
```

- `ejs_unavailable`: Python bağımlılıklarını yeniden kurun veya imajı yeniden oluşturun.
- `runtime_unavailable`: Deno kurulumunu/AREV_DENO yolunu kontrol edin.
- `network_unavailable`: sunucunun DNS/internet bağlantısını kontrol edin.
- `source_blocked`: YouTube bu servis bağlantısından hesap doğrulaması istiyor; bu, eksik EJS ile aynı hata değil.

## Doğrulama

- Python: 12 regresyon testi başarılı.
- Vitest: 43 test başarılı; mevcut auth.logout testi atlanmış durumda.
- TypeScript `tsc --noEmit` başarılı.
- Sunucu esbuild derlemesi başarılı.
- Gerçek yt-dlp 2026.10.26, EJS 0.8.0, Deno 2.9.7 ve FFmpeg/ffprobe ile tanılama `ready: true` verdi.
- Bu çalışma ortamında YouTube alan adı DNS çözümlemesi başarısız olduğu için canlı YouTube indirmesi doğrulanamadı. Kullanıcının API sunucusuna yayın yapılmadı; Android/iOS paket derlemesi ve cihaz testi yapılmadı. Docker imajı bu ortamda çalıştırılmadı.

Testleri tekrar çalıştırmak için:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
pnpm test
pnpm check
pnpm build
```

Güvenli ağ/IP kontrolleri ve DRM/özel içerik kısıtları korundu. Güncelleme hesap çerezi veya kimlik bilgisi istemez.
