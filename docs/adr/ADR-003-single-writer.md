# ADR-003 — Durumu yalnızca orchestrator yazar

**Durum:** Kabul edildi · 2026-09-10

## Bağlam
Agent'ların kendi durumlarını bildirmesi doğal görünüyor; ilk tasarımlarda
agent'ın `state.json`'a yazması öneriliyordu.

## Karar
Agent'lar orkestrasyon durumuna **yazamaz**. Agent'ın tek yapılandırılmış
çıktısı, kendisine verilen `result_path` dosyasıdır. Orchestrator onu okur,
doğrular ve olayı kendisi yazar.

## Alternatifler
- **Agent state'e yazar:** Paralel agent'larda yarış; ayrıca agent kendi
  başarısını ilan edebilir — kalite kapısını anlamsızlaştırır.

## Sonuçlar
- (+) Yarış koşulu yapısal olarak imkânsız
- (+) Agent kendi işini "başarılı" ilan edemez
- (+) Her durum geçişi tek kod yolundan geçer → denetlenebilir
- (−) Adapter'da fazladan bir okuma/ayrıştırma adımı
