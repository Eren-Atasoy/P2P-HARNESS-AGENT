# ADR-004 — Kalite kararı deterministiktir

**Durum:** Kabul edildi · 2026-09-10

## Bağlam
"Kod doğru mu" sorusunu bir LLM'e sormak kolay ve esnektir.

## Karar
Geçme/kalma kararı **yalnızca** process çıkış kodundan gelir. LLM incelemesi
bulgu üretir; kararı orchestrator'ın sabit kuralı verir (`docs/02 §5`).

## Alternatifler
- **LLM hakem:** Non-deterministik, kandırılabilir, ürünün tek gerçek
  farklılaşmasını (doğrulanmışlık) yok eder.

## Sonuçlar
- (+) Tekrarlanabilir, denetlenebilir, savunulabilir
- (+) "Verified Product" iddiası anlamlı hâle gelir
- (−) Kapı altyapısına yatırım gerekir (Faz 4)
- (−) Kapının kapsamadığı kalite boyutları (okunabilirlik, mimari uyum)
  incelemeye kalır — bunlar CRITICAL/HIGH kuralıyla yönetilir
