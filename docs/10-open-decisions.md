# 10 — Senin Karar Vermen Gereken Noktalar

Bu belge, mimarinin **bilinçli olarak açık bıraktığı** kararları listeler.
Hiçbiri varsayılanla geçilmemeli; her biri Faz 1 başlamadan cevaplanmalı.

Her karar verildiğinde buraya cevabı + gerekçesi yazılır ve gerekiyorsa bir
ADR açılır. Cevaplanmamış bir karar, ilerideki bir task'ın sessizce yanlış
varsayım yapması demektir.

---

## D1 — P2P'nin kendi dili: Python mı, TypeScript mi?

**Öneri: Python 3.11+** (`docs/01 §7` gerekçesi).

Karşı argüman: `gemini-cli` Node ekosisteminde; ileride onun SDK'sına
bağlanmak istersen Node avantajlı olur.
Karşı-karşı argüman: Adapter zaten subprocess; SDK'ya bağlanmak `RuntimeAdapter`
içinde izole bir değişiklik.

**Neden şimdi karar vermelisin:** Faz 1'in ilk satırı bu dile yazılıyor.
Sonradan değiştirmek her şeyi yeniden yazmak demek.

- [x] Karar: Python 3.11+ (Pydantic v2 + Typer + Pytest). Gerekçe: CLI orkestrasyonu, veri modelleri doğrulama katılığı, subprocess yönetimi ve test altyapısı için en verimli ve olgun ortam. Üretilecek nihai ürünlerin dili ise kullanıcı ve Blueprint seçimine bırakılmıştır. (2026-09-11)

---

## D2 — İlk hedef teknoloji yığını (referans ürün için)

> **KISMEN KAPANDI (2026-09-10).** Frontend tarafı `docs/12-design-system.md`
> ile bağlandı: **Next.js 15 (App Router) · TypeScript strict · Tailwind CSS ·
> Radix UI primitives (shadcn/ui deseni) · Lucide**.
>
> Backend ve veritabanı hâlâ açık (öneri: FastAPI + Postgres) ve Faz 7'ye kadar
> bekleyebilir. Ayrım bilinçli: frontend standardı **şimdi** gerekiyordu çünkü
> tasarım sistemi ona bağlı; backend seçimi Faz 7'den önce gerekmiyor.
>
> Aşağıdaki değerlendirme, kararın nasıl verildiğinin kaydı olarak duruyor.

Faz 7'de üreteceğimiz ilk gerçek ürünün yığını. Blueprint mimarisi çoklu yığını
destekleyecek ama **birincisi** en olgun olan olmalı.

| Seçenek | Artı | Eksi |
|---|---|---|
| FastAPI + Next.js + Postgres | AI'lar en iyi bu kombinasyonu üretiyor; test araçları olgun | İki dil, iki ekosistem |
| Next.js full-stack + Postgres | Tek dil, tek build, daha az entegrasyon yüzeyi | Backend ağırlaştıkça sıkışır |
| .NET + Next.js | Senin mevcut deneyimin | AI üretim kalitesi ve topluluk örnekleri daha zayıf |

**Öneri:** FastAPI + Next.js + Postgres. Gerekçe: uygulayıcı bir AI modeli;
onun en güvenilir ürettiği ve doğrulama araçlarının en olgun olduğu yığını
seçmek, senin kişisel tercihinden daha ağır basar.

- [ ] Karar: ______

---

## D3 — Mobil hedef v1'de var mı?

Şu an `docs/00 §6`'da kapsam dışı. Mobil eklemek: ayrı build zinciri, emülatör
tabanlı E2E, mağaza imzalama — doğrulama maliyetini kabaca ikiye katlar.

**Öneri:** v1 web + API. Mobil, Faz 9'dan sonra bir Blueprint olarak.
Ürün vaadin "mobil dahil" ise bunu **pazarlama** değil **roadmap** kararı
olarak vermelisin.

- [ ] Karar: ______

---

## D4 — Açık kaynak lisansı

| Seçenek | Sonuç |
|---|---|
| MIT / Apache-2.0 | En geniş benimseme; herkes ticarileştirebilir |
| AGPL-3.0 | Barındıran rakip kaynak açmak zorunda; kurumsal benimseme düşer |
| Elastic / BSL | "Açık kaynak" değil; topluluk tepkisi riski |

**Öneri:** Apache-2.0. Gerekçe: yerel çalışan bir CLI için "rakip bunu SaaS
yapar" riski zaten düşük; asıl risk benimsenmemek. Patent hükmü MIT'e üstünlük
sağlar.

Bu karar, `docs/00 §4`'teki ticari katman ayrımını etkiler.

- [ ] Karar: ______

---

## D5 — Proje adı ve alan adı

`Prompt2Product` tanımlayıcı ama jenerik ve arama sonuçlarında zayıf.
Faz 9'dan (açık kaynak yayını) önce kararlaştırılmalı — sonrası yeniden
adlandırma maliyeti taşır.

**Durum (2026-09-10):** kullanıcı kararı erteledi. `PRODUCT.md` → Brand
Commitments bunu **çalışma adı** olarak kaydetti: hiçbir logo, wordmark veya
görsel iş bu isim üzerine kurulamaz.

- [ ] Karar: ______

---

## D6 — Kullanıcı kimlik bilgisi modeli (ürün tarafı)

`docs/00 §4.2` BYOC diyor. Somutlaştırılması gereken:

- Kullanıcının hangi CLI'ları kurmuş olması gerekiyor?
- Hiçbiri yoksa ne olur — kurulum yönlendirmesi mi, yerel model desteği mi?
- API anahtarı tabanlı kullanıcılar için ayrı bir adapter yazılacak mı?

**Öneri:** v1 için `claude` **veya** `gemini`den en az biri zorunlu; `p2p doctor`
eksik olanı bildirir ve `routing.yaml`'ı mevcut olanlara göre daraltır.

- [ ] Karar: ______

---

## D7 — Telemetri

Hangi promptların çalıştığını öğrenmek ürünü iyileştirir; ama local-first
vaadiyle gerilim yaratır.

**Öneri:** v1'de telemetri **yok**. Yerel `p2p cost` ve olay günlüğü zaten
ihtiyacın olan veriyi veriyor. Uzak telemetri, ancak açık opt-in ve ne
gönderildiğinin tam listesiyle.

- [ ] Karar: ______

---

## D8 — Test kapsam eşiği

`AGENTS.md` %80 demiyor; bilinçli. Üretilen projede kapsam eşiği ne olmalı ve
`WARN` mı `FAIL` mi?

**Öneri:** `coverage < 70` → `FAIL`, `70-85` → `WARN`. Gerekçe: kapsam bir
kalite göstergesi değil, bir yokluk göstergesidir. Yüksek eşik, modeli anlamsız
test yazmaya iter — `docs/05 §7`'deki mutasyon örneklemesi gerçek sinyaldir.

- [ ] Karar: ______

---

## Karar verilene kadar

Yukarıdakilerden **D1 ve D2** Faz 1'i bloke eder. Diğerleri Faz 9'a kadar
bekleyebilir ama beklediklerini bilerek beklemelisin — unutulmuş karar,
verilmiş karardan daha pahalıdır.

---

# Kapsam genişlemesiyle gelen yeni kararlar (2026-09-10)

Aşağıdakiler, otonomi + çok-runtime kapsamına geçişle açılan kararlardır.

## D9 — Varsayılan otonomi seviyesi

`docs/03 §5`'te üç seviye var: `supervised`, `guarded`, `full`.

**Öneri: `guarded`.** Gerekçe: `supervised` ilk deneyimde ürünü yavaş ve
sıradan gösterir; `full` ise kullanıcı henüz sisteme güvenmeden onu riske atar.
`guarded`, vaadi (iki onay) tutarken `high` risk korumasını da açık bırakır.

İlk kez çalıştıranlar için tek seferlik bir `supervised` önerisi gösterilebilir.

- [ ] Karar: ______

---

## D10 — v1'de kaç runtime uygulanacak

Arayüz dört `Connection` türünü tanımlıyor; uygulama ayrı bir maliyet.

| Seçenek | Sonuç |
|---|---|
| Yalnızca `claude_code` + `gemini_cli` | En hızlı Faz 7; model-bağımsızlık **kanıtlanmamış iddia** kalır |
| + `ApiRuntime` (Faz 9) | İddia kanıtlanır; ~2 gün |
| + `OllamaRuntime` (Faz 9) | Yerel/gizli senaryo açılır; ~1 gün |

**Öneri:** v1 çekirdeğinde ilk ikisi; Faz 9'da `ApiRuntime` + `OllamaRuntime`
birlikte. Gerekçe: bir soyutlamanın doğruluğu, ancak **üçüncü** uygulama
eklendiğinde kanıtlanır. İki uygulama her zaman uyar.

- [ ] Karar: ______

---

## D11 — `automation_policy` varsayılanı ne kadar katı olmalı

`docs/04 §3`, varsayılanı `unknown` yapıp ilk kullanımda uyarı gösteriyor.

Alternatif: `unknown` bağlantıları **hiç kullanmamak** (kullanıcı açıkça
`allowed` işaretlemeden). Daha güvenli ama ilk çalıştırmada sürtünme yaratır.

**Öneri:** `unknown` + tek seferlik onay. Gerekçe: sistem kullanıcı adına
hukuki karar veremez; ama onu kararı vermeye zorlamak, sessizce varsaymaktan
iyidir. Uyarının metni sağlayıcı adı içermemeli — kullanıcı kendi
sözleşmesini kontrol etmeli.

- [ ] Karar: ______

---

## D12 — Risk sınıflandırmasını kim tanımlar

`docs/03 §5.1` riski "task'ın neye dokunduğundan" türetiyor. Bu kuralın
kendisi nerede yaşayacak?

| Seçenek | Artı | Eksi |
|---|---|---|
| Kod içinde sabit | Basit, kaçırılamaz | Yığına göre değişemez |
| `risk-rules.yaml` (veri) | Blueprint başına ayarlanabilir, gözden geçirilebilir | Yanlış yapılandırma korumayı kapatabilir |
| Mimar agent takdir eder | Esnek | **Reddedilmeli** — modelin özgüveni riski ölçmez |

**Öneri:** veri olarak `risk-rules.yaml`, ama **taban kural kodda sabit**:
auth, ödeme, sır, yıkıcı migration ve dağıtım her zaman `high` — yapılandırma
bunu düşüremez, yalnızca genişletebilir.

- [ ] Karar: ______

---

---

# Tasarım sistemiyle gelen kararlar (2026-09-10)

`docs/12-design-system.md` üç yeni karar açtı. Üçü de Faz 7'den önce
gerekmiyor; detay ve öneriler `docs/12 §5`'te.

## D13 — Task graph görselleştirme kütüphanesi

React Flow (hazır etkileşim, ~50kb, kendi stili) vs elle SVG + dagre (tam token
kontrolü, pan/zoom elle). **Öneri:** dagre + elle SVG — graph'ın okunabilirliği
ürünün değeri, hazır kütüphanenin varsayılan görünümü `docs/12 §1.1`'deki bakış
açısını taşımaz.

- [ ] Karar: ______

## D14 — Panel yazabilir mi

`ADR-003` UI'ın orkestrasyon durumuna yazmasını yasaklıyor; onay ve steer
eylemleri bunu ihlal etmez ama dolaylılığın biçimi kararlaşmadı.
**Öneri:** panel yerel CLI'a komut kuyruğu üzerinden yazar; orchestrator
kuyruğu okur, eylemi yapar, olayı kendisi yazar. Tek yazar kuralı korunur.

- [ ] Karar: ______

## D15 — Blueprint tokenlarını kullanıcı nasıl değiştirir

Üretilen ürün kullanıcının markasını taşır; özelleştirme biçimi (prompt'ta
marka bilgisi / üretim sonrası düzenleme / `Blueprint` parametresi) açık.

- [ ] Karar: ______

---

## Öncelik

**Faz 1'i bloke edenler:** D1 (dil) · D2 backend tarafı (frontend kapandı)
**Faz 2'yi bloke edenler:** D9 (otonomi varsayılanı), D12 (risk kuralları)
**Faz 5'e kadar bekleyebilir:** D11
**Faz 7'ye kadar bekleyebilir:** D15, D2 backend
**Faz 9'a kadar bekleyebilir:** D3-D8, D10
**Faz 10'a kadar bekleyebilir:** D13, D14
