# 08 — Yol Haritası

## Prensipler

1. **Her faz çalışan bir şey bırakır.** Yarım bırakılan faz yoktur.
2. **Çıkış kriteri gözlemlenebilirdir.** "Tamamlandı" bir komutun çıktısıdır.
3. **Doğrulanmamış varsayım üstüne faz kurulmaz.** `docs/11`'deki bir madde
   `DOĞRULANDI` olmadan ona dayanan iş başlamaz.
4. **Fantezi paralellik yok.** Tek kişi + eldeki runtime'lar varsayımıyla.
5. **Dogfooding Faz 9'dan sonra başlar.** P2P bir Python CLI'dır; kendi türünde
   proje üretebilmesi için ikinci bir Blueprint gerekir.

Süre tahminleri odaklanmış tek kişilik çalışma içindir; takvim değil,
**sıralama** bağlayıcıdır.

---

## Faz 0 — Runtime fizibilitesi  (~1-2 gün)

**Amaç:** Tüm planın dayandığı varsayımları kanıtlamak; `docs/11`'deki
doğrulama borcunu kapatmak.

### Test 1 — Claude runtime
`claude -p` task kabul ediyor · dosya okuyabiliyor · belirtilen yola JSON
sonuç yazıyor · yazma izni `.p2p/docs/**` ile sınırlanabiliyor.

### Test 2 — Gemini runtime
`gemini -p` bir `git worktree` içinde çalışıyor · dosya değiştirebiliyor ·
`--policy` ile **yalnızca test koşucusunu** çalıştırabiliyor, başka komutu
çalıştıramıyor (ADR-008) · yapılandırılmış sonuç yazıyor · onay istemi
geldiğinde askıda kalmıyor.

### Test 3 — Otonom döngü MVP'si (kritik)
```
Claude task üretir -> Gemini uygular -> kapılar koşar ->
Claude inceler -> Gemini düzeltir -> kapılar yeşil
```
**İnsan müdahalesi olmadan.** Elle yazılmış bir script yeterli; amaç mimariyi
değil, **döngünün fiziksel olarak mümkün olduğunu** kanıtlamak.

### Ek doğrulamalar
`docs/11`: V3 (Antigravity SDK), V4 (Claude Agent SDK), V7 (sandbox),
V8 (paralel oturum sınırı).

**Çıkış kriteri:** Test 3 geçiyor. Bu an, tam otonomi vaadinin ilk teknik
kanıtıdır; geçmezse mimari değil **ürün tanımı** yeniden düşünülür.

**Risk:** Sağlayıcı CLI'ları beklenen davranışı göstermeyebilir → adapter
tasarımı değişir, çekirdek mimari değişmez (`docs/04 §4`).

---

## Faz 1 — Çekirdek veri modeli ve olay deposu  (~2 gün)

- `docs/02`'deki tüm modeller (Pydantic), `Connection` dâhil
- Append-only olay yazıcı (tek yazar, kilitli) + state türetici
- `MockRuntime`
- `p2p status`

**Çıkış:** Elle yazılmış 5 olaydan doğru `state.json` türetiliyor; süreç
öldürülüp yeniden başlatıldığında aynı state çıkıyor. Testler gerçek model
çağırmıyor.

---

## Faz 2 — Task graph, scheduler ve router  (~4 gün)

- Bağımlılık çözümü, çevrim tespiti
- `allowed_paths` çakışma analizi, dalga hesabı
- Durum makinesi + geçiş doğrulama
- Retry/escalation sayaçları, ilerleme kontrolü
- **Capability router:** uygunluk süzgeci + puanlama, `UNROUTABLE` (`docs/04 §5`)
- **Risk seviyeleri ve otonomi modları** (`docs/03 §5`)

**Çıkış:** `MockRuntime` ile 10 task'lık sentetik graph doğru sırayla ve doğru
paralellikte koşuyor; enjekte edilen hata doğru escalate oluyor; yeteneği
karşılanmayan task `UNROUTABLE` veriyor; `high` risk task'ı `full` modda bile
insan kapısına takılıyor. **Bu faz tamamen modelsiz test edilebilir olmalı.**

Faz 2 ve Faz 4 paralel ilerleyebilir.

---

## Faz 3 — Workspace, git ve bootstrap  (~3 gün)

- Worktree yaşam döngüsü, dal politikası
- Commit üretimi, birleştirme sırası, çakışma tespiti
- `git status` doğrulaması (kapsam ihlali yakalama)
- **`WORKSPACE_BOOTSTRAP`:** iskelet, bağımlılık kurulumu (lock'tan),
  veritabanı ayağa kaldırma, migration, boş proje smoke testi
- Worktree'ler arası bağımlılık dizini paylaşımı (cache)

**Çıkış:** İki sahte task paralel worktree'de çalışıp `integration`'a
çakışmasız birleşiyor; kapsam dışına yazan task yakalanıp geri alınıyor; boş
projede bootstrap sonrası kapılar `ERROR` değil `PASS`/`FAIL` veriyor.

---

## Faz 4 — Doğrulama motoru  (~3 gün)

- Deklaratif kapı tanımı, çalıştırıcı, zaman aşımı, `isolation: serialized`
- `pytest` / `tsc` / `eslint` / `ruff` çıktı ayrıştırıcıları
- `smoke` kapısı (docker compose)
- `FAIL` / `ERROR` / `QUOTA` ayrımı, hata sınıflandırma

**Çıkış:** Bilerek bozulmuş örnek projede her kapı doğru sınıfla düşüyor;
`Failure[]` yapılandırılmış üretiliyor; iki paralel task'ın `smoke` kapısı
birbirini bozmuyor.

---

## Faz 5 — Otonom orchestrator  (~5 gün)

Projenin kalbi. Faz 1-4'ün parçalarını, kapanana kadar dönen tek bir döngüde
birleştirir (`docs/03 §7`).

- Gerçek adapterlar: `ClaudeCodeRuntime`, `GeminiCliRuntime`
- Prompt derleme katmanları + bağlam bütçesi
- Dar kabuk politikası (ADR-008), onay-istemi davranışı
- `routing.yaml`, `Connection` sağlığı, `p2p doctor`, maliyet günlüğü
- **Otonom yürütme döngüsü:** dispatch, verify, review, repair, devam
- Döngü sonlandırma: tamamlandı / kilitlendi / insan bekliyor / bütçe doldu
- İlerleme yok tespiti
- **`p2p steer`** — escalate olmuş task'a insan yönlendirmesini `Decision`
  olarak enjekte etme (`docs/03 §3.5`)

**Çıkış:** Elle yazılmış 3 task'lık bir graph `--autonomy full` ile **baştan
sona insan müdahalesi olmadan** koşuyor; en az bir task doğal olarak fix
döngüsüne girip çıkıyor; `p2p status` kimin adına hangi kararın verildiğini
gösteriyor.

---

## Faz 6 — Planlama zinciri  (~4 gün)

- Discovery, belirsizlik çıkarımı, G1
- Mimari üretimi, G2
- Task graph üretimi (risk seviyeleri dâhil), G3
- ACR mekanizması uçtan uca

**Çıkış:** `p2p new "basit bir yapılacaklar API'si"` sonucunda onaylanmış bir
task graph.

---

## Faz 7 — İlk uçtan uca ürün  (~5 gün)

Tek hedef: **tek promptan çalışan ürün.**

Referans senaryo: kimlik doğrulamalı, PostgreSQL'li, Docker'la ayağa kalkan
randevu API'si + minimal web arayüzü.

**Çıkış:** `p2p new "..."` sonrası `docker compose up` ile ürün tarayıcıda
çalışıyor; tüm kapılar yeşil; `.p2p/` silindiğinde proje normal repo olarak
çalışmaya devam ediyor.

**Risk (en yüksek):** Üretilen kod entegrasyonda dağılabilir. Azaltma:
`contract` ve `smoke` kapıları Faz 4'te hazır olduğu için sorun erken görünür.

---

## Faz 8 — Tarayıcı doğrulama ve regresyon  (~3 gün)

- Playwright `e2e` kapısı, kullanıcı akışı üretimi
- Etki tabanlı regresyon seçimi
- Tautoloji taraması (sahte test yakalama)
- **`p2p retro`** — olay günlüğünden tekrarlayan hata kalıplarını çıkarma ve
  kural/kapı önerisi üretme (`docs/03 §8`)

**Çıkış:** Bir kabul kriterini bilerek bozmak E2E'yi kırmızı yapıyor ve doğru
task'ı yeniden açıyor.

---

## Faz 9 — Genişletilebilirlik ve açık kaynak  (~5 gün)

Model-bağımsızlık iddiasının **kanıtlandığı** faz. Üçüncü bir adapter çekirdeğe
dokunmadan eklenene kadar bu bir iddiadır, gerçek değil.

- **`ApiRuntime`** (OpenAI-uyumlu) — `Connection(kind=api)` kanıtı
- **`OllamaRuntime`** — `Connection(kind=local)` kanıtı
- Blueprint arayüzü; ikinci yığın **Python CLI** olarak sabitlenir
- Eklenti arayüzleri: RuntimeAdapter, QualityGate, Blueprint
- Lisans, katkı rehberi, issue/PR şablonları, `docs/**` İngilizce
- `p2p audit`, güvenlik sertleştirme, `a11y` kapısı, mutasyon testi
- Sürümleme ve yayın süreci

**Çıkış:** Başka biri README'yi takip ederek kendi makinesinde ürün
üretebiliyor; yeni bir runtime'ı çekirdeğe dokunmadan ekleyebiliyor;
`grep -r` çekirdek kaynakta hiçbir sağlayıcı veya model adı bulmuyor.

---

## Faz 10 — Kendini geliştirme (tam dogfooding)

P2P'nin yeni özellikleri P2P ile geliştirilir. Hem en güçlü kanıt hem en
acımasız kalite testi.

**Çıkış:** P2P'ye eklenen bir özelliğin tamamı P2P tarafından planlanmış,
uygulanmış, doğrulanmış ve birleştirilmiş; `git log` bunu gösteriyor.

---

## Kritik yol

```
0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10
          Faz 2 ve Faz 4 paralel (ikisi de modelsiz)
```

## En büyük dört risk

| Risk | Neden ölümcül | Azaltma |
|---|---|---|
| **Otonom döngü kapanmıyor** (Faz 0 Test 3) | Ürün vaadinin kendisi | Faz 0'da, kod yazmadan önce kanıtlanır |
| **Entegrasyon çöküşü** | Vaadi doğrudan yok eder | `contract` + `smoke` erken (Faz 4), sözleşme-önce paralellik |
| **Sağlayıcı CLI değişimi** | Adapter kırılır | Dar adapter yüzeyi, `MockRuntime` ile test, `p2p doctor` erken uyarı |
| **Kapsam kayması** | Faz 7'ye hiç ulaşılamaz | `docs/00 §6`; girmek ADR gerektirir |
