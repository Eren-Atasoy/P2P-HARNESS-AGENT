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

## 5. İnsan karar kapıları

Bunlar hız kaybı değil, ürünün kalite tanımıdır. v1'de **dört** zorunlu kapı:

| # | Kapı | Ne zaman | Neden otomatik olamaz |
|---|---|---|---|
| G1 | **Belirsizlik çözümü** | Discovery sonrası | Ürün kararı; yanlış varsayım tüm ağacı çürütür |
| G2 | **Mimari onayı** | Architecture sonrası | Geri dönüşü en pahalı karar |
| G3 | **Kapsam onayı** | Task graph üretildikten sonra | Maliyet burada belirlenir |
| G4 | **Yayın onayı** | Regresyon sonrası | Dışa dönük eylem |

Bu dört kapı, `docs/00 §1`'deki vaadin parçasıdır: ürün "tek promptla ürün"
değil, "tek promptla, **iki zorunlu onayla** doğrulanmış ürün"dür. G1 ve G3
`--yes` ile atlanabildiği için zorunlu sayı ikidir (G2, G4). (C2)

Ek olarak `human_approval=true` olan tek tek task'lar ve tüm `ESCALATED`'lar.

`--yes` bayrağı G1 ve G3'ü atlayabilir (varsayılanları kullanır, `Decision`
kaydına `decided_by=default` yazar). **G2 ve G4 atlanamaz.**

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
