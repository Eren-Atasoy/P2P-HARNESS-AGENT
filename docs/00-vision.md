# 00 — Vizyon ve Sınırlar

## 1. Tek cümlelik tanım

> **Prompt2Product, kullanıcının erişebildiği AI agent'larını, araçlarını ve
> runtime'larını otonom biçimde koordine ederek doğal dildeki ürün isteklerini
> doğrulanmış yazılım ürünlerine dönüştüren, model-bağımsız ve local-first bir
> yazılım mühendisliği platformudur.**

Üç iddianın her biri bağlayıcıdır:

**Otonom.** Kullanıcı prompt verir; agent'lar arasında mesaj taşımaz, "şimdi
sıra kimde" diye düşünmez. Orchestrator task üretir, bağımlılık çözer, agent
seçer, paralel çalıştırır, doğrular, inceletir, düzelttirir ve devam eder
(`docs/03 §7`).

**Model-bağımsız.** Claude ve Gemini, P2P'yi geliştirirken kullandığımız ilk
iki runtime'dır — mimarinin dayanağı değil. Kullanıcı hangi AI'a erişiyorsa
(abonelik, API, yerel model, gateway) sistem onu kullanır (`docs/04`).

**Doğrulanmış.** Bir işin bittiğine dil modeli karar vermez; kapı çıkış kodu
karar verir (`docs/05`).

### Otonomi, "insan hiç yok" demek değil

Otonomi seviyeli çalışır (`docs/03 §5`): varsayılan `guarded` modda yalnızca
mimari onayı, yayın onayı ve `high` risk task'ları insana gelir. `full` modda
proje kapıları da otomatik geçilir — ama **hangi kararların insansız verildiği
asla gizlenmez**; her biri `decided_by=default` olarak kaydedilir ve raporlanır.

Kapatılamayan tek şey `high` risk task'larıdır: ödeme, kimlik doğrulama, sır,
yıkıcı migration, dağıtım. Gerekçe basit — modelin özgüveni, riskin gerçek
büyüklüğüyle ilişkili değildir.

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

Bu ikisi, ürünün desteklediği runtime'ların **ilk ikisidir**; ayrıcalıklı
değildir. `RuntimeAdapter` ve `Connection` soyutlamaları (`docs/04`) sayesinde
üçüncü bir runtime eklemek çekirdeğe dokunmaz.

### 4.2 `p2p` — sattığın/dağıttığın ürün

Başka bir kullanıcının makinesinde, **onun** kimlik bilgisiyle çalışır.

> **Mutlak kural:** Senin aboneliğin hiçbir zaman başka bir kullanıcının
> isteğine hizmet edemez. Bu hem sağlayıcı sözleşmelerinin ihlali hem de
> teknik olarak imkânsızdır (oturum yerel makineye bağlıdır).
>
> Ürün daima **BYOC** (bring your own credentials) modelinde çalışır:
> kullanıcı kendi bağlantılarını getirir — abonelik tabanlı CLI, API anahtarı,
> yerel model veya gateway. Hepsi tek bir `Connection` soyutlamasıyla temsil
> edilir (`docs/04 §2`).
>
> Ayrıca: bir aboneliğin üçüncü taraf yazılımca otomatik kullandırılmasının
> **izinli** olup olmadığı teknik bir soru değildir. P2P bu konuda karar
> vermez ama sessiz de kalmaz: her bağlantı bir `automation_policy` taşır
> (`docs/04 §3`, `docs/11 V6`).

Bu ayrım kod seviyesinde de korunur: çekirdek motor hiçbir yerde bir kimlik
bilgisi saklamaz, sadece kullanıcının makinesindeki CLI'ları çağırır.

## 5. Başarı kriterleri (v1)

v1, aşağıdakiler **kanıtlanabilir** olduğunda başarılıdır:

| # | Kriter | Nasıl ölçülür |
|---|---|---|
| S1 | Tek promptan çalışan ürün | `p2p new "..."` → `guarded` modda en fazla 2 insan onayı → `docker compose up` → tarayıcıda açılıyor |
| S1b | Gerçek otonomi | `--autonomy full` ile başlatılan bir koşu, insan müdahalesi olmadan en az bir tam `implement → verify → review → fix → verify` döngüsünü tamamlıyor |
| S2 | Doğrulama gerçek | Bilerek bozulan bir kabul kriteri, pipeline'ı FAIL ettiriyor |
| S3 | Model bağımsızlığı | (a) `routing.yaml`'da bağlantı değiştirmek çekirdek koda dokunmadan çalışıyor; (b) çekirdek kaynak kodunda hiçbir sağlayıcı/model adı geçmiyor (grep ile kanıtlanır) |
| S4 | Yapısal tutarlılık | Aynı prompttan üretilen 3 task graph'ın **hepsinde**: çevrim yok, her MUST kapasitesi kapsanmış, paralel çiftler disjoint, kritik yol uzunluğu ±1 içinde |
| S5 | Kurtarılabilirlik | Süreç ortasında `Ctrl+C` → `p2p resume` kaldığı yerden devam ediyor |
| S6 | Şeffaflık | Her adım için "hangi model, hangi prompt, hangi çıktı, hangi maliyet" diskten okunabiliyor |

## 6. Açık olmayan hedefler (v1 kapsam dışı)

Kapsam disiplini için burada tutuluyor. Bunlara "sonra" bile denmeyecek,
gerekçeli bir ADR olmadan girilmeyecek:

- Bulut yürütme, çok kullanıcılı eşzamanlılık, takım işbirliği
- Kubernetes, mesaj kuyruğu, event sourcing, mikroservis
- Kendi model gateway'imiz (OmniRoute dahil — bkz. ADR-005). Gateway,
  `Connection` türü olarak tanımlıdır; adapter'ı Faz 9'da eklenebilir
- API, yerel model ve gateway adapter'larının **uygulanması** (arayüz v1'de
  tanımlı, uygulama Faz 9)
- Web UI (v1 CLI'dır; UI Faz 10+)
- Mobil uygulama üretimi (Faz 8'de değerlendirilecek, v1'de web+backend)
- Otomatik production deployment (v1 artifact üretir, deploy etmez)

## 7. Hedef kullanıcı

**Birincil:** kendi başına çalışan, ürün fikrini hızlıca gerçek bir kod
tabanına dönüştürmek isteyen, kodu okuyabilen ve sahiplenmek isteyen geliştirici.

Kritik nokta: P2P'nin çıktısı **devralınabilir** olmalı. Kullanıcı yarın P2P'yi
silip repoyu normal bir proje gibi geliştirebilmeli. Bu, üretilen kodun
`.p2p/` metadata'sından tamamen bağımsız olmasını zorunlu kılar.
