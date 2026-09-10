# 08 — Yol Haritası

## Prensipler

1. **Her faz çalışan bir şey bırakır.** Yarım bırakılan faz yoktur.
2. **Çıkış kriteri gözlemlenebilirdir.** "Tamamlandı" bir komutun çıktısıdır.
3. **Fantezi paralellik yok.** Tek kişi + iki agent varsayımıyla planlandı.
4. **Dogfooding Faz 6'da başlar**, önce değil. Çalışmayan bir aracı kendini
   geliştirmek için kullanmak, iki problemi birbirine düğümler.

Süre tahminleri tek kişilik odaklanmış çalışma içindir; takvim değil, sıralama
bağlayıcıdır.

---

## Faz 0 — Doğrulama ve iskele  (~1 gün)

**Amaç:** Tüm planın dayandığı varsayımları kanıtlamak.

Yapılacaklar:
- `claude -p` ve `gemini -p` headless çalışıyor mu, JSON dönüyor mu
- Her ikisi de belirtilen dizine dosya yazabiliyor mu, izin promptunda takılıyor mu
- Bir `git worktree` içinde `gemini -p` çalışıyor mu
- `--approval-mode auto_edit` gerçekten kabuk komutunu engelliyor mu
- Repo iskeleti, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` yerinde

**Çıkış kriteri:** Elle yazılmış tek bir kabuk komutu, bir worktree'de
`gemini`ye dosya yazdırıp `result.json` üretiyor; `claude` o dosyayı okuyup
inceleme JSON'u yazıyor.

**Risk:** Sağlayıcı CLI'ları beklenen bayrakları desteklemiyor olabilir →
adapter tasarımı değişir, mimari değişmez.

---

## Faz 1 — Çekirdek veri modeli ve olay deposu  (~2 gün)

- `docs/02`'deki tüm modeller (Pydantic)
- Append-only olay yazıcı + state türetici
- `mock` runtime adapter'ı
- `p2p status`

**Çıkış:** Elle yazılmış 5 olaydan doğru `state.json` türetiliyor; süreç
öldürülüp yeniden başlatıldığında aynı state çıkıyor. Testler gerçek model
çağırmıyor.

---

## Faz 2 — Task graph ve scheduler  (~3 gün)

- Bağımlılık çözümü, çevrim tespiti
- `allowed_paths` çakışma analizi, dalga hesabı
- Durum makinesi + geçiş doğrulama
- Retry/escalation sayaçları, ilerleme kontrolü

**Çıkış:** `mock` runtime ile 10 task'lık sentetik bir graph, doğru sırayla ve
doğru paralellikte koşuyor; enjekte edilen hata doğru şekilde escalate oluyor.
**Bu faz tamamen modelsiz test edilebilir olmalı.**

---

## Faz 3 — Workspace ve git yöneticisi  (~2 gün)

- Worktree yaşam döngüsü, dal politikası
- Commit üretimi, birleştirme sırası, çakışma tespiti
- `git status` doğrulaması (kapsam ihlali yakalama)
- **`WORKSPACE_BOOTSTRAP` aşaması (C5):** iskelet, bağımlılık kurulumu
  (lock'tan), veritabanı ayağa kaldırma, migration, boş proje smoke testi.
  Task graph'ın parçası değil, ondan önce gelen orchestrator adımı; `GUARDED`
  sınıfında çalışır
- Worktree'ler arası bağımlılık dizini paylaşımı (cache) — dört paralel
  worktree'de dört `node_modules` ilk gerçek koşuda hissedilir

**Çıkış:** İki sahte task paralel worktree'de çalışıp `integration`'a
çakışmasız birleşiyor; kapsam dışına yazan sahte task yakalanıp geri alınıyor;
**boş bir projede bootstrap sonrası tüm kapılar `ERROR` değil `PASS`/`FAIL`
veriyor.**

---

## Faz 4 — Doğrulama motoru  (~3 gün)

- Deklaratif kapı tanımı, çalıştırıcı, zaman aşımı
- `pytest`/`tsc`/`eslint`/`ruff` çıktı ayrıştırıcıları
- `smoke` kapısı (docker compose)
- `FAIL` vs `ERROR` ayrımı, hata sınıflandırma

**Çıkış:** Bilerek bozulmuş bir örnek projede her kapı doğru sınıfla düşüyor;
`Failure[]` yapılandırılmış olarak üretiliyor.

---

## Faz 5 — Gerçek runtime adapterları  (~3 gün)

- `claude` adapter (mimar/gözden geçiren, yazma kısıtlı)
- `gemini` adapter (uygulayıcı, worktree kapsamlı)
- Dar kabuk politikası (ADR-008) ve onay-istemi davranışı (C1)
- Prompt derleme katmanları + bağlam bütçesi
- `routing.yaml`, `p2p doctor`, maliyet günlüğü

**Çıkış:** Elle yazılmış tek bir `TaskContract`, uçtan uca
implement → verify → review → merge döngüsünden geçiyor. **İlk gerçek yeşil task.**

---

## Faz 6 — Planlama zinciri  (~4 gün)

- Discovery → belirsizlik çıkarımı → insan kapısı (G1)
- Mimari üretimi → G2
- Task graph üretimi → G3
- ACR mekanizması uçtan uca

**Çıkış:** `p2p new "basit bir yapılacaklar API'si"` → onaylanmış task graph.

Dogfooding **burada başlamaz** (M4): P2P bir Python CLI'dır ve o türde proje
üretebilmesi için ikinci bir Blueprint gerekir — o da Faz 9'da geliyor.

---

## Faz 7 — İlk uçtan uca ürün  (~5 gün)

Tek hedef: **tek promptan çalışan bir ürün.**

Referans senaryo: kimlik doğrulamalı, PostgreSQL'li, Docker'la ayağa kalkan
bir randevu API'si + minimal web arayüzü.

**Çıkış:** `p2p new "..."` → `docker compose up` → tarayıcıda çalışıyor;
tüm kapılar yeşil; `.p2p/` silindiğinde proje normal repo olarak çalışmaya
devam ediyor.

**Risk (en yüksek):** Üretilen kod entegrasyon aşamasında dağılabilir.
Azaltma: `contract` ve `smoke` kapıları Faz 4'te hazır olduğu için sorun
erken görünür.

---

## Faz 8 — Tarayıcı doğrulama ve regresyon  (~3 gün)

- Playwright `e2e` kapısı, kullanıcı akışı üretimi
- Etki tabanlı regresyon seçimi
- Tautoloji taraması (sahte test yakalama)

**Çıkış:** Bir kabul kriterini bilerek bozmak, E2E'yi kırmızı yapıyor ve
doğru task'ı yeniden açıyor.

---

## Faz 9 — Açık kaynak sertleştirme  (~4 gün)

- Blueprint arayüzü — ikinci yığın **Python CLI** olarak sabitlenir. Böylece
  hem arayüz kanıtlanır hem Faz 10'daki dogfooding mümkün hâle gelir (M4)
- Eklenti arayüzleri: RuntimeAdapter, QualityGate, Blueprint
- Lisans, katkı rehberi, issue/PR şablonları, `docs/**` İngilizce
- `p2p audit`, güvenlik sertleştirme
- Sürümleme ve yayın süreci

**Çıkış:** Başka bir kişi, README'yi takip ederek kendi makinesinde bir ürün
üretebiliyor ve yeni bir kapıyı çekirdeğe dokunmadan ekleyebiliyor.

---

## Faz 10 — Kendini geliştirme (tam dogfooding)

P2P'nin yeni özellikleri P2P ile geliştirilir. Bu, hem en güçlü pazarlama
kanıtı hem de en acımasız kalite testidir.

**Çıkış:** P2P'ye eklenen bir özelliğin tamamı, P2P tarafından planlanmış,
uygulanmış, doğrulanmış ve birleştirilmiş; `git log` bunu gösteriyor.

---

## Kritik yol

```
0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10
```

Faz 2 ve 4 **paralel** ilerleyebilir (ikisi de modelsiz). Bunun dışında
sıralama bağlayıcıdır: her faz bir öncekinin çıkış kriterine dayanır.

## En büyük üç risk

| Risk | Neden ölümcül | Azaltma |
|---|---|---|
| **Entegrasyon çöküşü** (parçalar tek tek çalışır, birlikte çalışmaz) | Ürün vaadini doğrudan yok eder | `contract` + `smoke` kapıları erken (Faz 4), sözleşme-önce paralellik |
| **Sağlayıcı CLI değişimi** | Adapter kırılır | Adapter yüzeyi dar, `mock` ile test, `p2p doctor` erken uyarı |
| **Kapsam kayması** (bulut, UI, çoklu yığın erken) | Faz 7'ye hiç ulaşılamaz | `docs/00 §6` kapsam dışı listesi; girmek ADR gerektirir |
