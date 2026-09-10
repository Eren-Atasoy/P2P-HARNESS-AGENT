# Prompt2Product

Kullanıcının erişebildiği AI agent'larını, araçlarını ve runtime'larını otonom
biçimde koordine ederek doğal dildeki ürün isteklerini doğrulanmış yazılım
ürünlerine dönüştüren, model-bağımsız ve local-first bir yazılım mühendisliği
platformu.

> **Prompt in. Verified Product out.**

Üç iddia bağlayıcıdır: **otonom** (kullanıcı agent'lar arasında mesaj taşımaz),
**model-bağımsız** (çekirdekte hiçbir sağlayıcı adı geçmez), **doğrulanmış**
(bitti kararını kapı çıkış kodu verir).

Bu repo şu an **mimari ve spesifikasyon fazındadır.** Henüz runtime kodu yoktur.

---

## Bu repoyu nasıl okumalısın

Sırayla:

| # | Dosya | Ne anlatır |
|---|---|---|
| 1 | `docs/00-vision.md` | Ne yapıyoruz, ne yapmıyoruz |
| 2 | `docs/01-architecture.md` | Sistem mimarisi, modüller, veri akışı |
| 3 | `docs/02-data-model.md` | Task, State, Contract şemaları |
| 4 | `docs/03-orchestration.md` | State machine, paralellik, retry, escalation |
| 5 | `docs/04-provider-architecture.md` | Sağlayıcı, bağlantı, runtime, capability routing |
| 6 | `docs/05-verification.md` | Kalite kapıları, deterministik doğrulama |
| 7 | `docs/06-security.md` | Tehdit modeli ve izin sınırları |
| 8 | `docs/07-git-ci.md` | Branch, worktree, commit, CI stratejisi |
| 9 | `docs/08-roadmap.md` | Fazlar ve çıkış kriterleri |
| 10 | `docs/09-workflow.md` | Günlük çalışma akışı — ilk gün ne yapacaksın |
| 11 | `docs/11-verification-backlog.md` | Doğrulanmamış varsayımlar — hangi faz neye bağlı |
| 12 | `docs/12-design-system.md` | Tasarım sistemi, görsel kimlik, UI kalite kapıları |
| 13 | `docs/architecture-review.md` | Red team bulguları ve karar kaydı |
| 14 | `docs/adr/*.md` | Geri dönüşü zor kararların gerekçeleri |

Ürün gerçeği: **`PRODUCT.md`** (kullanıcılar, konumlanış, kanıt, ilkeler).

Agent'lara verilecek kalıcı kurallar ve master promptlar:

| Dosya | Kime |
|---|---|
| `AGENTS.md` | Tüm agent'lar (runtime-bağımsız mühendislik kuralları) |
| `CLAUDE.md` | Claude Code — mimar / gözden geçiren rolü |
| `GEMINI.md` | Gemini CLI — uygulayıcı rolü |
| `prompts/*.md` | Faz bazlı master promptlar |

---

## Uygulamaya geçiş

Devralan için tek giriş noktası: **`HANDOFF.md`**

## Dil politikası

- `docs/**` → **Türkçe.** Birincil okuyucu sensin.
- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `prompts/**` → **İngilizce.**
  Modeller İngilizce talimatı ölçülebilir biçimde daha tutarlı izler ve bu
  dosyalar açık kaynak sürümünde olduğu gibi kalacak.

Açık kaynak yayınında `docs/**` İngilizceye çevrilecek (bkz. Faz 9).

---

## Şu anki durum

Faz: **mimari ve spesifikasyon tamamlandı, uygulama başlamadı.**

İki tur gözden geçirmeden geçti: red team (16 bulgu, 13'ü işlendi) ve kapsam
genişlemesi (otonomi + model bağımsızlığı). 10 ADR, 12 belge, 9 master prompt.

Sıradaki iki adım:

1. **Faz 0 Test 3'ü koş** (`docs/08`): Claude task üretir → Gemini uygular →
   kapılar koşar → Claude inceler → Gemini düzeltir, **insan müdahalesi
   olmadan**. Bu geçmeden hiçbir kod yazılmamalı; ürünün vaadi buna bağlı.
2. `docs/11`'deki doğrulama borcunu kapat — özellikle V3 (Antigravity SDK)
   ve V4 (Claude Agent SDK), çünkü bunlar henüz **duyum** seviyesinde.
3. Bloke eden kararları ver: **D1** (dil), **D2** (referans yığın),
   ardından **D9** (otonomi varsayılanı) ve **D12** (risk kuralları).
