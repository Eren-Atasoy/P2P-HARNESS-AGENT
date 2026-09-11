# 01 — Sistem Mimarisi

## 1. Mimari seçimi

Üç aday değerlendirildi (detay: `adr/ADR-001`).

| | A: Düz script + dosya | **B: Modüler monolit + olay günlüğü** | C: Olay güdümlü agent platformu |
|---|---|---|---|
| Karmaşıklık | Çok düşük | Düşük-orta | Yüksek |
| Debug edilebilirlik | Orta | **Yüksek** | Düşük |
| Paralellik | Zayıf | **İyi** | Çok iyi |
| Kurtarılabilirlik | Yok | **Var** | Var |
| Katkıcı dostluğu | Yüksek | **Yüksek** | Düşük |
| Buluta taşınabilirlik | Zor | **Orta** | Kolay |

**Seçim: B.** Tek process, modüler monolit; kalıcılık append-only olay günlüğü;
agent'lar alt process. Gerekçe: v1'in gerçek riski ölçek değil, **hata ayıklama**.
Bir agent yanlış kod ürettiğinde "neden" sorusunu 30 saniyede cevaplayamıyorsan
proje ölür. Olay günlüğü bunu garanti eder.

## 2. Kuş bakışı

```
                         ┌──────────────┐
                         │   p2p CLI    │
                         └──────┬───────┘
                                │
                    ┌───────────▼────────────┐
                    │      Application       │  komut → use-case
                    └───────────┬────────────┘
                                │
      ┌─────────────────────────▼──────────────────────────┐
      │                  Orchestrator                      │
      │  task graph · scheduler · state machine · otonom   │
      │  döngü · retry · escalation                        │
      └──┬────────┬─────────┬─────────┬─────────┬──────────┘
         │        │         │         │         │
   ┌─────▼────┐┌──▼──────┐┌─▼───────┐┌▼────────┐┌▼─────────┐
   │  Policy  ││Capability││Workspace││ Verifi- ││  Event   │
   │  Engine  ││  Router  ││ Manager ││  cation ││  Store   │
   │izin+risk ││cap+risk→ ││ git/fs  ││ Engine  ││  JSONL   │
   │+otonomi  ││ bağlantı ││worktree ││         ││tek yazar │
   └──────────┘└────┬─────┘└─────────┘└────┬────┘└──────────┘
                    │                      │
        ┌───────────▼────────────┐    ┌────▼──────────────┐
        │  Connection Registry   │    │ lint · typecheck  │
        │  + Runtime Adapters    │    │ unit · contract   │
        │                        │    │ smoke · e2e · sec │
        │ subscription│api│local │    └───────────────────┘
        │        │gateway        │
        └───┬────────┬───────┬───┘
            │        │       │
       ┌────▼───┐┌───▼───┐┌──▼────────┐
       │ claude ││gemini ││ api/local │   ← v1'de ilk ikisi
       │  -p    ││  -p   ││ (Faz 9)   │      uygulanır
       └────────┘└───────┘└───────────┘
                    │
             ┌──────▼────────┐
             │ generated repo│
             │ + git worktree│
             └───────────────┘
```

## 3. Modüller ve sorumluluklar

Bağımlılık yönü **daima yukarıdan aşağıya**. Alt katman üstü tanımaz.

| Modül | Sorumluluk | Sorumlu **olmadığı** |
|---|---|---|
| `cli` | Argüman ayrıştırma, çıktı biçimlendirme | İş mantığı |
| `app` | Use-case orkestrasyonu (`new`, `plan`, `run`, `resume`, `status`) | Zamanlama, model seçimi |
| `orchestrator` | Task graph, scheduler, state machine, retry, escalation | Model çağırma, kabuk komutu |
| `runtime` | Bir agent'ı çalıştırıp `AgentResult` döndürmek | Ne çalıştırılacağına karar vermek |
| `connections` | Kullanıcının AI erişimlerini kaydetmek, sağlığını ve politikasını izlemek | Seçim yapmak |
| `workspace` | Dizin düzeni, git, worktree, artifact yolları | Task durumu |
| `verification` | Kalite kapılarını çalıştırıp `GateResult` döndürmek | Sonuca göre karar vermek |
| `policy` | Bir eylemin izinli olup olmadığına karar vermek | Eylemi yapmak |
| `events` | Append-only olay yazımı + state türetimi | Yorumlama |
| `router` | (capabilities + risk + policy) → `Connection` seçimi; uygun yoksa `UNROUTABLE` | Adapter detayı, çağrı biçimi |

### Altın kural: tek yazar

> Orkestrasyon durumunu **yalnızca orchestrator** yazar.
> Agent'lar state'e dokunamaz. Agent'ın tek yapılandırılmış çıktısı,
> kendisine verilen `result_path` dosyasına yazdığı JSON'dur.

Bu kural olmadan paralel agent'lar durum dosyasını yarıştırır ve sistem
sessizce bozulur. (ADR-003)

## 4. Veri akışı — uçtan uca

```
kullanıcı promptu
   │
   ▼
[DISCOVERY]  claude ── ürün tanımı, belirsizlik listesi
   │                    ↳ belirsizlik varsa → İNSAN KARAR KAPISI
   ▼
[ARCHITECTURE] claude ─ mimari + teknoloji seçimi + veri modeli
   │                    ↳ İNSAN ONAY KAPISI (geri dönüşü pahalı)
   ▼
[PLANNING]   claude ── task graph (bağımlılıklar + kabul kriterleri)
   │
   ▼
[ROUTING]    router ────── her task için capability + risk → Connection
   │                          ↳ uygun bağlantı yoksa → UNROUTABLE
   ▼
[SCHEDULING] orchestrator ─ topolojik sıra, paralel dalga hesabı
   │
   ├──► dalga 1: DB-001            (worktree A)
   │
   ├──► dalga 2: API-001 ‖ UI-001  (worktree B, C)  ← paralel
   │
   └──► dalga 3: E2E-001           (birleştirilmiş ağaç)
                    │
   her task için:   ▼
        ┌──────────────────────────────┐
        │ IMPLEMENT   gemini            │
        │     ▼                         │
        │ VERIFY      deterministik     │  ← AI yok
        │     ▼                         │
        │ REVIEW      claude            │
        │     ▼                         │
        │ APPROVED? --hayır--> FIX -----┘
        │     │evet
        └─────┼────────────────────────┐
              ▼                         │
           MERGE (worktree -> integration)
              ▼
        [REGRESSION]  tüm kapılar yeniden
              ▼
        [RELEASE]  artifact + docs + İNSAN ONAY KAPISI
```

## 5. Üç ayrı doğruluk kaynağı

Bunları karıştırmak en yaygın mimari hatadır. Her verinin **tek** bir evi vardır.

| Veri türü | Ev | Neden |
|---|---|---|
| Uygulama kaynak kodu | **Git** | Sürümleme, diff, merge, geri alma zaten çözülmüş |
| Orkestrasyon durumu | **`.p2p/events.jsonl`** | Append-only, kilitsiz, insan okuyabilir, git'e girebilir |
| Büyük artifact (log, ekran görüntüsü, ham model çıktısı) | **`.p2p/runs/<run_id>/`** | Git'i şişirmemeli; `.gitignore`'da |
| Mimari kararlar | **`docs/` + `docs/adr/`** | İnsan tarafından okunan sözleşme |

`state.json` **türetilmiş** bir görünümdür — olay günlüğünden yeniden
üretilebilir, doğruluk kaynağı değildir. Silinirse yeniden hesaplanır.

### Neden SQLite değil (v1) ve EventStore Soyutlaması

Paralel agent process'leri aynı SQLite dosyasına doğrudan yazarsa kilit çekişmesi
yaşanır ve Windows'ta bu özellikle sorunludur. Tek yazarlı append-only JSONL,
v1'in yerel eşzamanlılık ihtiyacı için hem yeterli hem de radikal biçimde daha basittir.

**Gelecek projeksiyonu (EventStore interface):**
Event depolama katmanı bir `EventStore` arayüzü arkasında soyutlanır:
- `JsonlEventStore` (v1 — yerel dosya tabanlı, append-only doğruluk kaynağı)
- `SqliteEventStore` (gelecek projeksiyonu — `p2p status`, `p2p cost`, `p2p analytics` gibi zengin sorgular için JSONL'den SQLite'a türetilmiş görünüm) (ADR-002)

## 6. Üretilen çalışma alanı düzeni

```
<generated-project>/
├── .git/
├── .p2p/                  ← P2P metadata (üretilen uygulamadan tamamen ayrık)
│   ├── project.json       ← ürün tanımı, teknoloji seçimi (değişmez)
│   ├── routing.yaml       ← bağlantılar, yetenekler, politika (docs/04 §6)
│   ├── events.jsonl       ← doğruluk kaynağı
│   ├── state.json         ← türetilmiş görünüm (gitignore)
│   ├── tasks/*.json       ← task sözleşmeleri
│   ├── runs/<run_id>/     ← prompt, ham çıktı, log (gitignore)
│   ├── reviews/*.json     ← inceleme sonuçları
│   ├── acr/*.md           ← mimari değişiklik talepleri
│   └── docs/              ← Claude'un ürettiği ürün + mimari belgeleri
├── docs/                  ← son kullanıcı belgeleri
├── backend/
├── frontend/
├── tests/
├── infra/
└── .github/workflows/
```

**Değişmez kural:** `.p2p/` silindiğinde proje normal bir repo olarak
çalışmaya devam etmelidir. P2P metadata'sı uygulama koduna sızamaz —
ne import, ne yorum satırı, ne yapılandırma.

### P2P Runtime Stack ≠ Generated Product Stack

En temel mimari ayrım şudur:
- **P2P Runtime Stack:** Python 3.12+, Typer, Pydantic v2, uv. P2P'nin kendi orchestrator / control-plane motorudur.
- **Generated Product Stack:** Tamamen dinamiktir; kullanıcının promptuna ve seçilen Blueprint'e göre belirlenir (ör: Next.js + FastAPI, Go + React, Flutter + Node.js vb.). P2P'nin Python olması, üretilen ürünün Python olmasını zorunlu kılmaz.

## 7. Teknoloji seçimi (P2P'nin kendisi için)

| Alan | Seçim | Neden | Alternatif ve neden değil |
|---|---|---|---|
| Dil | **Python 3.12+** | Alt process orkestrasyonu, Antigravity Python SDK & MCP entegrasyonu, model uyumu, zengin veri modelleme (Pydantic v2) | Node/TS: frontend ekosistemi zengin ama P2P control plane için subprocess/agent orkestrasyonunda Python daha avantajlı. Go: tek binary ama AI SDK ve hızlı iterasyonda zayıf |
| Paket Yöneticisi | **uv** | Ultra hızlı paket çözümü, lock dosyası otoritesi, pipx benzeri tek komut çalıştırma | Standart pip: yavaş; poetry: ağır |
| CLI | **Typer** | Tip ipuçlarından üretim, alt komut ağacı, zengin yardım çıktısı | argparse: ayrıntılı; Click: Typer'ın alt katmanı |
| Eşzamanlılık | **`concurrent.futures.ThreadPoolExecutor` (v1) → `asyncio / TaskGroup` (geçiş yolu)** | v1 prototipinde alt process bekleme için yeterli; Faz 5 orchestrator'da agent lifecycle, streaming stdout, timeout ve cancel ağacı için `asyncio.create_subprocess_exec` + `TaskGroup`'a evrilir | — |
| Kalıcılık | **`EventStore` (v1: `JsonlEventStore`, Gelecek: `SqliteEventStore`)** | Append-only, kilitsiz, insan okuyabilir; SQLite projection ile analitik | Doğrudan SQLite yazımı: paralel kilit çekişmesi |
| Şema doğrulama | **Pydantic v2** | Agent çıktısı güvenilmezdir; sınırda kırılmalı | Elle dict kontrolü: sessiz hata kaynağı |
| Şablonlama | **Jinja2** | Promptlar versiyonlanabilir dosya olmalı | f-string: koda gömülür, gözden geçirilemez |
| Test | **pytest** | — | — |
| Loglama | **structlog / JSON** | Olay günlüğüyle aynı biçim | — |
| Dağıtım | **uv / pipx** | Tek komut kurulum | — |

Prensip: **sıkıcı, sağlam ve genişletilebilir** teknoloji.

## 8. Genişletilebilirlik: eklenti sınırları

v1'de gerçek bir eklenti sistemi **yok**, ama üç genişleme noktası arayüz
olarak tanımlı ve ileride eklenti haline gelecek:

1. **RuntimeAdapter** — yeni agent runtime (`docs/04 §4`)
2. **QualityGate** — yeni doğrulama kapısı (`docs/05 §6`)
3. **Blueprint** — yeni proje şablonu / teknoloji yığını
4. **Capability** — yeni yetenek türü (yalnızca veri; kod değişikliği gerektirmez)

Bu üçü dışında hiçbir şey v1'de genişletilebilir yapılmayacak. Erken
soyutlama hem katkıcıyı hem bizi yavaşlatır.

## 9. Buluta geçiş yolu (bugün yapılmayacak, ama kapatılmayacak)

- `Workspace` arayüzü yerel dosya sistemi varsayımını sızdırmaz → S3/hacim
- Olay günlüğü append-only → doğrudan bir akış/kuyruk arkasına taşınabilir
- `RuntimeAdapter` alt process varsayımını sızdırmaz → uzak yürütücü olabilir
- Orchestrator durumsuzdur; durum olay günlüğünden türetilir → yatay ölçek

Kapatmamak için tek somut kural: **hiçbir modül `os.getcwd()` ya da mutlak
yerel yol varsaymaz; her yol `Workspace`'ten gelir.**
