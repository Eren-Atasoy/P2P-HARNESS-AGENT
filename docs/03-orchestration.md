# 03 — Orkestrasyon

## 1. Task durum makinesi

Bir task'ın alabileceği durumlar ve geçişler. Tanımsız geçiş yoktur; her geçiş
bir olay yazar.

```
                  ┌─────────┐
                  │ PENDING │  bağımlılıklar tamamlanmadı
                  └────┬────┘
                       │ tüm depends_on = DONE
                  ┌────▼────┐
        ┌────────►│  READY  │  zamanlanabilir
        │         └────┬────┘
        │              │ scheduler seçti
        │         ┌────▼─────────┐
        │         │ IMPLEMENTING │  agent çalışıyor
        │         └────┬─────────┘
        │              │
        │       ┌──────┼────────────────┬──────────────┐
        │       │completed          blocked        failed
        │       │                       │              │
        │  ┌────▼──────┐          ┌─────▼────┐   ┌─────▼─────┐
        │  │ VERIFYING │          │ BLOCKED  │   │  FAILED   │
        │  └────┬──────┘          │  (ACR)   │   └─────┬─────┘
        │       │                 └─────┬────┘         │
        │  ┌────┼─────┬──────┐          │              │
        │  PASS │ FAIL │ ERROR│          │              │
        │       │      │      │          │              │
        │  ┌────▼───┐  │  ┌───▼──────┐   │              │
        │  │REVIEW- │  │  │ESCALATED │◄──┴──────────────┘
        │  │  ING   │  │  └──────────┘   (insan gerekli)
        │  └────┬───┘  │
        │       │      │
        │  ┌────┼──────┼───────┐
        │ APPR. │ CHANGES  REJECTED
        │       │ REQUESTED  │
        │       │      │     │
        │  ┌────▼───┐  │     │
        │  │APPROVED│  │     │
        │  └────┬───┘  │     │
        │       │      │     │
        │       │  attempt < max ?
        └───────┼──────┴─────┘  evet → READY (fix modu, attempt+1)
                │                hayır → ESCALATED
           ┌────▼────┐
           │ MERGING │  worktree → integration dalı
           └────┬────┘
           ┌────▼────┐
           │  DONE   │
           └─────────┘
```

### Geçiş kuralları

| Kural | Gerekçe |
|---|---|
| `IMPLEMENTING → VERIFYING` zorunlu geçiş | Doğrulama atlanamaz. "Bu küçük bir değişiklik" istisnası yoktur |
| `VERIFYING(ERROR) → ESCALATED` | Araç/ortam hatası fix döngüsüne sokulmaz; model kendi ortamını tamir etmeye çalışıp durumu kötüleştirir |
| `REJECTED` geri sayaç tüketir | Aksi hâlde sonsuz döngü |
| `BLOCKED`'dan çıkış yalnızca ACR çözümüyle | Uygulayıcı kendi engelini kaldıramaz |
| `DONE`'dan geri dönüş yok | Yeni ihtiyaç → yeni task. Task'lar değişmezdir |

## 2. Zamanlama ve paralellik

### 2.1 Dalga hesabı

Task graph yönlü çevrimsiz olmak zorundadır (planlama aşamasında doğrulanır;
çevrim varsa plan reddedilir, yeniden planlanır).

Scheduler her turda: `READY` durumundaki task'ları alır, **çakışmayanları**
aynı dalgaya koyar.

### 2.2 Çakışma tanımı

İki task paralel çalışabilir ⟺ `allowed_paths` glob kümeleri kesişmiyorsa.

```
API-001  allowed: backend/api/**, tests/api/**
UI-001   allowed: frontend/**,    tests/ui/**
                                        → kesişim yok → PARALEL

API-001  allowed: backend/**
DB-002   allowed: backend/models/**
                                        → kesişim var → SIRALI
```

Bu, "bağımlılık yok ama aynı dosyaya yazıyorlar" tuzağını kapatır.
Bağımlılık grafiği tek başına yeterli **değildir**.

### 2.3 İzolasyon: worktree

Paralel çalışan her task kendi `git worktree`'sinde çalışır:

```
.p2p/wt/API-001/   → dal: p2p/task/API-001
.p2p/wt/UI-001/    → dal: p2p/task/UI-001
```

Neden ayrı dizin, ayrı dal:

- İki agent aynı dosya sistemini fiziksel olarak paylaşmaz → yarış yok
- Bir task başarısız olursa worktree silinir, ana ağaç temiz kalır
- Merge çakışması `git`'in çözdüğü bilinen bir problem hâline gelir

### 2.4 Birleştirme sırası

Deterministik olmalı: **task id alfabetik sırası**. Rastgele sıra, aynı girdiden
farklı sonuç üretir ve hata ayıklamayı imkânsızlaştırır.

Merge çakışması olursa:

1. Otomatik çözüm **denenmez**
2. `MERGE_CONFLICT` olayı yazılır
3. Çakışan task `ESCALATED` olur, mimar agent'a çakışma özeti verilir

Otomatik çakışma çözümü v1 kapsamı dışıdır; sessizce yanlış kod birleştirmek,
insana sormaktan çok daha pahalıdır.

### 2.5 Kaynak kapıları serileştirilir (C3)

Worktree, **dosya** izolasyonu sağlar; **çalışma zamanı** izolasyonu sağlamaz.
`smoke` ve `integration` kapıları docker konteyneri kaldırır: iki worktree aynı
anda çalışırsa aynı port, aynı konteyner adı, aynı hacim çakışır. En tehlikeli
belirti çökme değil, **yanlış PASS**'tir: task A'nın smoke testi, task B'nin
ayakta kalan konteynerine bağlanıp yeşil verir.

**v1 kararı:** kaynak gerektiren kapılar global bir semaforla **sırayla**
çalışır. Kod yazımı ve hafif kapılar (lint, typecheck, unit) paralel kalır.

```
kaynak gerektiren kapılar: smoke, integration, migration, e2e
paralel çalışabilenler:    policy, format, lint, typecheck, build, unit, contract
```

Bedeli: bu kapılarda paralellik yok, toplam süre uzar. Karşılığı: kesin
doğruluk ve hata ayıklanabilirlik. Dinamik port + compose proje adı ile gerçek
paralellik, ölçülmüş bir darboğaz hâline geldiğinde eklenir — önce değil.

### 2.6 Eşzamanlılık sınırı

```
max_parallel = min(
    routing.budget_headroom(runtime),   # kota
    cpu_count // 2,                     # kapılar da CPU yiyor
    4                                   # sabit üst sınır
)
```

Sabit üst sınır 4: daha fazlası, hata ayıklanabilirliği ve kota tüketimini
kötüleştirir, hızı ise doğrusal artırmaz (kapılar seri çalışır).

## 3. Onarım döngüsü

Bir task başarısız olduğunda, "tekrar dene" demek yeterli değildir. Hatanın
**sınıflandırılması** ve buna göre farklı bir strateji seçilmesi gerekir.

| Sınıf | Belirti | Aksiyon |
|---|---|---|
| `SYNTAX` | derleyici/parser hatası | Aynı runtime, dar kapsamlı fix promptu, sadece hatalı dosyalar bağlam olarak |
| `TEST_FAIL` | test kırmızı | Aynı runtime, fix promptuna **başarısız test çıktısı** eklenir |
| `CONTRACT` | API/şema sözleşme ihlali | Sözleşme belgesi bağlama eklenir; ısrar ederse ACR |
| `POLICY` | izinsiz yol değişikliği | Değişiklik geri alınır, task yeniden başlar, uyarı promptu eklenir |
| `ENV` | araç yok, bağımlılık kurulamıyor | **Fix döngüsüne girmez** → ESCALATED |
| `ARCH` | agent mimari sorunu bildirdi | ACR açılır → mimar agent |
| `QUOTA` | runtime kotası bitti | Fix döngüsüne **girmez** → `PAUSED` (bkz. §3.4) |
| `UNKNOWN` | sınıflandırılamadı | 1 kez daha dene, sonra ESCALATED |

### 3.1 Fix promptunun bağlamı

Fix turunda agent'a **tüm görev yeniden anlatılmaz**. Verilenler:

1. Orijinal `TaskContract`
2. Kendi önceki `AgentResult.summary`'si
3. Başarısız kapı çıktısı (kırpılmış: ilk 50 + son 50 satır)
4. Varsa `ReviewResult.findings`
5. Açık talimat: *"Sadece bu bulguları gider. Başka refactor yapma."*

Bu son madde kritik. Serbest bırakılan bir fix turu, çalışan kodu bozar —
gözlenen en yaygın regresyon kaynağı budur.

### 3.2 Sonsuz döngü savunması — üç katman

1. **Sayaç:** `attempt >= max_attempts` → ESCALATED
2. **İlerleme kontrolü:** ardışık iki turda aynı kapı, aynı hata imzasıyla
   düşerse (`hash(failures)` eşit) → sayacı beklemeden ESCALATED.
   Aynı hatayı üçüncü kez üretmesini beklemek zaman ve kota israfıdır.
3. **Bütçe:** task başına toplam duvar-saati / çalıştırma sayısı üst sınırı

### 3.4 Kota tükenmesi — `PAUSED` (M6)

İki abonelik tabanlı runtime kullanan bir sistemde kotanın koşu ortasında
bitmesi istisna değil, **beklenen** durumdur.

`PAUSED`, `ESCALATED`'dan farklıdır: insan kararı gerektirmez, **zaman**
gerektirir. Sıra:

1. `QUOTA` hatası → task `PAUSED`, deneme sayacı **tüketilmez**
2. `routing.yaml`'daki `escalation` haritasında alternatif runtime varsa
   task oraya yönlendirilip `READY` olur
3. Alternatif yoksa ve bekleyen tüm task'lar aynı runtime'a bağlıysa
   proje `SUSPENDED` olur
4. `p2p resume` kaldığı yerden devam eder

`p2p status`, `PAUSED` task'ları "kota bekliyor — tahmini sıfırlanma: …"
biçiminde ayrı gösterir. Kullanıcının "sistem çöktü mü" diye tahmin etmesi
gereken hiçbir durum olmamalı.

### 3.5 Escalation ne demek

`ESCALATED` = **insan gerekli**. Sistem durmaz; o task'ı `BLOCKED` sayıp
bağımsız dalları çalıştırmaya devam eder ve `p2p status` çıktısında
"3 task insan kararı bekliyor" der.

### Yönlendirme: `p2p steer`

Escalate olmuş bir task'a insan müdahalesi, sohbet değil **kayıt** olmalıdır:

```
p2p steer AUTH-003 "Oturum yenilemesi refresh token ile değil,
                    kısa ömürlü access token + yeniden giriş ile olacak."
```

Bu metin bir `Decision` kaydı olur (`decided_by=human`), task sözleşmesinin
notlarına eklenir ve sonraki fix turunda bağlama girer. Prompt geçmişinde
kaybolmaz; altı ay sonra "bu neden böyle" sorusunun cevabı olur.

Ekran görüntüsü, log parçası veya beklenen çıktı örneği de aynı şekilde
eklenebilir; hepsi task'ın artifact'ı olarak saklanır.

Otomatik olarak bir sonraki insana teslim edilen paket:

- Task sözleşmesi
- Tüm denemelerin özeti (ne denendi, ne oldu)
- Son hata çıktısı
- Mimar agent'ın "muhtemel kök neden" analizi (tek çağrı)
- Önerilen 2-3 seçenek

## 4. Architecture Change Request (ACR)

Uygulayıcı agent mimarinin yanlış/eksik olduğunu düşünürse **kendi başına
düzeltemez**. Bu mekanizma, projenin en değerli tek fikridir: mimari bütünlüğü
ölçekte koruyan tek şeydir.

```
gemini  ── "şema bu ilişkiyi desteklemiyor"
   │
   ▼
.p2p/acr/ACR-004.md yazar, outcome=blocked döner
   │
   ▼
task BLOCKED, ACR_OPENED olayı
   │
   ▼
orchestrator → claude (mimar) → ACR'ı değerlendirir
   │
   ├─ REJECTED  → gerekçe task notlarına eklenir, task READY (fix modu)
   ├─ ACCEPTED  → mimari belge güncellenir + YENİ task açılır
   │              (mevcut task ona bağımlı hâle gelir)
   └─ DEFERRED  → teknik borç kaydı, task geçici çözümle devam eder
```

ACR şablonu (`prompts/` altında):

```markdown
# ACR-<n>: <tek satır>
- Task: <id>
- Çelişen belge/karar: <yol veya ADR no>
- Gözlem: (koda dayalı, spekülasyon değil)
- Neden mevcut mimariyle çözülemiyor:
- Önerilen değişiklik:
- Etkilenen bileşenler:
- Geçici çözüm mümkün mü: evet/hayır + maliyeti
```

## 5. Otonomi ve risk tabanlı insan kapıları

Ürünün vaadi tam otonomi (`docs/00 §1`). Ama "her karar makineye" ile "her
karar insana" arasındaki doğru nokta, **riske göre değişir**. Bir lint
düzeltmesiyle bir üretim veritabanı migration'ı aynı muameleyi görmemeli.

### 5.1 Task risk seviyeleri

Risk, mimar agent'ın keyfi takdiri değil; task'ın **neye dokunduğundan**
türetilir ve doğrulanabilir bir kuraldır:

| Seviye | Tetikleyici | Örnek |
|---|---|---|
| `low` | Yalnızca sunum, biçim, belge, iç refactor | lint düzeltme, UI aralıkları, docstring |
| `medium` | İş mantığı, veri şeması, dış entegrasyon | yeni uç, şema alanı, API istemcisi |
| `high` | Kimlik doğrulama/yetkilendirme, ödeme, sır, yıkıcı migration, dağıtım | auth akışı, faturalama, `DROP COLUMN` |

Kural: bir task `high` risk kategorisindeki dosyalara veya kavramlara
dokunuyorsa risk **yükseltilir, asla düşürülmez**. Planlayıcı bunu düşük
gösteremez.

### 5.2 Otonomi seviyeleri

```
p2p run --autonomy supervised | guarded | full
```

| Seviye | Proje kapıları | Task kapıları | Kime |
|---|---|---|---|
| `supervised` | G1 G2 G3 G4 | `medium` + `high` | İlk kullanım, öğrenme |
| `guarded` **(varsayılan)** | G2 G4 | `high` | Günlük kullanım |
| `full` | — | `high` | Gece koşusu, güvenilen alan |

Proje kapıları:

| # | Kapı | Ne zaman |
|---|---|---|
| G1 | Belirsizlik çözümü | Discovery sonrası |
| G2 | Mimari onayı | Architecture sonrası |
| G3 | Kapsam onayı | Task graph sonrası |
| G4 | Yayın onayı | Regresyon sonrası |

### 5.3 `full` seviyesinde bile kapatılamayan tek şey

`high` risk task'ları. Gerekçe: bunlar geri alınamayan veya para/veri kaybettiren
eylemlerdir ve modelin özgüveni, riskin gerçek büyüklüğüyle ilişkili değildir.

`full` seviyesinde G2 ve G4 **otomatik onaylanır**, ancak sessizce değil:
her biri `Decision` kaydına `decided_by=default` olarak yazılır ve
`p2p status` bunları ayrıca listeler. Kullanıcı, sabah kalktığında hangi
kararların kendisi adına verildiğini tek ekranda görür.

> Bu, `docs/00 §1`'deki vaadin tam karşılığıdır: sistem uçtan uca otonom
> çalışabilir, ama **hangi kararların insansız verildiği asla gizlenmez.**

### 5.4 Yönlendirilemeyen task: `UNROUTABLE`

Router hiçbir uygun bağlantı bulamazsa (`docs/04 §5`) task `ESCALATED` olur.
Bu, otonom bir koşunun sessizce durmasının en olası nedenidir; mesaj bu yüzden
somut olmak zorundadır: hangi yetenek eksik, hangi bağlantı eklenmeli.

## 6. Kurtarılabilirlik

Herhangi bir anda `Ctrl+C` veya çökme:

1. Olay günlüğü diskte, son tamamlanmış olaya kadar tutarlı
2. `p2p resume` → state yeniden türetilir
3. `IMPLEMENTING` durumunda kalmış task'lar: worktree'si incelenir
   - Değişiklik yoksa → `READY`
   - Değişiklik varsa → `VERIFYING` (yarım işi çöpe atma, doğrula).
     Bu ilk doğrulama denemesi **sayaçtan düşülmez**: süreç dosya yazımının
     ortasında ölmüş olabilir ve bu, agent'ın hatası değildir.
4. Yarım kalmış alt process'ler run_id ile tespit edilip temizlenir

Bu, uzun süren üretimlerde (saatler) pazarlık konusu olmayan bir özelliktir.

---

## 7. Otonom yürütme döngüsü

Orchestrator'ın `plan → implement → review` şeklinde doğrusal bir akışı yoktur.
Durum makinesini ilerleten, kapanana kadar dönen tek bir döngüsü vardır.

```
while proje_bitmedi:

    1. ready      = graph.hazır_taskları()        # bağımlılıklar tamam
    2. dalga      = scheduler.paketle(ready)      # allowed_paths disjoint
    3. atamalar   = router.seç(dalga)             # capability + risk + policy
                    ↳ uygun bağlantı yoksa → UNROUTABLE → escalate
    4. sonuçlar   = runtime.paralel_çalıştır(atamalar)
    5. kapılar    = verification.çalıştır(sonuçlar)
                    ↳ kaynak kapıları semaforla serileştirilir (§2.5)
    6. sınıflar   = failure.sınıflandır(kapılar)
    7. incelemeler= review.çalıştır(geçenler)
    8. yeni_task  = repair.planla(sınıflar + incelemeler)
    9. escalate   = policy.kontrol(sayaçlar, bütçe, risk)
   10. state.uygula(olaylar)                      # tek yazar

    if hiçbir_ilerleme_yok:  break                # §7.2
```

Kullanıcı `p2p run` der ve gider. Sistem gece boyunca task → kod → test →
inceleme → düzeltme → yeniden test → sonraki task döngüsünü sürdürür.

### 7.1 Döngü değişmezleri

Her turda doğru kalması gereken şeyler; ihlali bir hatadır:

1. Her task tam olarak bir durumda
2. Çalışan iki task'ın `allowed_paths`'i kesişmiyor
3. Her durum geçişi bir olay yazdı
4. Hiçbir agent state'e yazmadı (ADR-003)
5. Aktif çalıştırma sayısı ≤ her bağlantının `limits.concurrency` toplamı

### 7.2 Döngü nasıl biter

Dört meşru çıkış var. Beşincisi yok — sonsuz dönen bir döngü hatadır.

| Çıkış | Koşul |
|---|---|
| **Tamamlandı** | Tüm task'lar `DONE`, regresyon yeşil |
| **Kilitlendi** | `READY` task yok, ama `PENDING` var → bağımlılık grafiği hatalı veya hepsi bloke |
| **İnsan bekliyor** | Çalıştırılabilir hiçbir task yok, ≥1 `ESCALATED` / kapı bekliyor |
| **Bütçe doldu** | Süre veya çalıştırma bütçesi aşıldı |

**İlerleme yok tespiti:** bir turda hiçbir olay yazılmadıysa ve hiçbir yeni
task hazır hâle gelmediyse döngü kendini durdurur. Bu, "sistem çalışıyor
görünüyor ama hiçbir şey olmuyor" durumunun tek savunmasıdır — ve otonom
sistemlerde en pahalı başarısızlık biçimi budur.

### 7.3 Kısmi başarı meşru bir sonuçtur

Otonom bir koşu, "her şey oldu" veya "hiçbir şey olmadı" ile bitmek zorunda
değil. Sabah kullanıcının göreceği tipik çıktı:

```
p2p status

  DONE          14 task
  ESCALATED      2 task   (AUTH-003: 3 denemede geçemedi
                           E2E-001 : UNROUTABLE — 'browser' sağlayan bağlantı yok)
  PAUSED         1 task   (kota — claude-pro, ~06:00'da sıfırlanır)
  otomatik karar 2 adet   (G2, G4 — decided_by=default)

  ürün ayakta:  http://localhost:3000    (14/17 kabul kriteri doğrulandı)
```

Bu ekran ürünün kendisidir: ne yapıldığı, ne yapılamadığı ve **kimin adına
hangi kararın verildiği** tek bakışta görünür.

---

## 8. Retrospektif — tekrarlayan hatayı kalıcı kurala çevirmek

Sistemin zamanla iyileşmesinin tek meşru yolu budur. Bir agent'ın "daha iyi
öğrenmesi" beklenemez; öğrenen şey **sistemin kendisidir**.

### 8.1 Sinyal olay günlüğünden gelir, insan hafızasından değil

`p2p retro` olay günlüğünü tarar ve tekrar eden kalıpları çıkarır:

| Kalıp | Eşik | Ne anlama gelir |
|---|---|---|
| Aynı kapı + aynı hata imzası, farklı task'larda | 3 kez | Sistemik bir üretim hatası |
| Aynı inceleme bulgusu kategorisi | 3 kez | Kural eksik veya belirsiz |
| Aynı capability'de ardışık escalation | 2 kez | Yanlış yönlendirme veya yetersiz bağlantı |
| Aynı temada ACR | 2 kez | Mimari belge eksik veya yanlış |

Tespit **deterministiktir** — hata imzası karşılaştırması, model yargısı değil.
Yalnızca *öneri metnini* yazmak için bir model çağrılır.

### 8.2 En önemli kural: önce kapı, sonra prompt

Bir hata üçüncü kez tekrarladığında iki seçenek vardır:

| Seçenek | Etkisi |
|---|---|
| `GEMINI.md`'ye bir cümle eklemek | Modelden **hatırlamasını** ister. Olasılıksal |
| Bir lint kuralı / kapı eklemek | Hatayı **mekanik olarak** yakalar. Kesin |

> **Tercih daima kapıdır.** Prompt'a eklenen kural, bağlam büyüdükçe silikleşir;
> bir lint kuralı her seferinde aynı şekilde çalışır. Bu, ADR-004'ün doğrudan
> devamıdır: kaliteyi ikna değil, mekanizma sağlar.

Prompt kuralı, yalnızca mekanik olarak yakalanamayan şeyler için kullanılır
(tasarım tercihi, kapsam disiplini, raporlama biçimi).

### 8.3 Çıktı

`p2p retro` bir **öneri** üretir, kendiliğinden değişiklik yapmaz:

```
RETRO  son 40 çalıştırma

  ×5  unit / AssertionError: hataya dönen yol test edilmemiş
      → ÖNERİ (kapı): coverage kapısına branch eşiği ekle
  ×4  review / HIGH: sahiplik kontrolü eksik (IDOR)
      → ÖNERİ (kapı): security kapısına çapraz-kiracı testi zorunluluğu
      → ÖNERİ (kural): TEST- task şablonuna çapraz-kiracı AC'si ekle
  ×3  ACR: veri modeli ilişki ifade edemiyor
      → ÖNERİ (belge): docs mimari şablonuna ilişki kardinalitesi bölümü
```

Kabul edilen öneriler kural dosyalarına veya kapı tanımlarına işlenir ve
`RETRO_APPLIED` olayı yazılır. Böylece "bu kural neden var" sorusunun cevabı
her zaman kayıtlıdır.

### 8.4 Neden otomatik uygulanmaz

Kural değişikliği, gelecekteki her çalıştırmayı etkiler. Yanlış bir kural,
tek bir hatalı task'tan çok daha pahalıdır — ve otonom bir sistemde etkisi
sessizce yayılır. Öneri üretimi otomatiktir; kabul, `medium` risk bir karardır.
