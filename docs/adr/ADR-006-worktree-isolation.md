# ADR-006 — Paralel task izolasyonu git worktree ile

**Durum:** Kabul edildi · 2026-09-10

## Bağlam
Paralel agent'lar aynı çalışma ağacına yazarsa birbirlerinin dosyalarını
bozar; ayrıca hangi değişikliğin kime ait olduğu kaybolur.

## Karar
Paralel her task kendi `git worktree`'sinde, kendi dalında çalışır.
Birleştirme deterministik sırayla (task id) yapılır.

## Alternatifler
- **Tam repo kopyası:** Disk ve zaman maliyeti yüksek, git geçmişi kopuk.
- **Dosya kilitleme:** Karmaşık, kilitlenme riski, kısmi yazım sorunu çözülmez.
- **Sadece sıralı çalıştırma:** Basit ama paralellik faydasını tamamen kaybeder.

## Sonuçlar
- (+) Fiziksel izolasyon; yarış imkânsız
- (+) Başarısız task'ın atılması bedelsiz
- (+) Çakışma, git'in çözülmüş problemi hâline gelir
- (−) Disk kullanımı artar → başarılı task sonrası worktree silinir
- (−) Bağımlılık dizinleri (`node_modules`) worktree başına — cache paylaşımı
  gerekebilir (Faz 3'te ele alınacak uygulama detayı)
