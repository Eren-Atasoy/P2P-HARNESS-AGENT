# ADR-001 — Modüler monolit + olay günlüğü

**Durum:** Kabul edildi · 2026-09-10

## Bağlam
P2P birden çok agent'ı eşzamanlı yönetir. Dağıtık bir agent platformu (mesaj
kuyruğu, olay veriyolu, ayrı worker'lar) cazip görünüyor.

## Karar
v1 **tek process modüler monolit** olacak. Agent'lar alt process; modüller
arası iletişim doğrudan fonksiyon çağrısı; kalıcılık append-only olay günlüğü.

## Alternatifler
- **Düz script + dosya:** Kurtarılabilirlik ve paralellik yok.
- **Olay güdümlü platform (kuyruk + worker):** Gerçek ölçek sağlar ama v1'in
  problemi ölçek değil. Hata ayıklama maliyeti ve katkı eşiği kabul edilemez.

## Sonuçlar
- (+) Tek yerden hata ayıklama, tek process'te breakpoint
- (+) Katkıcı bir öğleden sonrada sistemi anlayabilir
- (−) Tek makine sınırı — v1 için kabul
- Buluta geçiş için modül sınırları korunur (`docs/01 §9`)
