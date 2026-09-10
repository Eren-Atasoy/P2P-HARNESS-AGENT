# 12 — Tasarım Sistemi ve Görsel Kimlik

> Bu belge bir stil rehberi değil, **sözleşmedir.** `docs/02`'deki alan adları
> nasıl bağlayıcıysa buradaki token adları da öyledir. Uygulayıcı agent bunları
> yeniden adlandıramaz, "iyileştiremez"; itirazı varsa ACR açar (`ADR-007`).

**Kapsam:** iki ayrı UI yüzeyi (§2) ve ikisinin paylaştığı tek token katmanı.
**Bağlayıcı brief:** kullanıcı 2026-09-10'da görsel yönü sabitledi
(`PRODUCT.md` → Brand Commitments). Brief kazanır.

---

## 1. Görsel Kimlik ve Tasarım Felsefesi

### 1.1 Bakış açısı — bu neden bir Linear klonu değil

Brief, modern developer tool estetiğini (Linear · Vercel · Supabase · Raycast)
sabitliyor. Bu doğru karar: hedef kullanıcı bu dili zaten konuşuyor, öğrenme
maliyeti sıfır.

Ama bu aynı zamanda yazılım tarihinin en çok kopyalanan estetiği. Ondan
ayrışmak için bir eksen gerekiyor ve o ekseni ürünün kendi iddiası veriyor:

> **Otonomi şeffaflığı azaltmaz** (`PRODUCT.md` İlke 2).

Bunun görsel karşılığı **kanıt yoğunluğu**dur. Linear karmaşıklığı pürüzsüz
yüzeylerin arkasına saklar; bu arayüzün tersini yapması gerekir —
**karar soyağacını göstermek.**

| Kategori alışkanlığı | Bizim kuralımız |
|---|---|
| Durum = renkli nokta | Durum = bileşik kayıt: **hâl + kim karar verdi + neyle doğrulandı** |
| Başarı sessizdir | Otomatik verilen karar **görünür bir işaret taşır** |
| Sayı büyük gösterilir | Sayı **karşılaştırılabilir** gösterilir (tabular, hizalı) |
| İlerleme = yüzde çubuğu | İlerleme = **hangi kapının geçildiği**, adıyla |

Somut sonuç: bu sistemin imza öğesi bir renk veya animasyon değil,
**`decided_by=default` işareti** — kullanıcının yokluğunda verilmiş kararı
gösteren, göz ardı edilemeyen ama panik yaratmayan im (§2.A.4).

### 1.2 Tema — kategoriden değil, kullanım sahnesinden

Dark mode **birincil**, ama "geliştirici aracı koyu olur" diye değil.
Gerekçe kullanım sahnesi (`PRODUCT.md` → Operating Context): kullanıcı gece
başlattığı koşuya sabah dönüyor, terminalin yanındaki bir pencerede, kendi
makinesinde. Ortam ışığı düşük, oturum uzun.

Light mode **birinci sınıftır**: yüksek kontrastlı, temiz, gündüz ofis ışığında
okunabilir. İki tema ayrı ayrı tasarlanır; light, dark'ın `invert()`'i değildir.

Seçim sırası: kullanıcı tercihi → `prefers-color-scheme` → dark.

### 1.3 Renk — semantik token, ham değer değil

**Kural:** bileşen kodunda ham renk değeri (`#7C63F5`, `slate-900`) **yasaktır.**
Yalnızca semantik token kullanılır; ham değerler tek bir dosyada yaşar.

Bu, `ADR-009`'un görsel karşılığıdır: nasıl çekirdek kodda sağlayıcı adı
geçmiyorsa, bileşen kodunda da ham renk geçmez.

#### Katman (Background & Surface)

Derinlik gölgeyle değil, **yüzey açıklığıyla** kurulur. Dört katman, fazlası yok.

| Token | Dark | Light | Kullanım |
|---|---|---|---|
| `--bg-base` | `hsl(225 15% 7%)` `#0F1015` | `hsl(220 20% 99%)` `#FBFCFD` | Sayfa zemini |
| `--bg-surface` | `hsl(225 14% 10%)` `#161821` | `hsl(0 0% 100%)` `#FFFFFF` | Panel, kart, tablo |
| `--bg-raised` | `hsl(225 13% 14%)` `#1E2029` | `hsl(220 18% 97%)` `#F5F7FA` | Popover, seçili satır |
| `--bg-overlay` | `hsl(225 12% 18%)` `#272A35` | `hsl(220 16% 94%)` `#EEF1F5` | Modal, tooltip, palet |
| `--bg-inset` | `hsl(228 18% 5%)` `#0A0B0F` | `hsl(220 16% 95%)` `#F0F3F7` | Kod bloğu, log |

#### Kenarlık

| Token | Dark | Light |
|---|---|---|
| `--border-subtle` | `hsl(225 10% 20%)` `#2D303A` | `hsl(220 14% 92%)` `#E7EAF0` |
| `--border-default` | `hsl(225 10% 27%)` `#3C4049` | `hsl(220 13% 86%)` `#D6DAE3` |
| `--border-strong` | `hsl(225 9% 38%)` `#565A66` | `hsl(220 12% 72%)` `#B0B6C2` |

#### Metin

| Token | Dark | Light | Kontrast tabanı |
|---|---|---|---|
| `--text-primary` | `hsl(225 20% 96%)` `#F2F4F9` | `hsl(225 25% 11%)` `#161A24` | ≥ 12:1 |
| `--text-secondary` | `hsl(225 12% 74%)` `#B4B9C6` | `hsl(225 12% 38%)` `#565E6E` | ≥ 7:1 |
| `--text-tertiary` | `hsl(225 10% 58%)` `#8A90A0` | `hsl(225 10% 48%)` `#6E7585` | ≥ 4.5:1 |
| `--text-disabled` | `hsl(225 8% 42%)` `#646977` | `hsl(225 8% 62%)` `#969BA8` | yalnızca etkileşimsiz |

> `--text-tertiary` **tabandır**: gövde ve placeholder metin bunun altına inemez.
> Renkli yüzeyde ikincil metin **griden değil**, o yüzeyin tonundan türetilir.
> `G_UI_3` bunu mekanik doğrular.

#### Marka vurgusu

Electric indigo. Tek marka rengi; ikinci bir "marka mavisi" yoktur.

| Token | Dark | Light |
|---|---|---|
| `--accent-brand` | `hsl(252 88% 68%)` `#7C63F5` | `hsl(252 78% 58%)` `#5B3FE0` |
| `--accent-brand-hover` | `hsl(252 88% 74%)` `#9280F7` | `hsl(252 78% 51%)` `#4A2CD4` |
| `--accent-brand-bg` | `hsl(252 45% 18%)` `#221A3F` | `hsl(252 90% 96%)` `#EEEAFE` |
| `--accent-brand-border` | `hsl(252 50% 32%)` `#3B2C6E` | `hsl(252 70% 85%)` `#C7BAF8` |
| `--accent-brand-fg` | `hsl(0 0% 100%)` | `hsl(0 0% 100%)` |

#### Durum renkleri

Her durumun üç varyantı vardır: `-fg` (metin/ikon), `-bg` (dolgu), `-border`.
Tek bir `-fg` ile rozet yapılmaz.

| Anlam | Token kökü | Dark `-fg` | Light `-fg` | Nerede |
|---|---|---|---|---|
| Başarı | `--status-success` | `hsl(152 58% 52%)` `#3ECF8E` | `hsl(152 62% 32%)` `#1F8354` | Kapı PASS, DONE |
| Uyarı | `--status-warning` | `hsl(38 92% 60%)` `#F7B23B` | `hsl(38 88% 38%)` `#B7770B` | Kapı WARN, borç |
| Tehlike | `--status-danger` | `hsl(358 72% 62%)` `#E5484D` | `hsl(358 68% 46%)` `#C62A2F` | Kapı FAIL, REJECTED |
| **İnsan onayı** | `--status-gated` | `hsl(282 70% 70%)` `#C77DEE` | `hsl(282 62% 46%)` `#9333BE` | G kapısı, `high` risk |
| Çalışıyor | `--status-running` | `hsl(191 88% 60%)` `#38CFEA` | `hsl(191 84% 36%)` `#0E8FA9` | IMPLEMENTING, VERIFYING |
| Bekliyor | `--status-paused` | `hsl(225 10% 58%)` `#8A90A0` | `hsl(225 10% 48%)` `#6E7585` | PAUSED, PENDING |
| Yönlendirilemedi | `--status-unroutable` | `hsl(20 80% 62%)` `#EE8149` | `hsl(20 76% 42%)` `#BC5418` | UNROUTABLE |

`-bg` ve `-border`: dark'ta aynı hue, `L` sırasıyla `%16` ve `%28`;
light'ta `%96` ve `%86`.

> **Mor / cyan ayrımı bilinçli.** `--status-gated` (mor) *"senin kararını
> bekliyor"*, `--status-running` (cyan) *"sistem çalışıyor"* demektir. İkisi asla
> yer değiştirmez; kullanıcının uzaktan bakışta ayırt etmesi gereken tek şey budur.

> **Renk tek başına anlam taşımaz.** Her durum ayrıca bir **ikon şekli** ve bir
> **metin etiketi** taşır. `G_UI_3` renk-tek sinyalini hata sayar.

### 1.4 Tipografi

| Rol | Font | Fallback | Kullanım |
|---|---|---|---|
| Arayüz / metin | **Geist** | `Inter`, `system-ui`, `sans-serif` | Her şey |
| Veri / kod | **Geist Mono** | `JetBrains Mono`, `ui-monospace` | Kod, log, task id, hash, süre |

Google Fonts üzerinden; `font-display: swap`; yalnızca `400 · 500 · 600`
ağırlıkları subset edilir. Üçüncü bir aile **yoktur**.

> **Monospace kostüm değildir.** Mono yalnızca kod, log, tanımlayıcı, ölçüm ve
> karşılaştırılan sayı için kullanılır. "Teknik görünsün" diye başlıkta, etikette
> veya gövde metninde mono kullanmak yasaktır.
>
> Sayısal sütunlarda `font-variant-numeric: tabular-nums` **zorunludur**.

#### Ölçek

İki taban var, çünkü iki farklı izleyici var (§2):

| Token | Dashboard (13px taban) | Blueprint (16px taban) | Tracking |
|---|---|---|---|
| `--text-2xs` | `11px / 16px` | `12px / 16px` | `0` |
| `--text-xs` | `12px / 18px` | `13px / 20px` | `0` |
| `--text-sm` | `13px / 20px` | `14px / 22px` | `-0.005em` |
| `--text-base` | `14px / 22px` | `16px / 26px` | `-0.01em` |
| `--text-lg` | `16px / 24px` | `18px / 28px` | `-0.015em` |
| `--text-xl` | `20px / 28px` | `22px / 30px` | `-0.02em` |
| `--text-2xl` | `26px / 32px` | `30px / 36px` | `-0.025em` |
| `--text-3xl` | `32px / 38px` | `40px / 44px` | `-0.03em` |
| `--text-display` | kullanılmaz | `clamp(44px, 6vw, 72px)` | `-0.035em` |

Kurallar:
- Tracking tabanı `-0.04em`; altına inilmez.
- Gövde ölçüsü **65–75ch**, `max-width` ile sınırlanır.
- Display en fazla `6rem`.
- Ağırlık: `400` gövde, `500` etiket/UI, `600` başlık. `700` **yoktur** — vurgu
  boyut ve renkle kurulur.
- Başlıklarda `text-wrap: balance`.

### 1.5 Uzay, köşe, derinlik

**Uzay:** 4px tabanlı ölçek — `0 2 4 6 8 12 16 20 24 32 40 48 64`. Ara değer
üretilmez.

Ritim: sıkı gruplar, cömert ayrım. **Başlığın üstünde altından fazla boşluk olur.**

**Köşe:** `--radius-sm 4px` · `md 6px` · `lg 8px` · `xl 12px` · `full 9999px`.
Dashboard `sm`/`md` ağırlıklı — bilinçli olarak sıkı; yuvarlaklık aracı
yumuşatır, biz yumuşaklık istemiyoruz.

**Derinlik:** gölge **offset + blur** taşır. Sıfır offsetli renkli hale
dekorasyondur, yasaktır.

```
--shadow-sm:  0 1px 2px  hsl(228 20% 3% / .28)
--shadow-md:  0 4px 12px hsl(228 20% 3% / .34), 0 1px 2px hsl(228 20% 3% / .22)
--shadow-lg:  0 12px 32px hsl(228 20% 3% / .42), 0 2px 6px hsl(228 20% 3% / .26)
```

Dark temada derinlik öncelikle yüzey açıklığıyla kurulur; gölge yalnızca
gerçekten yüzen katmanlarda (popover, modal, dropdown) kullanılır.

### 1.6 Tarayıcı yüzeyleri

Çizmediğin parçalar da tasarımı taşır. Bunlar **zorunludur**, opsiyonel cila değil:

| Yüzey | Kural |
|---|---|
| `::selection` | `--accent-brand-bg` zemin, `--text-primary` metin |
| Caret | `caret-color: var(--accent-brand)` |
| Scrollbar | `--border-default` thumb, `--bg-base` track, 10px, yuvarlak |
| Focus ring | `2px solid var(--accent-brand)` + `2px` offset; **asla `outline: none`** |
| `::placeholder` | `--text-tertiary` |
| Bağlantı | `text-underline-offset: 0.2em`, `text-decoration-thickness: 1px` |
| Tablo sayıları | `tabular-nums` |

### 1.7 Kesin yasaklar

Tercih değil, **kapıdan geçmeyecek** öğeler. `G_UI_1` bir kısmını lint kuralıyla
yakalar; kalanı incelemede kırmızıdır.

- **Kicker / eyebrow** (başlığın üstünde küçük etiket). İstisnasız.
- **Gradient metin.** Vurgu ağırlık ve boyutla kurulur.
- Sayfa yapısı olarak **eşit boyutlu ikon + başlık + metin kart ızgarası**.
  İç içe kart her zaman yanlıştır.
- **Hero metrik şablonu**: büyük sayı + küçük etiket + destek istatistiği.
- **Bölüm numaraları** (01 / 02 / 03), sıra bilgi taşımıyorsa.
- Dekorasyon amaçlı **glass / blur**.
- Kart, liste veya uyarıda **1px'ten kalın renkli `border-left`**.
- **Sert offset gölge** (`4px 4px 0`) — neobrutalist bir dünya değiliz.
- **Sparkline, progress ring** veya içerik yerine geçen yumuşak gölgeli kutular.
- **Emoji veya unicode glif ikon yerine.** İkonlar tek kalınlıkta, Lucide'dan
  veya elle çizilmiş SVG.
- Sistem display fontu (Impact, Arial Black) başlık sesi olarak.
- Karar bekleyen bir işi **modal ile kesmek**, korunmuş odak gerekmiyorsa.

---

## 2. İki Farklı UI Kapsamı

Karıştırılması pahalı bir ayrım. **Aynı token katmanını paylaşırlar, aynı
ürün değildirler.**

| | A — P2P Kontrol Paneli | B — Üretilen Ürün Blueprint'i |
|---|---|---|
| Kimin ürünü | Bizim | Kullanıcının |
| İzleyici | P2P'yi çalıştıran geliştirici | Kullanıcının son kullanıcısı |
| Mod | **Operate** | Değişken (çoğu Operate + Persuade) |
| Taban tipografi | 13px, yoğun | 16px, ferah |
| Stack | Vite + React + TS, CLI servis eder | Next.js 15 App Router |
| Faz | 10+ | 7 (referans yığın) |
| Token katmanı | **Ortak** (§1) | **Ortak** (§1), tema override edilebilir |

> Blueprint'in tokenları **varsayılandır, dayatma değil.** Üretilen ürün
> kullanıcının markasını taşır; token dosyası bir başlangıç noktasıdır ve
> kullanıcı değiştirebilir. Panel'in tokenları ise bizim ürün kimliğimizdir.

### A — P2P Kontrol Paneli

Tek cümlelik iş tanımı: *"Yokluğumda ne oldu, ne karar verildi, şimdi benden ne
bekleniyor?"*

#### A.1 Ekran envanteri

| Ekran | İş |
|---|---|
| **Run Overview** | Koşunun tek ekranlık gerçeği; giriş noktası |
| **Task Graph** | Bağımlılıklar, dalgalar, paralellik |
| **Task Detail** | Sözleşme, denemeler, kapılar, inceleme, diff |
| **Event Stream** | Ham olay günlüğü, filtrelenebilir |
| **Approvals** | İnsan kararı bekleyen her şey (§A.3) |
| **Connections** | Bağlantı sağlığı, kota, `automation_policy` |
| **Retro** | `p2p retro` önerileri (`docs/03 §8`) |

Run Overview, `docs/03 §7.3`'teki metin çıktısının doğrudan görsel karşılığıdır.
O çıktı zaten doğru bilgi mimarisidir; ekran onu **yeniden icat etmez**, açar.

#### A.2 Task Graph görselleştirici

- Yönlü çevrimsiz graph; **dalgalar yatay bantlar** olarak sunulur — paralellik
  kullanıcının görmesi gereken birinci bilgidir (`docs/03 §2`).
- Düğüm = task. Renk durumu, **şekil riski** taşır: `low` yuvarlak köşe,
  `medium` dikdörtgen, `high` çentikli köşe. Renk tek sinyal değildir.
- Kenar = bağımlılık. `depends_on` düz çizgi; ACR'dan doğan bağımlılık kesik.
- Otomatik yerleşim (dagre benzeri katmanlı), elle konum yok — graph veriden
  türetilir, kullanıcı düzenlemez.
- 40+ düğümde otomatik olarak **dalga özetine** düşer; her düğümü çizmeye
  çalışmak okunabilirliği yok eder.
- Kütüphane kararı açık (§5, D13). React Flow ve elle SVG + dagre adayları.

#### A.3 İnsan onay ekranı

Ürünün en kritik ekranı. Buraya düşen her şey, sistemin **tek başına karar
veremediği** şeydir.

Her onay kaydı şunları gösterir:

1. **Ne** — task/kapı kimliği ve tek satır özeti
2. **Neden burada** — `high` risk mi, G kapısı mı, escalation mı
3. **Kanıt** — kapı çıktıları, inceleme bulguları, diff
4. **Sistemin görüşü** — mimar agent'ın kök neden analizi ve önerdiği seçenekler
5. **Eylem** — Onayla / Reddet / **Yönlendir** (`p2p steer`, serbest metin)

Diff önizlemesi satır bazlı, `--bg-inset` üzerinde, mono. Eklenen satır
`--status-success-bg`, silinen `--status-danger-bg` — ikisi de ayrıca `+`/`-`
işareti taşır.

**Modal kullanılmaz.** Onay bir kesinti değil, kullanıcının o ekrana gelme
sebebidir; kendi rotasında tam sayfa yaşar.

**Yıkıcı eylem onayı** (`FORBIDDEN`/`DANGEROUS` sınıfı, `docs/06 §6`) tek
tıkla verilemez: ikincil bir doğrulama gerektirir ve varsayılan odak **iptal**
üzerindedir.

#### A.4 Otonomi anahtarı ve `decided_by=default` işareti

Otonomi seviyesi (`supervised | guarded | full`) her ekranda görünür ve tek
yerden değiştirilir. Seviye yükseltmek — özellikle `full` — **bir onay
adımıdır**, sessiz bir toggle değil; kullanıcı neyin otomatikleşeceğini
gördükten sonra onaylar.

`full` modda dahi `high` risk task'ları geçmez (`ADR-010`). Anahtar bunu
seçim anında açıkça söyler.

**İmza öğe:** otomatik verilmiş her karar, kaydının yanında ayırt edici bir im
taşır ve Run Overview'da **ayrı bir satırda sayılır**:

```
otomatik karar   2   (G2 mimari · G4 yayın — decided_by=default)
```

Bu im gizlenemez, filtrelenip kapatılamaz, "hepsini gördüm" ile susturulamaz.
Ürünün ikinci ilkesinin görsel karşılığı budur.

#### A.5 Canlı akış

- Taşıma **SSE**; `.p2p/events.jsonl` takip edilir (`ADR-002`). WebSocket
  gereksiz — akış tek yönlü.
- UI **yazmaz** (`ADR-003`). Onay ve steer eylemleri CLI'a komut olarak gider;
  UI sonucu olay günlüğünden okur.
- Bağlantı koparsa: son bilinen durum **bayat** olarak işaretlenir ve zamanı
  gösterilir. Sessizce eski veri gösterilmez.
- Yeni olaylar listeye **üstten** girer, ekran zıplamaz; kullanıcı aşağı
  kaydırmışsa otomatik takip durur ve "N yeni olay" düğmesi çıkar.

### B — Üretilen Ürün Blueprint'i

Faz 7 referans yığınının frontend standardı. Üretilen her ürün bununla başlar.

**Stack:** Next.js 15 (App Router) · TypeScript strict · Tailwind CSS ·
Radix UI primitives (shadcn/ui deseni) · Lucide ikonlar.

Gerekçe `docs/10 D2`'de: uygulayıcı bir AI modeli olduğu için, en güvenilir
ürettiği ve doğrulama araçlarının en olgun olduğu yığın seçilir.

#### B.1 Zorunlu sayfa akışları

| Akış | Zorunlu durumlar |
|---|---|
| Landing | hero, değer önerisi, CTA — kanıt uydurulmaz (`PRODUCT.md` → Evidence) |
| Auth | login, register, şifre sıfırlama, doğrulama, hata |
| Dashboard | dolu, **boş**, yükleniyor, hata, yetkisiz |
| Liste / Detay | dolu, boş, filtrelenmiş-boş, sayfalama, sıralama |
| Form | boş, doldurulmuş, gönderiliyor, alan hatası, sunucu hatası, başarı |
| Hata | 404, 500, `error.tsx` sınırı, `not-found.tsx` |

#### B.2 Üç durum pazarlık konusu değildir

Her veri gösteren bileşen üçünü de tanımlamak zorundadır. Eksiği `G_UI_4`'te
kırmızıdır.

- **Boş:** ne olduğunu açıklar ve **bir sonraki eylemi verir**. Süslü çizim
  değil, cümle + düğme. "Henüz veri yok" tek başına eksiktir.
- **Yükleniyor:** `Suspense` + skeleton. Skeleton **gerçek yerleşimin
  iskeletidir**; genel gri kutu değil. Spinner yalnızca 400ms'den kısa
  belirsiz beklemelerde.
- **Hata:** `error.tsx` sınırı. Sorunu **ve kurtarma yolunu** söyler; yığın
  izi kullanıcıya gösterilmez, `retry` düğmesi bulunur.

---

## 3. Bileşen Mimarisi ve Dizin Düzeni

### 3.1 Üç katman, karışmaz

```
components/
├── ui/          Primitifler. Ürün bilgisi YOK. Radix + token.
│                Button, Input, Select, Dialog, Tooltip, Badge,
│                Skeleton, Table, Tabs, Toast
│
├── features/    Ürün bilgisi taşır. Alan başına klasör.
│   ├── task-graph/    GraphCanvas, WaveBand, TaskNode, DependencyEdge
│   ├── approvals/     ApprovalCard, DiffPreview, DecisionActions
│   ├── run/           RunSummary, StatusRollup, AutonomySwitch
│   ├── events/        EventStream, EventRow, StreamFilter
│   └── connections/   ConnectionCard, HealthBadge, QuotaMeter
│
└── layouts/     İskelet. AppShell, SidebarNav, PageHeader, SplitPane
```

Bağımlılık yönü tek yönlüdür ve `docs/01 §3`'ün aynısıdır:

```
layouts → features → ui → tokens
```

- `ui/` **asla** `features/`'tan import etmez.
- İki `features/` klasörü birbirinden import etmez; ortak parça `ui/`'ye çıkar.
- `ui/` içinde durum adı geçmez. `<Badge tone="success">` doğru;
  `<TaskStatusBadge>` `features/`'a aittir.

### 3.2 Bileşen sözleşmesi

Her `ui/` bileşeni şunları karşılamak zorundadır:

- [ ] Tüm görsel değerler token'dan; ham renk/ölçü yok
- [ ] `hover` · `focus-visible` · `active` · `disabled` · `loading` durumları
- [ ] Klavyeyle tam kullanılabilir; focus ring görünür
- [ ] `forwardRef` + yerel HTML attribute'ları geçirir
- [ ] Erişilebilir ad (`aria-label` veya görünür metin)
- [ ] İki temada da doğru; hiçbir değer temaya sabitlenmemiş

### 3.3 Responsive — mobile-first

| Ad | Min genişlik | Not |
|---|---|---|
| `base` | `0` | Varsayılan; medya sorgusu yok |
| `sm` | `640px` | |
| `md` | `768px` | Tablet |
| `lg` | `1024px` | Panel'in gerçek tabanı |
| `xl` | `1280px` | |
| `2xl` | `1536px` | |

Yalnızca `min-width` kullanılır; `max-width` sorgusu yazılmaz.

**Panel (A) için dürüst kapsam:** yoğun bir izleme aracıdır. `lg` ve üstünde
tam işlevlidir. `base`–`md` arası **okunabilir ve eyleme geçirilebilir** olmak
zorundadır — kullanıcı telefondan bakıp onay verebilmelidir — ama task graph
küçük ekranda **dalga listesine** düşer. Graph'ı telefona sıkıştırmaya çalışmak
ikisini de bozar.

**Blueprint (B):** her breakpoint'te tam işlevli.

Sabit kurallar: dokunma hedefi ≥ `44px`; hiçbir breakpoint'te yatay taşma;
geniş içerik (tablo, kod, graph) kendi `overflow-x: auto` kabında kayar,
sayfa gövdesi asla yatay kaymaz.

### 3.4 Mikro-etkileşim ve hareket

| Token | Süre | Nerede |
|---|---|---|
| `--motion-instant` | `100ms` | Renk, opaklık |
| `--motion-fast` | `150ms` | Hover, focus, küçük durum |
| `--motion-base` | `200ms` | Popover, dropdown, akordeon |
| `--motion-slow` | `320ms` | Sayfa/panel geçişi. Üst sınır |

Easing: `--ease-out: cubic-bezier(0.16, 1, 0.3, 1)` (üstel çıkış).
Giriş `ease-out`, çıkış `ease-in`, süre çıkışta `%70`.

Kurallar:

- Yalnızca `transform`, `opacity`, `filter`, `clip-path` animasyonlanır.
  Layout tetikleyen özellik (`width`, `top`, `margin`) animasyonlanmaz.
- **Bir yetkili an**; her bölüme aynı giriş animasyonu verilmez.
- Animasyon **görünür bir varsayılandan** başlar; içerik opaklık 0'dan gelmez.
- `prefers-reduced-motion: reduce` → süreler `0.01ms`, hareket iptal, durum
  değişimi anında ve tam.
- Canlı akışta gelen satır **kısa bir vurgu** alır ve söner; kalıcı yanıp
  sönme yoktur.

Yasak: sonsuz dönen dekoratif animasyon, parallax, imleç takip efekti,
kaydırma ile tetiklenen ardışık giriş dizileri.

---

## 4. UI Kalite Kapıları — `docs/05` Entegrasyonu

`docs/05`'in temel ilkesi burada da aynen geçerlidir:

> Bir UI bileşeninin doğru olduğuna **dil modeli karar vermez**; kapı çıkış
> kodu karar verir (`ADR-004`).

Dört kapı `docs/05 §2`'deki katman sırasına eklenir ve `TaskContract.gates`
içinde adlarıyla anılır.

| Kapı | Komut | Geçme koşulu | Sınıf |
|---|---|---|---|
| `G_UI_1` | `prettier --check . && eslint . --max-warnings=0` | exit 0 | lint |
| `G_UI_2` | `tsc --noEmit` | exit 0 | typecheck |
| `G_UI_3` | `axe` + `lhci` | axe ihlal 0 (critical/serious), Lighthouse a11y ≥ 90 | a11y |
| `G_UI_4` | `vitest run` + `playwright test --grep @smoke` | exit 0 | unit + e2e |

### G_UI_1 — Lint ve biçim

`prettier --check` ve `eslint --max-warnings=0`. Uyarı **hata sayılır**; biriken
uyarı sessiz borçtur.

Zorunlu eklentiler: `eslint-plugin-jsx-a11y`, `eslint-plugin-react-hooks`,
`@typescript-eslint`.

`docs/03 §8.2` gereği, §1.7'deki yasakların mekanik olarak yakalanabilenleri
**lint kuralı olarak** yaşar, prompt satırı olarak değil:

- Ham renk değeri (`#rrggbb`, `rgb()`, `hsl()`) bileşen dosyasında → hata
- Tailwind'de token dışı renk sınıfı (`text-slate-400`) → hata
- `outline: none` (yerine focus stili konmadan) → hata
- `<div>` üzerinde `onClick`, rol ve klavye işleyicisi olmadan → hata
- Ölçek dışı `font-size` / `spacing` ham değeri → hata

### G_UI_2 — Tip güvenliği

`tsc --noEmit`, `strict: true`. `any` yasak (`unknown` + daraltma kullanılır).
`@ts-ignore` yasak; `@ts-expect-error` yalnızca gerekçe yorumuyla.

### G_UI_3 — Erişilebilirlik

- `axe-core`: `critical` ve `serious` ihlal sayısı **0**
- Lighthouse accessibility skoru **≥ 90**
- Kontrast: gövde ≥ `4.5:1`, büyük metin ≥ `3:1` — §1.3 tabanlarıyla uyumlu
- **Renk-tek sinyal hatadır**: her durum ikon veya metin de taşımalı
- Klavye: tüm etkileşimli öğeler erişilebilir, focus görünür, tuzak yok
- Her sayfada tek `h1`; başlık seviyesi atlanmaz

### G_UI_4 — Bileşen ve E2E testleri

- `vitest` + Testing Library. Test **davranışı** doğrular, implementasyonu değil.
- `ui/` bileşenleri için üç durum testi zorunlu: boş, yükleniyor, hata (§B.2).
- Playwright `@smoke`: uygulama gerçekten ayağa kalkıyor ve altın yol çalışıyor.
  Bu, `docs/05 §3`'teki `smoke` kapısının frontend karşılığıdır ve aynı
  gerekçeyle pazarlık konusu değildir — **bütün testler geçip uygulama
  açılmaması** UI'da da en sık başarısızlık biçimidir.
- Kaynak gerektiren kapılar (`playwright`) `isolation: serialized`
  (`docs/03 §2.5`).

### Kapı tanımı

```yaml
gates:
  G_UI_1:
    cmd: ["pnpm", "run", "lint:ci"]
    cwd: "frontend"
    timeout_s: 180
    parse: eslint
  G_UI_2:
    cmd: ["pnpm", "exec", "tsc", "--noEmit"]
    cwd: "frontend"
    timeout_s: 300
    parse: tsc
  G_UI_3:
    cmd: ["pnpm", "run", "a11y:ci"]
    cwd: "frontend"
    timeout_s: 600
    isolation: serialized
    parse: axe
  G_UI_4:
    cmd: ["pnpm", "run", "test:ci"]
    cwd: "frontend"
    timeout_s: 900
    isolation: serialized
    parse: vitest
```

### Etki tabanlı regresyon

`docs/05 §8`'e eklenir:

```
frontend/**          → G_UI_1, G_UI_2, G_UI_4, e2e
frontend/tokens/**   → yukarıdakiler + G_UI_3 (token değişimi kontrastı bozabilir)
components/ui/**     → yukarıdakilerin tamamı
```

### DONE tanımına ek

`docs/05 §9`'daki listeye, UI dokunan task'lar için:

- [ ] Bileşen iki temada da doğru
- [ ] Boş / yükleniyor / hata durumları var ve test edilmiş
- [ ] `base` ve `lg` breakpoint'lerinde yatay taşma yok
- [ ] Klavyeyle tam kullanılabilir

---

## 5. Açık Kararlara Etkisi

### D2 — Referans yığın: **bağlandı**

`docs/10 D2` bu belgeyle kapanıyor. Frontend tarafı artık açık değil:

> **Next.js 15 (App Router) · TypeScript strict · Tailwind CSS ·
> Radix UI primitives (shadcn/ui deseni) · Lucide**

Backend ve veritabanı tarafı D2'nin önerisinde kalıyor (FastAPI + Postgres) ve
Faz 7'ye kadar onaylanmayı bekliyor. Bu ayrım bilinçli: frontend standardı
şimdi gerekiyordu çünkü tasarım sistemi ona bağlı; backend seçimi Faz 7'den
önce gerekmiyor.

### D9 — Otonomi varsayılanı

Panel bu kararı **görünür kılar** ama vermez. `guarded` önerisi geçerli;
anahtar (§A.4) hangi seviyede neyin otomatikleştiğini seçim anında gösterir.

### Yeni açık kararlar

**D13 — Task graph görselleştirme kütüphanesi**

| Seçenek | Artı | Eksi |
|---|---|---|
| React Flow | Hazır etkileşim, pan/zoom, olgun | ~50kb, kendi stil sistemi token'larımızla çakışabilir |
| Elle SVG + dagre | Tam token kontrolü, küçük | Pan/zoom, sanallaştırma elle yazılır |

**Öneri:** dagre yerleşimi + elle SVG. Gerekçe: graph'ın **okunabilirliği**
ürünün değeri; hazır bir kütüphanenin varsayılan görünümü §1.1'deki bakış
açısını taşımaz. Karar Faz 10'a kadar bekleyebilir.

- [ ] Karar: ______

**D14 — Panel yazabilir mi**

`ADR-003` UI'ın orkestrasyon durumuna yazmasını yasaklıyor. §A.3'teki onay ve
steer eylemleri bu yasağı ihlal etmez (CLI'a komut giderler, UI sonucu olay
günlüğünden okur) — ama bu dolaylılığın uygulama biçimi kararlaştırılmadı.

**Öneri:** panel yerel CLI'a bir komut kuyruğu üzerinden yazar; orchestrator
kuyruğu okur, eylemi kendisi yapar ve olayı kendisi yazar. Tek yazar kuralı
korunur.

- [ ] Karar: ______

**D15 — Blueprint tokenlarını kullanıcı nasıl değiştirir**

Üretilen ürün kullanıcının markasını taşır. Token dosyasının nasıl
özelleştirileceği (prompt'ta marka bilgisi mi, üretim sonrası düzenleme mi,
`Blueprint` parametresi mi) kararlaştırılmadı. Faz 7'ye kadar bekleyebilir.

- [ ] Karar: ______

---

## 6. Bu belgeyi kim, ne zaman okur

| Kim | Ne zaman | Ne için |
|---|---|---|
| Uygulayıcı agent | Her UI task'ı | Token adları, dizin, yasaklar, DONE tanımı |
| Gözden geçiren agent | Her UI incelemesi | §1.7 yasakları, §3.2 sözleşmesi |
| Orchestrator | Kapı seçimi | §4 kapı tanımları |
| İnsan | Faz 7 ve Faz 10 öncesi | §5 açık kararlar |

Değiştirmek isteyen: **ACR açar** (`prompts/acr-template.md`). Token adı veya
yasak listesi sessizce değiştirilemez — `docs/02`'deki alan adlarıyla aynı
statüdedir.
