# 05 — Doğrulama Mimarisi

## 1. Temel ilke

> Bir işin geçip geçmediğine **asla bir dil modeli karar vermez.**
> Karar, bir process'in çıkış kodudur.

Dil modeli iki yerde kullanılır ve ikisi de karar noktası değildir:

- **Test yazarken** (kod üretir, sonucu yine kapı doğrular)
- **İnceleme yaparken** (bulgu üretir, kararı orchestrator'ın kuralı verir)

Bu ilkeden sapılan her yerde sistem "kendi ödevini kendi notlandıran" bir
şeye dönüşür ve ürünün tek gerçek farklılaşması yok olur.

## 2. Kapı katmanları

Ucuzdan pahalıya sıralı. Bir katman `FAIL` verirse sonrakiler **çalışmaz**
(fail-fast) — bozuk kodda E2E çalıştırmak dakikaları çöpe atar.

| # | Kapı | Ne yakalar | Tipik süre |
|---|---|---|---|
| 0 | `policy` | İzinsiz yol değişikliği, sır sızıntısı | < 1 sn |
| 1 | `format` | Biçim | saniyeler |
| 2 | `lint` | Kural ihlali, ölü kod | saniyeler |
| 3 | `typecheck` | Tip hatası | saniyeler |
| 4 | `build` | Derleme/paketleme | ~1 dk |
| 5 | `unit` | Birim davranış | ~1 dk |
| 6 | `contract` | API şeması ↔ uygulama uyumu | saniyeler |
| 7 | `integration` | DB + servis birlikte | dakikalar |
| 8 | `migration` | Şema ileri/geri alınabilir mi | dakikalar |
| 9 | `smoke` | Uygulama gerçekten ayağa kalkıyor mu | ~1 dk |
| 10 | `e2e` | Kullanıcı akışı tarayıcıda | dakikalar |
| 11 | `security` | Bilinen zafiyet, sır, bağımlılık | dakikalar |
| 12 | `coverage` | Kapsam eşiği | — |

`a11y` (erişilebilirlik) v1 kapsamında **değildir** — üretilen ürünün
erişilebilirliği v1'de kabul kriteri değil. Faz 9+.

Her task **kendi ilgili kapılarını** çalıştırır (`TaskContract.gates`).
Tüm kapılar yalnızca regresyon aşamasında çalışır.

## 3. En kritik kapı: `smoke`

Deneyimsel olarak, AI üretimi kodun en sık başarısızlık biçimi şudur:
**bütün testler geçer, uygulama açılmaz.** Testler mock'lanmış bir dünyada
çalışır; gerçek başlatma yolu (config, migration, port, bağımlılık sırası)
hiç denenmemiştir.

`smoke` kapısı bunu kapatır:

```
1. docker compose up -d
2. sağlık ucu 200 dönene kadar bekle (zaman aşımı 90 sn)
3. bir "altın yol" isteği at, beklenen şekli doğrula
4. docker compose down
```

Bu kapı olmadan hiçbir görev `DONE` olamaz. Pazarlık konusu değildir.

## 4. `contract` kapısı

API sözleşmesi (`.p2p/docs/api-contract.md` → OpenAPI) ile çalışan uygulamanın
ürettiği şema karşılaştırılır.

Bunun değeri: frontend ve backend **paralel** çalışabilir. Frontend agent'ı
sözleşmeye göre kod yazar; backend agent'ı sözleşmeye göre uygular; kapı
ikisinin buluştuğunu garanti eder. Sözleşme olmadan paralellik, entegrasyon
aşamasında çöken bir yanılsamadır.

## 5. Kapı sonucu → orchestrator aksiyonu

| Sonuç | Aksiyon |
|---|---|
| `PASS` | Sonraki kapı |
| `WARN` | Devam, teknik borç kaydı |
| `FAIL` | Dur, hata sınıflandır, onarım döngüsü |
| `ERROR` | Dur, **ESCALATED** (kod sorunu değil) |
| `SKIPPED` | Devam, ama `DONE` olurken gerekçesi kaydedilir |

`WARN` eşiği ayarlanabilir olmalı: bir proje `coverage < 80` için `WARN`,
başka biri `FAIL` isteyebilir. Bu `.p2p/gates.yaml`'dan gelir.

## 6. Kapı tanımı — deklaratif

Kapılar koda gömülmez; teknoloji yığınına göre veri olarak tanımlanır:

```yaml
gates:
  unit:
    cmd: ["pytest", "-q", "--tb=short", "tests/"]
    cwd: "backend"
    timeout_s: 600
    on_missing_tool: ERROR
    parse: pytest
  typecheck:
    cmd: ["npx", "tsc", "--noEmit"]
    cwd: "frontend"
    timeout_s: 300
    parse: tsc
  smoke:
    cmd: ["docker", "compose", "up", "-d"]
    timeout_s: 600
    isolation: serialized      # kaynak çakışması — bkz. docs/03 §2.5
    parse: none
```

`isolation: serialized` olan kapılar global semaforla sırayla çalışır (C3).
Varsayılan `none`.

`parse` alanı, ham çıktıyı `Failure[]` listesine çeviren ayrıştırıcıyı seçer.
Yapılandırılmış hata olmadan fix promptu kaliteli olamaz — modele 4000 satır
log vermek yerine 3 satır hata vermek, düzeltme başarısını belirgin biçimde
artırır.

## 7. Test kalitesi — sinsi problem

AI, testi kendi kodunu doğrulayacak şekilde yazma eğilimindedir. Bunun
karşı-önlemleri:

| Önlem | Nasıl |
|---|---|
| **Testi başkası yazar** | **Kural (M2):** kabul kriterine bağlı testleri ayrı bir `TEST-` task'ı yazar; `tests/**` o task'ın `allowed_paths`'idir ve uygulayıcının `forbidden_paths`'idir. Uygulayıcı yalnızca kendi iç birim testlerini yazabilir ve **bunlar kabul kriteri sayılmaz** |
| **Kriter izlenebilirliği** | Her AC'nin `test_ref`'i olmalı; olmayan AC `DONE` engeller |
| **Tautoloji taraması** | `assert True`, boş test gövdesi, `expect(x).toBeDefined()` gibi kalıplar lint kuralıyla `FAIL` |
| **Kırmızı-yeşil kanıtı** | Uygulayıcı, testi implementasyon bozukken bir kez çalıştırıp kırmızı gördüğünü beyan eder (`GEMINI.md §3`); bu, ona verilen dar kabuk izninin (ADR-008) tek gerekçesidir |

**Mutasyon testi v1 kapsamında değildir.** Kendi başına bir altyapı yatırımı
gerektirir; "her kabul kriterinin bir `test_ref`'i var mı" kontrolü aynı riskin
çoğunu bedavaya kapatır. Faz 9+.

## 8. Regresyon

Bir task birleştirildikten sonra, o task'ın kapıları değil; **etkilenen
tüm kapılar** çalışır.

Etki hesabı v1'de basit ve muhafazakâr: değişen üst düzey dizine göre.

```
backend/**   → build, unit, contract, integration, smoke, e2e
frontend/**  → build, typecheck, unit, e2e
infra/**     → smoke, e2e
docs/**      → (kapı yok)
```

Muhafazakâr olması bilinçli: gereksiz kapı çalıştırmak zaman kaybı, gerekli
kapıyı atlamak ürün kaybıdır.

## 9. "DONE" tanımı

Bir task ancak şunların **hepsi** doğruyken `DONE` olur:

- [ ] Tüm `gates` `PASS` veya `WARN`
- [ ] Her `acceptance_criteria` için `verified_by` gerçekten koşulmuş
- [ ] `ReviewResult.verdict = APPROVED`, CRITICAL/HIGH bulgu yok
- [ ] `git` doğrulaması temiz: `allowed_paths` dışında değişiklik yok
- [ ] Integration dalına çakışmasız birleşmiş
- [ ] Regresyon kapıları yeşil
- [ ] `human_approval=true` ise insan onaylamış

Bu liste `p2p status <task>` çıktısında birebir gösterilir. Kullanıcı hangi
maddede takıldığını tahmin etmek zorunda kalmamalı.
