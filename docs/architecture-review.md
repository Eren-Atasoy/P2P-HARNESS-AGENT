# Mimari Gözden Geçirme (Red Team)

**Tarih:** 2026-09-10 · **Kapsam:** `docs/00`–`docs/10`, `docs/adr/*`,
`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `prompts/*`

---

## Verdict

Faz 1 ve Faz 2 **bugün başlayabilir**: veri modeli, olay deposu ve scheduler
aşağıdaki sorunların hiçbirinden etkilenmiyor ve modelsiz test edilebilir
oldukları için erken geri bildirim verirler. Ancak paket bugünkü hâliyle
Faz 5'e (gerçek runtime adapterları) **giremez**: uygulayıcı agent'a verilen
"bitti" tanımı, ona verilen çalıştırma yetkisiyle doğrudan çelişiyor (C1) ve
sistemin yapısal çıktısı, modelin prompt'a uyma nezaketine bağlanmış (C4).
Ayrıca ürünün tek cümlelik vaadi ile zorunlu insan kapıları arasında
çözülmemiş bir gerilim var (C2) — bu bir uygulama detayı değil, ürün kimliği
kararıdır ve Faz 7'nin çıkış kriterini ölçülemez bırakıyor.

**Faz 5'ten önce:** C1, C4, C5, M1, M2, M7 · **Faz 7'den önce:** C2, C3, M3 ·
**Faz 6'dan önce:** M4

---

## Critical Issues

### C1 — Uygulayıcı agent testleri çalıştıramaz, ama çalıştırması zorunlu tutuluyor

**Nerede:** `docs/04 §3.2` ↔ `GEMINI.md §3` ↔ `prompts/04-implement.md` adım 4-6

`docs/04 §3.2`, Gemini'yi `--approval-mode auto_edit` ile çalıştırıyor ve
"kabuk komutlarını onaylamaz" diyor; kabuk gerektiren işlerin kapılara ait
olduğunu belirtiyor. Aynı anda `GEMINI.md §3`, "yazdığın testleri çalıştırdın
ve geçiyorlar" ve "bir kez implementasyonu bozup kırmızı olduğunu gördün"
maddelerini "bitti" tanımının parçası yapıyor; `prompts/04` bunu 4., 5. ve 6.
adım olarak emrediyor.

**Neden kırılır:** Agent, yerine getiremeyeceği bir koşulla `completed`
raporlamak zorunda bırakılıyor. İki sonuçtan biri olur, ikisi de kötü:
(a) agent dürüstse asla `completed` dönmez, her task escalate olur;
(b) agent uyumluysa çalıştırmadığı testler için "geçti" der — sistemin tamamı
**yalan bir raporun** üstüne kurulur. Kalite iddiasının çöktüğü nokta burasıdır.

İkinci ve daha sinsi yüzü: headless modda onay istemiyle karşılaşıldığında ne
olacağı **hiçbir belgede tanımlı değil**. İstem askıda kalırsa her çalıştırmada
20 dakikalık zaman aşımına kadar bekleriz.

**Öneri:** Agent'a kendi test paketi için **dar kapsamlı** kabuk izni ver
(yalnızca test koşucusu ikilisi, argüman kalıbıyla sınırlı, `--policy` ile
tanımlı). Bağımlılık kurulumu ve migration orchestrator'da kalır. Tehdit modeli
ihlal edilmez: yasak olan **keyfi** komut, tüm komutlar değil. Alternatif,
`GEMINI.md §3`'ten test maddelerini kaldırmaktır — ama o zaman `docs/05 §7`'nin
en güçlü savunması kaybolur. Birinci seçenek tercih edilmeli.

Ayrıca her adapter için "onay istemi geldiğinde davranış" yazılmalı: stdin
kapalı, istem = anında başarısızlık, `ERROR` sınıfı.

---

### C2 — "Tek promptan ürün" vaadi ile dört zorunlu insan kapısı çelişiyor

**Nerede:** `docs/00 §1` ve `§5 (S1)` ↔ `docs/03 §5`

`docs/00` ürünü "Prompt in. Verified Product out." diye tanımlıyor ve S1
kriterini `p2p new "..."` → `docker compose up` olarak yazıyor. `docs/03 §5`
ise dört zorunlu insan kapısı tanımlıyor; G2 (mimari) ve G4 (yayın) için
"atlanamaz" diyor.

**Neden kırılır:** İkisi aynı anda doğru olamaz. S1'in ölçümü tek komutluk bir
akış tarif ediyor, G2/G4 akışı en az iki kez durduruyor. Faz 7'nin çıkış
kriteri bu yüzden ölçülemez: "çalışıyor" derken insanın iki kez müdahale
ettiği bir koşuyu mu, kapıları kapatılmış bir koşuyu mu kastediyoruz? Bir
mühendis bunu kendi kafasına göre yorumlayacak.

Bu bir tutarsızlıktan fazlası, konumlandırma kararı: kapıları savunuyorsan
ürün "tek promptla ürün" değil, **"tek promptla, iki onay noktasıyla ürün"**.
Bu dürüst ve savunulabilir bir vaat — ama `docs/00` bunu söylemiyor.

**Öneri:** S1'i yeniden yaz; kapıların akışın parçası olduğunu açıkça belirt ve
"insan etkileşimi ≤ N" biçiminde ölçülebilir yap. Vizyondaki tek cümlelik
vaadi de düzelt. Kapıları kaldırma — onlar doğru karar; yanlış olan, onları
görmezden gelen vaat.

---

### C3 — Paralel worktree'lerde çalışan kapılar birbirinin kaynağını çalar

**Nerede:** `docs/03 §2.3` + `docs/05 §3` + `ADR-006`

`ADR-006` paralel task'ları ayrı worktree'lere koyup dosya izolasyonunu doğru
çözüyor. Ama `docs/05 §3`'teki `smoke` kapısı `docker compose up` çalıştırıyor,
`integration` kapısı servis konteynerleri kaldırıyor. İki worktree aynı anda
bunu yaparsa: aynı port, aynı konteyner adı, aynı hacim, aynı compose proje adı.

**Neden kırılır:** Dosya izolasyonu çözülmüş, **çalışma zamanı izolasyonu
çözülmemiş**. Belirti sinsi olacak: task A'nın smoke testi, task B'nin ayakta
kalan konteynerine bağlanıp yeşil verecek. Yani yanlış bir `PASS` üretir —
`docs/05`'in tüm amacına aykırı ve hata ayıklaması çok zor.

**Öneri:** Her worktree'ye deterministik izolasyon kimliği ata
(`COMPOSE_PROJECT_NAME=p2p_<task_id>`), portları dinamik ata ve kapıya ortam
değişkeni olarak geçir. Kapı tanımına `isolation` alanı ekle:
`none | compose_project | container`. Basit alternatif: kaynak gerektiren
kapıları global semaforla serileştir — daha yavaş ama v1 için kabul edilebilir.
Bir karar verilmeli; şu an tanımsız.

---

### C4 — Sistemin yapısal çıktısı, modelin prompt'a uymasına bağlı

**Nerede:** `docs/04 §2` (adapter sorumluluk 4-5), `GEMINI.md §8`, `docs/02 §3`

Adapter `result.json`'u okuyup `AgentResult` üretiyor; ayrıştırma başarısızsa
`outcome=failed`. Yani sistemin task hakkında bildiği her şey, modelin "şu
dosyaya şu şemada JSON yaz" talimatına uymasından geçiyor.

**Neden kırılır:** Mimarinin geri kalanındaki şüphecilikle çelişen tek güven
noktası. Model 20 dakika doğru kod yazıp sonunda JSON'u yazmayı unutursa —
veya şemaya uymayan bir alan eklerse ki `extra="forbid"` nedeniyle bu **kesin**
kırılmadır — tüm iş `failed` sayılır ve bir deneme yanar. `docs/02 §3` zaten
`files_changed`'e inanmamayı söylüyor; aynı şüphecilik neden `result.json`'un
varlığına uygulanmıyor?

**Öneri:** `AgentResult`'ı zorunlu değil **tamamlayıcı** yap. Gerçek durum üç
bağımsız kaynaktan türetilsin: (1) `git status` — ne değişti, (2) kapı
sonuçları — çalışıyor mu, (3) `result.json` — agent ne düşünüyor. Üçüncüsü
eksikse `outcome` ilk ikisinden çıkarılır, `assumptions`/`acr` kaybı uyarı
olarak kaydedilir. `extra="forbid"` yalnızca bilinen alanlara uygulanır;
bilinmeyen alanlar loglanıp atılır. Aksi hâlde şema katılığı, korumak istediği
şeyi bozar.

---

### C5 — Ortam hazırlama (bootstrap) aşaması hiçbir yerde yok

**Nerede:** `docs/01 §4` yaşam döngüsü, `docs/08` Faz 4 ve 7, `docs/03 §3`

`docs/03 §3`, `ENV` sınıfını fix döngüsüne sokmayıp doğrudan `ESCALATED`
yapıyor — doğru karar. Ama yaşam döngüsünde bağımlılıkların **ne zaman ve kim
tarafından** kurulduğunu tanımlayan bir aşama yok; task graph'ta da böyle bir
task tipi tarif edilmiyor.

**Neden kırılır:** Yeni bir üretilen projede ilk task koştuğunda sanal ortam
yok, `node_modules` yok, veritabanı ayakta değil. Her kapı `ERROR` verir, her
task escalate olur, kullanıcı ilk denemede "her şey insan bekliyor" ekranı
görür. Bir mühendis bunu Faz 4'te keşfeder ve yaşam döngüsüne kendi kafasına
göre bir aşama uydurur.

**Öneri:** `WORKSPACE_BOOTSTRAP` aşaması ekle: iskelet oluşturma, bağımlılık
kurulumu (lock'tan), veritabanı ayağa kaldırma, migration ve bir "boş proje
smoke testi". Task graph'ın parçası değil, ondan önce gelen bir orchestrator
adımıdır ve `GUARDED` sınıfında çalışır. Faz 3 veya 4'ün çıkış kriterine yazılmalı.

---

## Major Issues

### M1 — Task sözleşmesi yazma yetkisi ADR-003 ile çelişiyor

`CLAUDE.md §2` Claude'a `.p2p/tasks/**` yazma izni veriyor; `docs/01 §3` ve
`ADR-003` "orkestrasyon durumunu yalnızca orchestrator yazar" diyor. Task
sözleşmesi durum mu, artifact mı? Belgeler cevap vermiyor; mühendis kural
uydurmak zorunda kalır.

**Öneri:** `TaskContract` **değişmez bir artifact**tır (durum değil; `status`
alanı zaten yok, bu iyi). Yine de mimar agent doğrudan yazmamalı: taslağı
`.p2p/docs/task-graph/` altına üretir, **orchestrator doğrulayıp**
`.p2p/tasks/` altına yerleştirir. Şema doğrulaması ve id çakışma kontrolü
tek yerde kalır.

### M2 — Testleri kim yazar: iki belge iki farklı şey söylüyor

`docs/05 §7` "testi başkası yazar; `test` capability'si ayrı task'tır" diyor ve
bunu AI'ın kendi kodunu doğrulamasına karşı **birincil önlem** yapıyor.
`docs/02 §2.2`'deki referans örnekte ise `API-001`'in `allowed_paths` listesinde
`tests/api/**` var — uygulayıcı kendi testini yazıyor. `prompts/03` "anlamlı
olduğunda ayrı task" diyerek üçüncü bir belirsizlik ekliyor.

**Öneri:** Tek kural seç, her yere uygula. Öneri: kabul kriterine bağlı testler
ayrı `TEST-` task'ında; uygulayıcı yalnızca iç birim testlerini yazabilir ve
bunlar kabul kriteri sayılmaz. Referans örneği düzelt — örnek, kuraldan daha
çok okunur.

### M3 — CI, `DONE` koşulu yapılmış ama hiçbir fazda uygulanmıyor

`docs/07 §5` "bir task `DONE` olmadan önce CI'nın da yeşil olması gerekir"
diyor ve bunu "bu belgenin en önemli kararı" diye işaretliyor. `docs/08`
roadmap'inde CI/GitHub entegrasyonunu üstlenen **hiçbir faz yok** (Faz 8
tarayıcı/regresyon, Faz 9 açık kaynak sertleştirme).

**Öneri:** Ya CI entegrasyonunu bir faza yaz (Faz 8'in doğal genişlemesi), ya
`docs/07 §5`'i v1 için "CI harici doğrulamadır, `DONE` koşulu değildir" diye
geri çek. İkincisi v1 kapsamı için daha dürüst. Şu anki hâli, uygulanmayacak
bir zorunluluk.

### M4 — Faz 6'daki dogfooding iddiası kendi roadmap'iyle imkânsız

Faz 6 "bu noktadan sonra dogfooding başlar: P2P'nin kendi task'ları P2P ile
planlanır" diyor. Ama P2P bir Python CLI'dır ve ikinci teknoloji yığını
(Blueprint arayüzü) Faz 9'a kadar yok; Faz 7'nin referans yığını web+API.
P2P kendi task'larını planlayamaz, çünkü kendi türünde proje üretemez.

**Öneri:** Ya Faz 6'nın dogfooding cümlesini kaldır (planlama zinciri yine de
değerli), ya Faz 9'daki "ikinci yığın" hedefini **Python CLI** olarak sabitle
ve dogfooding'i Faz 9 sonrasına taşı. İkincisi daha güçlü: ikinci blueprint'in
neden var olduğu da kanıtlanır.

### M5 — S4 (determinizm) kriteri ölçülemez

`docs/00 §5` S4: "Aynı prompt + aynı seed → aynı task graph yapısı."
`claude -p` ve `gemini -p` seed kontrolü sunmuyor; sunsalar bile örnekleme
determinizmi garanti edilmez. Ölçülemeyen bir başarı kriteri kriter değildir.

**Öneri:** S4'ü yapısal değişmezlerle değiştir: aynı prompttan üretilen üç
graph'ta da (a) çevrim yok, (b) her MUST kapasitesi kapsanmış, (c) paralel
çiftler disjoint, (d) kritik yol uzunluğu ±1 içinde. Bunlar mekanik olarak
kontrol edilebilir ve gerçekten önemsediğimiz şey zaten bu.

### M6 — Kota tükenmesinin çalışma zamanı davranışı tanımsız

`docs/02 §8` `daily_runs` bütçesi tanımlıyor, `docs/04 §5` `p2p doctor`'ın
kotayı "mümkünse" kontrol ettiğini söylüyor. Koşunun ortasında kota biterse ne
olur? Abonelik tabanlı iki runtime kullanan bir sistemde bu **istisna değil,
beklenen** durumdur.

**Öneri:** Ayrı hata sınıfı (`QUOTA`), fix döngüsüne girmez, task `PAUSED`
olur (yeni durum), `escalation` haritasındaki alternatif runtime'a düşülür, o
da yoksa proje `SUSPENDED` olur ve `p2p resume` ile devam eder. `PAUSED`,
`ESCALATED`'dan farklıdır: insan kararı değil, zaman gerektirir.

### M7 — Referans sözleşme, agent'ın kendi çıktısını yazmasını yasaklıyor

`docs/02 §2.2` örneğinde `forbidden_paths` içinde `.p2p/**` var. Ama agent
sonucunu `.p2p/runs/<run_id>/result.json`'a, ACR'ını `.p2p/acr/`'a yazmak
zorunda (`GEMINI.md §2`, §8). Kural olarak `forbidden`, `allowed`'ı eziyor
(`docs/02 §2` tablosu) — yani örnek sözleşme, agent'ın rapor vermesini
yasaklıyor.

**Öneri:** `result_path` ve `acr_path` `TaskContract`'ta birinci sınıf alan
olsun ve yol politikasından **muaf** tutulsun; `forbidden_paths` bunları
hiçbir zaman kapsamaz. Referans örneği düzelt.

---

## Minor Issues

- **`seq` monotonluğu:** `docs/02 §7` olay `seq`'inin monoton arttığını
  söylüyor; `docs/03 §2.5` dört paralel worker'a izin veriyor. Tek yazar kuralı
  bunu çözüyor ama yazıcının kilitlenmesi gerektiği hiçbir yerde yazmıyor.
- **Resume, yarım yazılmış dosyaya bir deneme harcıyor:** `docs/03 §6`,
  değişiklik varsa `VERIFYING`'e geçiyor. Süreç dosya yazımının ortasında
  öldüyse bu kesin bir `FAIL` ve boşa giden bir attempt. Resume sonrası ilk
  doğrulama denemesi sayaçtan düşülmesin.
- **Worktree başına bağımlılık dizini:** `ADR-006` bunu "Faz 3'te ele alınacak
  detay" diye erteliyor ama Faz 3'ün çıkış kriterinde yok. Dört paralel
  worktree'de dört `node_modules`, ilk gerçek koşuda hissedilir.
- **İsim çakışması:** `docs/adr/` (P2P'nin kararları) ile `.p2p/docs/adr/`
  (üretilen ürünün kararları) aynı isimde; `prompts/02` ikincisine yazıyor.
  Bir agent'ın karıştırması muhtemel — farklı adlandır.

---

## Open Questions

Hiçbir belgenin cevaplamadığı, uygulayıcının kesinlikle karşılaşacağı sorular:

1. **`estimated_size: L` olan task'ı kim böler?** `docs/02` "bölünmelidir",
   `prompts/03` "zamanlanamaz" diyor. Otomatik mi, mimar agent'a mı geri gider,
   insana mı? Mekanizma yok.
2. **`gates.yaml`'ı kim üretir?** `docs/05 §6` deklaratif kapı tanımını
   gösteriyor ama üretilen projede bunu kimin yazdığı belirsiz: blueprint mi,
   mimar agent mı, orchestrator mı?
3. **Merge sonrası regresyon kırmızıysa hangi task suçlu?** `docs/05 §8`
   regresyonu tanımlıyor ama birleştirilmiş üç task'tan hangisinin geri
   alınacağına dair kural yok.
4. **Bir task birden fazla capability gerektiriyorsa?** `TaskContract.capability`
   tekil. Migration + backend gerektiren bir task nasıl yönlendirilir?
5. **`WARN` biriktiğinde ne olur?** Teknik borç kaydediliyor ama hiçbir eşik
   `WARN` sayısını yayın kapısına bağlamıyor. Sonsuza kadar birikebilir.

---

## What is over-engineered

Silinmesi veya ertelenmesi önerilenler — hepsi v1'in taşımadığı ağırlık:

| Ne | Nerede | Neden |
|---|---|---|
| **Mutasyon örneklemesi** | `docs/05 §7` | Kendi başına bir altyapı projesi. "Her AC'nin `test_ref`'i var mı" kontrolü aynı riskin çoğunu bedavaya kapatıyor. Faz 9+ |
| **Ollama runtime** | `docs/04 §3.3`, `docs/09 §5` | Üçüncü bir runtime bağımlılığı, commit mesajı taslağı için. `docs/07 §3` zaten önemli satırları orchestrator'ın doldurduğunu söylüyor. Değeri ≈ 0 |
| **`a11y` kapısı** | `docs/05 §2` | v1'de üretilen ürünün erişilebilirliği kabul kriteri değil. Faz 8'e değil, Faz 9+'a |
| **ACR `DEFERRED` verdict'i** | `docs/03 §4`, `prompts/07` | Üç yollu karar, iki yollunun yapamadığı ne yapıyor? "Geçici çözümle devam" pratikte `REJECTED` + not |
| **`escalation.on_repeated_failure`** | `docs/02 §8` | Zarif ama kanıtlanmamış. Faz 5'te sabit routing ile başla, gerçek veriyle ekle |
| **`SKIPPED` kapı durumu** | `docs/05 §5` | `DONE` gerekçesine yazılıyor ama hiçbir yerde okunmuyor. Ya bir eşiğe bağla ya kaldır |

---

## Doğru olan ama yanlış görünen kararlar (savunma)

Bunlar "gereksiz karmaşıklık" diye işaretlenmeye açık; işaretlenmemeli:

- **Worktree izolasyonu (`ADR-006`).** Disk maliyeti gerçek, ama alternatifi
  (paylaşılan ağaç + kilit) sessiz veri bozulmasıdır. Karmaşıklık doğru yere
  harcanmış.
- **SQLite yerine JSONL (`ADR-002`).** "İlkel" görünür. Tek yazar +
  append-only, paralel süreçlerde kilit çekişmesini yapısal olarak yok eder;
  `tail -f` ile izlenebilirlik hata ayıklamada ölçülemez değerde.
- **`contract` kapısı (`docs/05 §4`).** Fazladan bir kapı gibi durur; aslında
  frontend/backend paralelliğini mümkün kılan **tek** şeydir. Silinirse
  paralellik yanılsamaya döner.
- **`smoke` kapısı (`docs/05 §3`).** "Testler zaten var" itirazına karşı:
  testler mock'lu dünyada koşar, başlatma yolu hiç denenmez. v1'in en yüksek
  getirili tek maddesi.
- **ACR mekanizması (`ADR-007`).** Gecikme getirir; karşılığında mimari
  erozyonunu görünür kılar. Ölçekte alternatifi yok.
- **Tek yazar kuralı (`ADR-003`).** Adapter'a fazladan bir okuma adımı ekler;
  karşılığında agent'ın kendi başarısını ilan etmesini imkânsız kılar.

---

## Karar Kaydı (2026-09-10)

Bulgular gözden geçirildi ve aşağıdaki kararlar verilip belgelere işlendi.

| # | Karar | Nereye işlendi |
|---|---|---|
| **C1** | Agent'a **dar kapsamlı kabuk izni**: yalnızca test koşucusu, `--policy` ile sabit. Onay istemi = anında `ERROR`, zaman aşımı beklenmez | `ADR-008` (yeni), `docs/04 §2, §3.2`, `docs/06 §6`, `GEMINI.md §2`, `prompts/04` |
| **C2** | **Kapılar kalır, vaat düzelir.** Ürün "tek promptla, iki onay noktasıyla doğrulanmış ürün" | `docs/00 §1, §5 (S1)`, `docs/03 §5` |
| **C3** | Kaynak gerektiren kapılar (`smoke`, `integration`, `migration`, `e2e`) **global semaforla serileştirilir**; hafif kapılar paralel kalır | `docs/03 §2.5` (yeni), `docs/05 §6` (`isolation` alanı) |
| **C4** | `AgentResult` **tamamlayıcı**; durum git + kapılar + result.json'dan türetilir. Bilinmeyen alanlar loglanıp atılır | `docs/02 §3`, `docs/04 §2` |
| **C5** | `WORKSPACE_BOOTSTRAP` aşaması eklendi, Faz 3'ün çıkış kriteri oldu | `docs/08 Faz 3` |
| **M1** | Mimar agent `.p2p/tasks/` yazmaz; taslağı `.p2p/docs/task-graph/`'a üretir, orchestrator doğrulayıp yerleştirir | `CLAUDE.md §2` |
| **M2** | Kabul kriteri testleri **her zaman** ayrı `TEST-` task'ı; uygulayıcının `forbidden_paths`'inde `tests/**` | `docs/02 §2.2`, `docs/05 §7`, `prompts/03` |
| **M3** | CI v1'de **harici doğrulamadır**, `DONE` koşulu değildir. Ayrışma riski, kapıların tek deklaratif tanımdan üretilmesiyle kapatılır. Karar v2'ye ertelendi | `docs/07 §5` |
| **M4** | Faz 6'daki dogfooding iddiası kaldırıldı; Faz 9'un ikinci Blueprint'i **Python CLI** olarak sabitlendi | `docs/08 Faz 6, Faz 9` |
| **M5** | S4 ölçülebilir yapısal değişmezlerle değiştirildi (çevrim, kapsama, disjointlik, kritik yol ±1) | `docs/00 §5` |
| **M6** | `QUOTA` hata sınıfı + `PAUSED` durumu; sayaç tüketilmez, alternatif runtime'a düşülür, yoksa `SUSPENDED` | `docs/02 §4, §8`, `docs/03 §3.4` (yeni) |
| **M7** | `result_path` / `acr_path` birinci sınıf alan ve yol politikasından muaf | `docs/02 §2, §2.2`, `GEMINI.md §2` |
| **Minor** | `seq` yazım kilidi · resume'un ilk denemesi sayaçtan düşülmez · worktree bağımlılık cache'i Faz 3'e · `.p2p/docs/decisions/` (isim çakışması giderildi) | `docs/02 §7`, `docs/03 §6`, `docs/08 Faz 3`, `prompts/02` |

### Silinenler (fazla mühendislik)

| Ne | Nereye taşındı |
|---|---|
| Mutasyon örneklemesi | Faz 9+. Yerine "her AC'nin `test_ref`'i var mı" + tautoloji taraması |
| Ollama runtime | Tamamen kaldırıldı — routing, adapter, roadmap, workflow |
| `a11y` kapısı | Faz 9+. Faz 8'den ve kapı tablosundan çıkarıldı |

### Kasıtlı olarak **korunanlar**

`ACR DEFERRED` verdict'i, `routing.escalation.on_repeated_failure` ve
`SKIPPED` kapı durumu — gözden geçirmede silinmesi önerilmişti, kullanıcı
kararıyla korundu.

### Hâlâ açık

- `docs/10-open-decisions.md`: **D1** (P2P'nin dili) ve **D2** (referans yığın)
  — Faz 1'i bloke ediyor
- Bu belgedeki 5 açık soru: `L` task'ı kim böler · `gates.yaml`'ı kim üretir ·
  regresyon kırmızıysa hangi task suçlu · çoklu capability · `WARN` birikimi

---

## Kapsam Genişlemesi (2026-09-10, ikinci tur)

Bu gözden geçirmeden sonra ürün tanımı genişletildi. Değişiklik iki eksende:

**1. Tam otonomi.** Kullanıcı prompt verir; orchestrator döngüyü kendisi
çevirir (`docs/03 §7`). Bu, C2 kararını **revize eder**: sabit dört kapı yerine
risk tabanlı, seviyeli otonomi (ADR-010). `high` risk task'ları hiçbir seviyede
otomatik geçmez; otomatik verilen her karar `decided_by=default` kaydedilir.

**2. Model-bağımsızlık.** Claude + Gemini sabit iki runtime değil, ilk iki
`Connection`. Yedi kavram ayrıldı, yönlendirme capability tabanlı hâle geldi
(ADR-009, `docs/04` yeniden yazıldı).

### Bu turda ortaya çıkan yeni bulgular

| # | Bulgu | Çözüm |
|---|---|---|
| **N1** | Doğrulanmamış vendor iddiaları mimariye girme riski taşıyordu (Antigravity SDK, Claude Agent SDK, model adları) | `docs/11` doğrulama borcu belgesi; hiçbir faz `DOĞRULANMADI` bir maddeye dayanamaz |
| **N2** | PyPI'daki `antigravity` paketi Google'ın SDK'sı **değil** — xkcd şakası paketi. Uygulayıcı agent bunu sessizce kurabilirdi | `docs/11 V3`'te açık uyarı |
| **N3** | Router uygun bağlantı bulamazsa otonom koşu sessizce durabilirdi | `UNROUTABLE` durumu + somut hata mesajı (`docs/04 §5`) |
| **N4** | Otonom döngünün bitmeme ihtimali | Dört meşru çıkış + "ilerleme yok" tespiti (`docs/03 §7.2`) |
| **N5** | Çok bağlantılı kurulumda yeni saldırı yüzeyi (kimlik karışması, kötücül gateway, denetimsiz otonomi) | T11-T13 tehditleri + `docs/06 §9, §10` |
| **N6** | Abonelik otomasyonunun lisans durumu teknik olarak çözülemez | `automation_policy` alanı: sistem karar vermez, sessiz de kalmaz (`docs/04 §3`) |

### Roadmap'e etkisi

Faz 0 artık **runtime fizibilitesi**: üç test, üçüncüsü otonom döngü MVP'si.
Faz 5 **otonom orchestrator** oldu. Faz 9, model-bağımsızlığın kanıtlandığı
faz — üçüncü ve dördüncü adapter eklenerek.

`docs/08 Faz 0`'ın "auto_edit kabuk komutunu engelliyor mu" maddesi ADR-008'e
göre düzeltildi; "Dogfooding Faz 6'da başlar" prensibi Faz 9 sonrasına taşındı.
Baseline commit'teki iki bilinen kalıntı böylece kapandı.
