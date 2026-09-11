# 07 — Git ve CI/CD Stratejisi

## 1. Git neden birinci sınıf

Git, P2P için sadece sürüm kontrolü değil; **izolasyon, geri alma ve
denetlenebilirlik** mekanizmasıdır. Task izolasyonu worktree ile, geri alma
commit ile, denetim geçmiş ile sağlanır. Bu üçünü kendimiz yazmıyoruz.

## 2. Dal modeli

```
main                    ← yalnızca yayınlanmış, tüm kapıları geçmiş durumlar
  └── p2p/integration   ← task'ların birleştiği çalışma dalı
        ├── p2p/task/DB-001
        ├── p2p/task/API-001
        └── p2p/task/UI-001
```

| Dal | Kim yazar | Koruma |
|---|---|---|
| `main` | Yalnızca yayın adımı, insan onayıyla | `push --force` yasak, doğrudan commit yasak |
| `p2p/integration` | Orchestrator (merge) | Yalnızca APPROVED task'lar |
| `p2p/task/<id>` | Orchestrator (agent adına) | Task bitince silinir |

Agent'ın kendisi **hiçbir git komutu çalıştırmaz** (`docs/06 §6`).

## 3. Commit kuralları

Task başına bir commit tercih edilir; fix turları `--amend` yerine ek commit
olarak kalır (denetim izi değerlidir), birleştirme sırasında squash edilir.

```
<type>(<task-id>): <özet>

<intent'ten türetilmiş 1-3 cümle>

Acceptance:
  - AC-1 ✓ tests/api/test_appointments.py::test_create_returns_201
  - AC-2 ✓ tests/api/test_appointments.py::test_requires_auth

Gates: lint ✓ typecheck ✓ unit ✓ contract ✓
Runtime: gemini  Attempt: 1
```

Bu biçim bilinçli: altı ay sonra `git log` okuyan biri, o değişikliğin
**neden** yapıldığını ve **nasıl doğrulandığını** modele sormadan görebilir.

Commit mesajının özet satırı task `intent`'inden türetilir; `Acceptance` ve
`Gates` satırları **orchestrator tarafından** doldurulur — modele bırakılmaz,
çünkü bunlar gerçeğin kaydıdır.

## 4. Worktree yaşam döngüsü

```
oluştur   git worktree add .p2p/wt/<id> -b p2p/task/<id> p2p/integration
çalış     agent worktree içinde
doğrula   kapılar worktree içinde
birleştir git merge --no-ff p2p/task/<id>   (integration üzerinde)
temizle   git worktree remove + dal sil
```

Başarısız task'ın worktree'si **silinmez**, `.p2p/wt/failed/<id>` altına
taşınır. İnceleme için gereklidir; `p2p clean` ile temizlenir.

## 5. CI: harici doğrulama değil, durum geçişi

Bu belgenin en önemli kararı.

CI, "commit'ten sonra çalışan ayrı bir şey" olarak konumlandırılırsa,
orchestrator'ın gerçeklik algısı CI'dan kopar: yerelde yeşil, CI'da kırmızı
bir dünya oluşur ve kimse hangisinin doğru olduğunu bilmez.

**v1 kararı (M3): CI harici doğrulamadır, `DONE` koşulu DEĞİLDİR.**

Yukarıdaki gerileme riski gerçek, ama v1'de bedeli daha yüksek: CI'yı durum
makinesine bağlamak uzak repo + `gh` kimlik doğrulaması + sonuç yoklama
döngüsü demek ve roadmap'te bunu üstlenen bir faz yok. Uygulanmayacak bir
zorunluluk yazmak, hiç yazmamaktan kötüdür.

Riski kapatan şey şu: **yerel kapılar ve CI kapıları aynı deklaratif tanımdan
üretilir** (`.p2p/gates.yaml` → GitHub Actions iş adımları). Aynı komut, aynı
sıra, aynı ayrıştırıcı. Ayrışma ancak ortam farkından doğabilir, tanım
farkından doğamaz.

**v2'ye ertelenen karar:** CI sonucunun bir durum geçişi hâline getirilmesi.
O noktada `docs/03`'e `CI_PENDING` durumu eklenecek.

## 6. CI iş akışı (üretilen proje)

```
on: [push, pull_request]

jobs:
  verify:
    - checkout
    - setup (dil çalışma ortamı, cache)
    - install (lock dosyasından, --frozen)
    - policy      ← sır taraması
    - lint
    - typecheck
    - build
    - unit
    - contract
    - integration (servis konteynerleriyle)
    - smoke
    - e2e         ← yalnızca PR ve main
    - security
    - artifact yükle (log, ekran görüntüsü, kapsam)
```

İki kural:

1. **Adım isimleri kapı isimleriyle birebir aynı.** Böylece CI çıktısı
   `GateResult` olarak ayrıştırılabilir.
2. **Kapılar makinede de tek komutla çalışabilmeli.** "Sadece CI'da çalışan"
   bir kapı, hata ayıklanamaz bir kapıdır.

## 7. GitHub Issues ve PR Tabanlı İş Yönetimi (Work Management)

Git ve `.p2p/events.jsonl`, sistemin **makine icra gerçeği** iken; GitHub Issues ve PR'lar sistemin **insan işbirliği ve görünürlük katmanı**dır.

### Üç Ayrı Gerçeklik Katmanı

| Veri | Doğruluk Kaynağı (Source of Truth) | Sorumlu |
|---|---|---|
| Kaynak Kod | **Git** | GitManager / Orchestrator |
| İcra Durumu (Execution State) | **`.p2p/events.jsonl`** | Tek Yazar (Orchestrator) |
| Mimari Sözleşmeler | **`docs/adr/`** | Mimar / İnsan |
| Görev Sözleşmesi | **`.p2p/tasks/*.json`** | Orchestrator |
| İnsan Görünür Backlog | **GitHub Issues** (veya `.p2p/issues/`) | IssueProvider / Orchestrator |
| Kod İnceleme & Tartışma | **GitHub PRs** | GitHubPRProvider / Orchestrator |
| Harici Doğrulama | **GitHub Actions (CI)** | GitHub Actions Runner |

> **Altın Kural:** Agent'lar (Claude veya Gemini) doğrudan GitHub API veya Git komutu çalıştırmaz. Claude yalnızca `ReviewResult` üretir. Issue açma, etiketleme ve PR oluşturma yetkisi **yalnızca Orchestrator'ın `GitHubAdapter` bileşenindedir**.

### Otonom Düzeltme ve İnceleme Döngüsü

```text
                  GEMINI
                    │
              implementation
                    │
                    ▼
               Task PR (p2p/task -> integration)
                    │
                    ▼
             deterministic CI
                    │
                    ▼
                 CLAUDE
                  review
                    │
              ┌─────┴─────┐
              │           │
            PASS         FAIL
              │           │
              ▼           ▼
            merge     GitHub Issue (Otomatik oluşturulur)
                          │
                          ▼
                     Repair Task (TaskContract)
                          │
                          ▼
                       GEMINI
                          │
                          ▼
                      Fix PR (#Fixes issue)
                          │
                          ↺
```

### Dal ve PR Ayrımı

Mimaride iki seviyeli PR modeli uygulanır:

1. **Task PR'ları (`p2p/task/<id>` → `p2p/integration`):**
   - Her görev tamamlandığında açılır.
   - İlgili GitHub Issue ile bağlanır (`Fixes #43`).
   - CI ve Claude Review bu PR üzerinde koşar. Merge edildiğinde ilgili Issue otomatik kapanır.
2. **Release PR (`p2p/integration` → `main`):**
   - Tüm task graph dalgası tamamlandığında açılır.
   - Ürün özeti, kabul kriteri tablosu, kapı durumları ve sürüm notlarını içerir.
   - **Yalnızca insan onayıyla** `main`'e birleştirilir.

### Standart Issue Şablonu ve Etiketler

Claude'un `ReviewResult`'ındaki bulgular (Finding) orchestrator tarafından standart bir GitHub Issue'ya dönüştürülür:

```markdown
## Problem
Refresh token rotation is not implemented.

## Severity
HIGH

## Evidence
backend/auth/token_service.py:84

## Acceptance Criteria
- [ ] Old refresh token becomes invalid
- [ ] New refresh token is generated
- [ ] Reuse is rejected
- [ ] Tests cover rotation

## Source
Task: API-042 | Attempt: 2
```

**Standart Etiketler (Labels):**
- **Tür:** `p2p:bug`, `p2p:feature`, `p2p:architecture`, `p2p:security`, `p2p:tech-debt`
- **Öncelik:** `priority:critical`, `priority:high`, `priority:medium`, `priority:low`
- **Hedef Agent:** `agent:gemini`, `agent:claude`
- **Durum:** `status:ready`, `status:in-progress`, `status:review`, `status:blocked`

### Local-First Prensibi (`IssueProvider` Soyutlaması)

GitHub bir zorunluluk (hard dependency) değildir. Sistem çevrimdışı veya GitHub olmadan da çalışır:

```text
IssueProvider (Interface)
   ├── LocalIssueStore     (v1: .p2p/issues/*.json — çevrimdışı / local-first)
   └── GitHubIssueProvider (gh CLI / GitHub REST API — insan işbirliği ve sync)
```

`p2p run --provider local` yerel dizini; `p2p run --provider github` uzak depoyu senkronize eder.

## 8. CD — provider-nötr

v1 **deploy etmez**, deploy edilebilir **artifact üretir**:

```
kod → build → konteyner imajı → (kayıt defteri) → [insan] → hedef
```

Üretilen `infra/` içeriği:

- `Dockerfile` (çok aşamalı, root olmayan kullanıcı)
- `docker-compose.yml` (yerel geliştirme, gerçek bağımlılıklarla)
- `.env.example`
- `docs/deployment.md` — hedefe özgü olmayan, elle uygulanabilir talimat

Hedef-özel yapılandırma (Fly, Render, Vercel, VPS) **Blueprint eklentisi**
olarak Faz 9'da gelir. Çekirdeğe hiçbir sağlayıcı adı girmez.

## 9. Geri alma

| Seviye | Mekanizma |
|---|---|
| Task | Worktree at, dalı sil, task `READY` |
| Birleştirme | `git revert` merge commit (reset değil — geçmiş korunur) |
| Proje | `.p2p/events.jsonl` + git geçmişi ile herhangi bir noktaya bakılabilir |

`git reset --hard` orchestrator tarafından **yalnızca task worktree'sinde**
kullanılır; `integration` veya `main` üzerinde asla.
