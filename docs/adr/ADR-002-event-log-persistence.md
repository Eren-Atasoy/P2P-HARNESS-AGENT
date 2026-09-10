# ADR-002 — Kalıcılık: append-only JSONL, SQLite değil

**Durum:** Kabul edildi · 2026-09-10

## Bağlam
Orkestrasyon durumu kalıcı olmalı ve paralel task'lar sırasında tutarlı kalmalı.

## Karar
`.p2p/events.jsonl` append-only olay günlüğü doğruluk kaynağıdır.
`state.json` bundan türetilen, atılabilir bir görünümdür.

## Alternatifler
- **SQLite:** Sorgu gücü iyi; ancak paralel yazarlarda kilit çekişmesi,
  Windows'ta özellikle sorunlu. Ayrıca ikili format, git diff'te okunamaz.
- **Salt `state.json` (üzerine yazma):** Yarım yazımda bozulur, geçmiş yok.

## Sonuçlar
- (+) Kilitsiz (tek yazar), çökmede tutarlı, `tail -f` ile izlenebilir
- (+) "Sistem o an ne biliyordu" sorusu kesin cevaplanır
- (−) Karmaşık sorgu zor → gerekirse JSONL'den SQLite projeksiyonu (uyumlu ekleme)
- (−) Günlük büyür → proje bitince sıkıştırılır
