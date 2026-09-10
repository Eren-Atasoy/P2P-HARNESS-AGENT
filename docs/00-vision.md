# 00 — Vizyon ve Sınırlar

## 1. Tek cümlelik tanım

Prompt2Product (P2P), doğal dildeki bir ürün isteğini; ürün tanımına, mimariye,
bağımlılık farkında bir görev grafiğine ve oradan **çalışan + otomatik
doğrulanmış** bir yazılım ürününe dönüştüren, yerel makinede çalışan,
model-bağımsız bir orkestrasyon platformudur.

Vaat, "tek promptla ürün" değil — **tek promptla, iki onay noktasıyla
doğrulanmış ürün**. Bu iki nokta (mimari onayı ve yayın onayı) mimarinin
parçasıdır, sürtünmesi değil: bir dil modelinin geri dönüşü en pahalı iki
kararını insana bırakır. Bu ayrımı bulanıklaştıran her pazarlama cümlesi,
`docs/03 §5`'teki kapılarla çelişir. (C2)

## 2. Ne değil

Bu ayrım ürünün kimliğidir; bulanıklaşırsa proje başka bir "AI site jeneratörü"ne
dönüşür.

| P2P **değildir** | Çünkü |
|---|---|
| Frontend jeneratörü (v0, Lovable, Bolt) | Backend, veri modeli, auth ve test kapsam içinde |
| Chat tabanlı kodlama asistanı | Girdi tek bir ürün isteği, çıktı doğrulanmış bir repo |
| Bulut SaaS | Yerel çalışır; kullanıcının kodu makinesinden çıkmak zorunda değil |
| Model sağlayıcı | Kendi inference'ını satmaz; kullanıcının kimlik bilgisini kullanır |
| Otonom "her şeyi kendin yap" sistemi | İnsan onay kapıları mimarinin parçasıdır |

## 3. Farklılaşma tezi

Rakiplerin çoğu **üretim** problemini çözüyor. P2P'nin iddiası **doğrulama**
problemini çözmek.

> Üretilen kodun derlenmesi "bitti" demek değildir.
> Bir görev, kabul kriterleri **ölçülebilir biçimde** karşılandığında biter.

Bu tez üç somut mimari sonuç doğurur ve dokümanların geri kalanı bunların
üstüne kuruludur:

1. **Kalite kapısı deterministiktir.** Bir işin geçip geçmediğine asla bir dil
   modeli karar vermez; process exit code'u karar verir. (`docs/05`)
2. **Durum, üretilen metinden değil, kontrolörden gelir.** Agent'lar orkestrasyon
   state'ine yazamaz. (`docs/02`, ADR-003)
3. **Mimari, uygulamadan izole korunur.** Uygulayıcı agent mimari kararı
   değiştiremez; ancak itiraz edebilir. (`docs/03`, ACR mekanizması)

## 4. İki ayrı ürün — karıştırılmamalı

Bu, projenin en kritik ve en kolay kaçırılan ayrımıdır.

### 4.1 `p2p-dev` — senin koşum takımın

Senin makinende, senin **Claude Pro** ve **Google AI Ultra** aboneliklerini
kullanarak P2P'yi geliştirmene yarayan iç araç.

- Claude Pro oturumu → `claude -p` ile mimar/gözden geçiren
- AI Ultra oturumu → `gemini -p` ile uygulayıcı

### 4.2 `p2p` — sattığın/dağıttığın ürün

Başka bir kullanıcının makinesinde, **onun** kimlik bilgisiyle çalışır.

> **Mutlak kural:** Senin aboneliğin hiçbir zaman başka bir kullanıcının
> isteğine hizmet edemez. Bu hem sağlayıcı sözleşmelerinin ihlali hem de
> teknik olarak imkânsızdır (oturum yerel makineye bağlıdır).
>
> Ürün daima **BYOC** (bring your own credentials) modelinde çalışır:
> kullanıcı kendi `claude` / `gemini` kurulumunu getirir.

Bu ayrım kod seviyesinde de korunur: çekirdek motor hiçbir yerde bir kimlik
bilgisi saklamaz, sadece kullanıcının makinesindeki CLI'ları çağırır.

## 5. Başarı kriterleri (v1)

v1, aşağıdakiler **kanıtlanabilir** olduğunda başarılıdır:

| # | Kriter | Nasıl ölçülür |
|---|---|---|
| S1 | Tek promptan çalışan ürün | `p2p new "..."` akışı, **en fazla 2 zorunlu insan onayıyla** tamamlanıyor → `docker compose up` → tarayıcıda açılıyor |
| S2 | Doğrulama gerçek | Bilerek bozulan bir kabul kriteri, pipeline'ı FAIL ettiriyor |
| S3 | Model bağımsızlığı | Routing config'de `backend: gemini → claude` değişikliği, çekirdek koda dokunmadan çalışıyor |
| S4 | Yapısal tutarlılık | Aynı prompttan üretilen 3 task graph'ın **hepsinde**: çevrim yok, her MUST kapasitesi kapsanmış, paralel çiftler disjoint, kritik yol uzunluğu ±1 içinde |
| S5 | Kurtarılabilirlik | Süreç ortasında `Ctrl+C` → `p2p resume` kaldığı yerden devam ediyor |
| S6 | Şeffaflık | Her adım için "hangi model, hangi prompt, hangi çıktı, hangi maliyet" diskten okunabiliyor |

## 6. Açık olmayan hedefler (v1 kapsam dışı)

Kapsam disiplini için burada tutuluyor. Bunlara "sonra" bile denmeyecek,
gerekçeli bir ADR olmadan girilmeyecek:

- Bulut yürütme, çok kullanıcılı eşzamanlılık, takım işbirliği
- Kubernetes, mesaj kuyruğu, event sourcing, mikroservis
- Kendi model gateway'imiz (OmniRoute dahil — bkz. ADR-005)
- Web UI (v1 CLI'dır; UI Faz 10+)
- Mobil uygulama üretimi (Faz 8'de değerlendirilecek, v1'de web+backend)
- Otomatik production deployment (v1 artifact üretir, deploy etmez)

## 7. Hedef kullanıcı

**Birincil:** kendi başına çalışan, ürün fikrini hızlıca gerçek bir kod
tabanına dönüştürmek isteyen, kodu okuyabilen ve sahiplenmek isteyen geliştirici.

Kritik nokta: P2P'nin çıktısı **devralınabilir** olmalı. Kullanıcı yarın P2P'yi
silip repoyu normal bir proje gibi geliştirebilmeli. Bu, üretilen kodun
`.p2p/` metadata'sından tamamen bağımsız olmasını zorunlu kılar.
