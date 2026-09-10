# Prompt2Product

Doğal dildeki bir ürün isteğini, çalışan ve doğrulanmış bir yazılım ürününe
dönüştüren, local-first ve model-bağımsız bir AI ürün mühendisliği platformu.

> **Prompt in. Verified Product out.**

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
| 5 | `docs/04-runtime-adapters.md` | Claude / Gemini adapter sözleşmesi |
| 6 | `docs/05-verification.md` | Kalite kapıları, deterministik doğrulama |
| 7 | `docs/06-security.md` | Tehdit modeli ve izin sınırları |
| 8 | `docs/07-git-ci.md` | Branch, worktree, commit, CI stratejisi |
| 9 | `docs/08-roadmap.md` | Fazlar ve çıkış kriterleri |
| 10 | `docs/09-workflow.md` | Günlük çalışma akışı — ilk gün ne yapacaksın |
| 11 | `docs/architecture-review.md` | Red team bulguları ve karar kaydı |
| 12 | `docs/adr/*.md` | Geri dönüşü zor kararların gerekçeleri |

Agent'lara verilecek kalıcı kurallar ve master promptlar:

| Dosya | Kime |
|---|---|
| `AGENTS.md` | Tüm agent'lar (runtime-bağımsız mühendislik kuralları) |
| `CLAUDE.md` | Claude Code — mimar / gözden geçiren rolü |
| `GEMINI.md` | Gemini CLI — uygulayıcı rolü |
| `prompts/*.md` | Faz bazlı master promptlar |

---

## Dil politikası

- `docs/**` → **Türkçe.** Birincil okuyucu sensin.
- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `prompts/**` → **İngilizce.**
  Modeller İngilizce talimatı ölçülebilir biçimde daha tutarlı izler ve bu
  dosyalar açık kaynak sürümünde olduğu gibi kalacak.

Açık kaynak yayınında `docs/**` İngilizceye çevrilecek (bkz. Faz 9).

---

## Şu anki durum

Faz: **mimari ve spesifikasyon tamamlandı, uygulama başlamadı.**

Sıradaki iki adım:

1. Red team turu **tamamlandı** — `docs/architecture-review.md`, 5 Critical /
   7 Major / 4 Minor bulgu ve karar kaydı içeriyor. 13 bulgu belgelere işlendi.
2. `docs/10-open-decisions.md` içindeki **D1** (dil) ve **D2** (referans yığın)
   kararlarını ver — Faz 1'i bloke ediyorlar.
3. Faz 0'ı koş: `claude -p` ve `gemini -p` doğrulaması + dar kabuk politikasının
   (ADR-008) gerçekten çalıştığının kanıtı.
