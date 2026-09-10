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
      │   task graph · scheduler · state machine · retry    │
      └──┬─────────┬──────────┬──────────┬──────────┬──────┘
         │         │          │          │          │
   ┌─────▼───┐┌────▼─────┐┌───▼─────┐┌───▼─────┐┌───▼──────┐
   │ Policy  ││ Runtime  ││Workspace││Verifi-  ││ Event    │
   │ Engine  ││ Registry ││ Manager ││cation   ││ Store    │
   │(izinler)││(adapter) ││(git/fs) ││ Engine  ││(JSONL)   │
   └─────────┘└────┬─────┘└────┬────┘└───┬─────┘└──────────┘
                   │           │         │
        ┌──────────┼───┐       │    ┌──────────────────┐
        │          │   │       │    │ pytest/tsc/lint/ │
   ┌────▼───┐ ┌────▼──┐│       │    │ playwright/smoke │
   │claude  │ │gemini ││       │    └──────────────────┘
   │ -p     │ │ -p    ││       │
   └────────┘ └───────┘│       │
                       └───────┤
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
| `workspace` | Dizin düzeni, git, worktree, artifact yolları | Task durumu |
| `verification` | Kalite kapılarını çalıştırıp `GateResult` döndürmek | Sonuca göre karar vermek |
| `policy` | Bir eylemin izinli olup olmadığına karar vermek | Eylemi yapmak |
| `events` | Append-only olay yazımı + state türetimi | Yorumlama |
| `routing` | capability → runtime eşlemesi | Adapter detayı |

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

### Neden SQLite değil

Paralel agent process'leri aynı SQLite dosyasına yazarsa kilit çekişmesi
yaşanır ve Windows'ta bu özellikle sorunludur. Tek yazarlı append-only JSONL,
v1'in eşzamanlılık ihtiyacı için hem yeterli hem de radikal biçimde daha basit.
Sorgu ihtiyacı büyürse JSONL'den SQLite'a projeksiyon yazmak geriye dönük
uyumlu bir eklemedir. (ADR-002)

## 6. Üretilen çalışma alanı düzeni

```
<generated-project>/
├── .git/
├── .p2p/                  ← P2P metadata (üretilen uygulamadan tamamen ayrık)
│   ├── project.json       ← ürün tanımı, teknoloji seçimi (değişmez)
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

## 7. Teknoloji seçimi (P2P'nin kendisi için)

| Alan | Seçim | Neden | Alternatif ve neden değil |
|---|---|---|---|
| Dil | **Python 3.11+** | Alt process orkestrasyonu stdlib'de çözülmüş; modellerin en iyi yazdığı dil; katkı eşiği düşük | Node: `gemini-cli` Node ama onu subprocess çağırıyoruz, aynı runtime'da olmanın faydası yok. Go: dağıtımı kolay ama üretim kalitesi ve katkı eşiği daha kötü |
| CLI | **Typer** | Tip ipuçlarından üretim, alt komut ağacı, iyi yardım çıktısı | argparse fazla ayrıntılı; Click zaten Typer'ın altında |
| Eşzamanlılık | **`concurrent.futures.ThreadPoolExecutor`** | İş yükü %100 alt process bekleme, GIL sorun değil; asyncio'dan çok daha kolay hata ayıklanır | asyncio: subprocess beklemek için gereksiz karmaşıklık |
| Kalıcılık | **JSONL + türetilmiş state** | Bkz. §5 | SQLite: kilit çekişmesi |
| Şema doğrulama | **Pydantic v2** | Agent çıktısı güvenilmezdir; sınırda kırılmalı | Elle dict kontrolü: sessiz hata kaynağı |
| Şablonlama | **Jinja2** | Promptlar versiyonlanabilir dosya olmalı | f-string: promptlar koda gömülür, gözden geçirilemez |
| Test | **pytest** | — | — |
| Loglama | **structlog** (veya stdlib JSON formatter) | Olay günlüğüyle aynı biçim | — |
| Dağıtım | **uv / pipx** | Tek komut kurulum | — |

Prensip: **sıkıcı ve sağlam** teknoloji.

## 8. Genişletilebilirlik: eklenti sınırları

v1'de gerçek bir eklenti sistemi **yok**, ama üç genişleme noktası arayüz
olarak tanımlı ve ileride eklenti haline gelecek:

1. **RuntimeAdapter** — yeni agent runtime (`docs/04`)
2. **QualityGate** — yeni doğrulama kapısı (`docs/05`)
3. **Blueprint** — yeni proje şablonu / teknoloji yığını

Bu üçü dışında hiçbir şey v1'de genişletilebilir yapılmayacak. Erken
soyutlama hem katkıcıyı hem bizi yavaşlatır.

## 9. Buluta geçiş yolu (bugün yapılmayacak, ama kapatılmayacak)

- `Workspace` arayüzü yerel dosya sistemi varsayımını sızdırmaz → S3/hacim
- Olay günlüğü append-only → doğrudan bir akış/kuyruk arkasına taşınabilir
- `RuntimeAdapter` alt process varsayımını sızdırmaz → uzak yürütücü olabilir
- Orchestrator durumsuzdur; durum olay günlüğünden türetilir → yatay ölçek

Kapatmamak için tek somut kural: **hiçbir modül `os.getcwd()` ya da mutlak
yerel yol varsaymaz; her yol `Workspace`'ten gelir.**
