# ADR-009 — Capability tabanlı yönlendirme ve Connection soyutlaması

**Durum:** Kabul edildi · 2026-09-10 · **Üstünü çizer:** ADR-005'i genişletir

## Bağlam

İlk tasarım iki sabit runtime varsayıyordu: Claude (mimar) ve Gemini
(uygulayıcı). Bu, geliştirme ortamımızı tarif ediyordu — ürünü değil.

Ürünün gerçek hedefi: kullanıcı hangi AI'a erişiyorsa onu kullanmak. Erişim
biçimleri birbirine hiç benzemiyor: abonelik oturumlu CLI, API anahtarı,
yerel süreç, gateway. Bunları tek bir "provider" kavramına sıkıştırmak,
yalnızca ilk erişim biçimine uyan bir soyutlama üretirdi.

Ayrıca model adları haftalar içinde eskiyor. Bir mimarinin doğruluğu asla
bir model adının güncelliğine bağlanamaz.

## Karar

Yedi kavram kesin olarak ayrılır (`docs/04 §1`):

```
Capability · Agent · Runtime · Connection · Provider · Model · Gateway
```

- **Yönlendirme capability tabanlıdır.** Task yeteneğini ve riskini bildirir;
  router hangi `Connection`'ın onu sağladığına bakar.
- **`Connection`, erişimin tek soyutlamasıdır.** `kind` alanı
  (`subscription | api | local | gateway`) farklılığı taşır; orchestrator
  bu alanı hiç okumaz.
- **Çekirdek kodda hiçbir sağlayıcı veya model adı geçmez.** Doğrulaması
  mekanik: Faz 9 çıkış kriterinde `grep`.
- Seçim iki aşamalıdır: ikili uygunluk süzgeci, sonra puanlama. Uygun aday
  yoksa `UNROUTABLE` (sessiz durma değil, somut hata).

## Alternatifler

- **Sabit iki runtime.** Basit; ama ürünün model-bağımsızlık iddiasını
  imkânsız kılar ve üçüncü bir runtime çekirdeği yeniden yazmayı gerektirir.
- **Provider = Connection (tek kavram).** Abonelik ile API'nin kimlik, kota ve
  lisans davranışı temelden farklı; birleştirmek her ikisine de kötü uyan bir
  soyutlama üretir.
- **Gateway'i merkeze koymak (OmniRoute orchestrator olarak).** Gateway
  *"sağlayıcıya nasıl ulaşırım"* problemini çözer; P2P *"bu işi kim yapmalı"*
  problemini. Farklı problemler; birleştirmek ikisini de bulanıklaştırır.
  ADR-005 geçerliliğini korur: gateway `Connection`'ın **altında** durur.

## Sonuçlar

- (+) Yeni runtime eklemek = yeni adapter + `routing.yaml` satırı; çekirdek sabit
- (+) Model adı değişimleri hiçbir belgeyi veya kodu geçersiz kılmaz
- (+) "CLI mi SDK mı" sorusu adapter'ın içinde kalır → `docs/11`'deki
  doğrulanmamış SDK iddiaları mimariyi etkilemez
- (−) Router, sabit eşlemeye göre daha karmaşık (uygunluk + puanlama)
- (−) `quality` puanları v1'de elle tanımlı ve öznel; telemetriyle
  iyileştirilene kadar kaba bir sıralama aracıdır
- (−) `UNROUTABLE` yeni bir başarısızlık modu; mesaj kalitesi kritik
