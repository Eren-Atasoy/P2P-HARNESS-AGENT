# Devir Paketi — Uygulamaya Geçiş

Bu belge, uygulamayı devralan agent'ın (veya insanın) tek giriş noktasıdır.

---

## 1. Durum

| | |
|---|---|
| Mimari ve spesifikasyon | **Tamam** — 13 belge, 10 ADR, 10 master prompt |
| Gözden geçirme | **Tamam** — red team (16 bulgu) + kapsam genişlemesi turu |
| Fizibilite koşum takımı | **Tamam** — `experiments/faz0/` |
| Faz 0 Test 3 (otonom döngü) | **GEÇMEDİ** — bkz. §2 |
| Çekirdek kod | **Yok** ve Faz 0 geçmeden yazılmayacak |

## 2. Uygulamayı bloke eden üç şey

Sırayla çözülmeli. Hiçbiri atlanamaz.

### B1 — `gemini` CLI kimlik doğrulaması yok

```
! gemini          → "Login with Google" → AI Ultra hesabı → /quit
```

Doğrulama: `python experiments/faz0/run.py --preflight` (11 sn, model
çağrısı israf etmez).

Detay: `docs/11 V1`. Antigravity'nin kimliği CLI tarafından kullanılmıyor.

### B2 — Faz 0 Test 3 geçmemiş

```
python experiments/faz0/run.py --inject-fault
```

Beklenen: `DONGU KAPANDI - Faz 0 Test 3 GECTI`.

Geçmezse **mimari değil, ürün tanımı** yeniden düşünülür (`docs/08 Faz 0`).
Otonomi vaadi bu döngüye dayanıyor; bir belge onu kanıtlayamaz.

### B3 — İki karar açık

`docs/10-open-decisions.md`:

- **D1** — P2P'nin dili. Öneri ve tüm belgelerin varsayımı: **Python 3.11+**
  (`docs/01 §7`). İtiraz yoksa bu geçerlidir.
- **D2** — Faz 7 referans yığını. Öneri: FastAPI + Next.js + Postgres.
  Faz 7'ye kadar bekleyebilir.

Faz 2'yi bloke edenler: **D9** (otonomi varsayılanı), **D12** (risk kuralları).

## 3. Uygulama sırası

`docs/08-roadmap.md` bağlayıcıdır. Özet:

```
Faz 1  veri modeli + olay deposu + MockRuntime      (~2 gün)
Faz 2  task graph + scheduler + router              (~4 gün)   ─┐ paralel
Faz 4  doğrulama motoru                             (~3 gün)   ─┘ (ikisi de modelsiz)
Faz 3  workspace + git + bootstrap                  (~3 gün)
Faz 5  otonom orchestrator                          (~5 gün)   ← projenin kalbi
Faz 6  planlama zinciri                             (~4 gün)
Faz 7  ilk uçtan uca ürün                           (~5 gün)
```

**Faz 1 ve 2 gerçek model çağırmadan yazılabilir ve test edilebilir.**
Bu tesadüf değil, tasarım: `MockRuntime` Faz 1'de var ki Faz 2'nin testleri
kota harcamasın.

## 4. Uygulayıcıya verilecek prompt

`prompts/08-implement-phase.md`

Kullanım:

```
gemini -p "$(cat prompts/08-implement-phase.md)  Phase: 1" \
  --approval-mode auto_edit
```

`GEMINI.md` ve `AGENTS.md` repo kökünde olduğu için otomatik yüklenir;
prompta kopyalanmaz.

## 5. Değiştirilemeyecek olanlar

Uygulama sırasında bunlara dokunulmaz. Bir tanesi yanlış görünüyorsa yol
ACR'dır (`prompts/acr-template.md`), sessiz düzeltme değil.

| Ne | Nerede |
|---|---|
| `docs/02`'deki alan adları | Birebir bağlayıcı |
| 10 ADR kararı | `docs/adr/` |
| Modül sınırları ve bağımlılık yönü | `docs/01 §3` |
| Kalite kararının deterministikliği | ADR-004 |
| Çekirdekte sağlayıcı/model adı yasağı | ADR-009 |

## 6. İlk gün ne yapılmalı

```
1. ! gemini                                    → giriş yap        (B1)
2. python experiments/faz0/run.py --preflight  → yeşil olmalı
3. python experiments/faz0/run.py --inject-fault → döngü kapanmalı (B2)
4. D1'i onayla veya değiştir                                      (B3)
5. gemini -p "$(cat prompts/08-implement-phase.md) Phase: 1"
```

3. adım geçmeden 5. adıma geçilmez.

## 7. Nerede ne var

```
AGENTS.md              tüm agent'ları bağlayan mühendislik kuralları
CLAUDE.md              mimar/gözden geçiren rolü
GEMINI.md              uygulayıcı rolü — sınırlar, bitti tanımı, risk
docs/00..11            vizyon → mimari → veri modeli → ... → doğrulama borcu
docs/adr/              geri dönüşü zor kararların gerekçeleri
docs/architecture-review.md   iki gözden geçirme turunun bulguları + karar kaydı
prompts/00..08         faz bazlı master promptlar
experiments/faz0/      fizibilite koşum takımı (P2P'nin çekirdeği DEĞİL)
```

Okuma sırası için `README.md`.
