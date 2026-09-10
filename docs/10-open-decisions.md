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

- [ ] Karar: ______  Gerekçe: ______

---

## D2 — İlk hedef teknoloji yığını (referans ürün için)

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
