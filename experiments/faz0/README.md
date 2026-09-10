# Faz 0 — Test 3: Otonom Döngü Fizibilitesi

Bu **P2P'nin çekirdeği değildir.** Tek amacı olan, atılabilir bir koşum takımı:

> Claude task üretir → Gemini uygular → kapılar koşar →
> Claude inceler → Gemini düzeltir → kapılar yeşil
>
> **İnsan müdahalesi olmadan.**

Bu döngü kapanmazsa mimari değil, ürün tanımı yeniden düşünülür
(`docs/08 Faz 0`).

## Ne kanıtlıyor

| Ne | Karşılığı |
|---|---|
| `claude -p` headless, yapılandırılmış çıktı yazıyor | `docs/11 V2` |
| `gemini -p` worktree içinde dosya değiştiriyor | `docs/11 V1` |
| Dar kabuk politikası: yalnızca test koşucusu | ADR-008 |
| Onay istemi askıda kalmıyor, hızlı düşüyor | `docs/04 §4` |
| Kapsam ihlali git ile yakalanıyor | `docs/02 §3` |
| Durum 3 kaynaktan türetiliyor (git + kapı + result.json) | C4 |
| Onarım döngüsü kapanıyor | `docs/03 §3` |
| Paralel oturum sınırı | `docs/11 V8` |

## Tasarım kararları

**Testi Claude yazar, uygulamayı Gemini.** `tests/` Gemini'nin
`forbidden_paths`'inde. Bu hem `docs/05 §7`'deki test sahipliği kuralını
uygular hem de Gemini'nin testi kendine uydurmasını fiziksel olarak engeller.
Doğrulama böylece gerçekten bağımsız olur.

**Hata enjekte edilir, beklenmez.** `--inject-fault`, ilk yeşilden sonra
implementasyonu bozar ve döngüyü onarıma zorlar. Onarım döngüsünü modelin
doğal olarak hata yapmasını umarak test etmek, testin kendisini
non-deterministik yapardı.

**Ölçer, varsaymaz.** Her adım artifact bırakır ve koşu sonunda `docs/11`
maddelerine karşılık gelen bir rapor üretir.

## Kullanım

```bash
python experiments/faz0/run.py --preflight        # ücretsiz, model çağırmaz
python experiments/faz0/run.py                    # tam döngü
python experiments/faz0/run.py --inject-fault     # onarım döngüsünü zorla
python experiments/faz0/run.py --concurrency 4    # V8: paralel oturum sınırı
```

Artifact'lar: `experiments/faz0/runs/<timestamp>/`
Çalışma alanı:  `experiments/faz0/workspace/` (her koşuda sıfırlanır)

## Uyarı

Bu script senin aboneliklerini kullanır. Tam döngü tipik olarak 4-8 model
çağrısı yapar. `--preflight` hiç çağrı yapmaz.
