# ADR-010 — Otonomi seviyeleri ve risk tabanlı kapılar

**Durum:** Kabul edildi · 2026-09-10 · **Revize eder:** architecture-review C2

## Bağlam

C2 kararında "kapılar kalsın, vaat düzelsin" denmişti: dört sabit insan kapısı,
ikisi kapatılamaz. Bu, ürünün otonomi hedefi netleştiğinde fazla katı kaldı.

Aynı anda iki şey doğru:

1. Bir lint düzeltmesi için insan onayı beklemek ürünü değersizleştirir.
2. Bir ödeme entegrasyonunu denetimsiz bırakmak kabul edilemez.

Sabit kapı listesi bu ikisini ayırt edemez, çünkü kapıyı **projeye** koyar,
**riske** değil.

## Karar

İki eksen tanımlanır.

**Task risk seviyesi** — task'ın neye dokunduğundan türetilir, planlayıcının
takdiri değildir: `low` / `medium` / `high`. Risk yükseltilebilir,
düşürülemez.

**Otonomi seviyesi** — kullanıcının koşu başına seçimi:

| Seviye | Proje kapıları | Task kapıları |
|---|---|---|
| `supervised` | G1 G2 G3 G4 | `medium` + `high` |
| `guarded` (varsayılan) | G2 G4 | `high` |
| `full` | — | `high` |

**Hiçbir seviyede kapatılamayan tek şey: `high` risk task'ları.**
Gerekçe: geri alınamayan veya para/veri kaybettiren eylemler; ve bir modelin
özgüveni riskin gerçek büyüklüğüyle ilişkili değildir.

`full` seviyesinde otomatik geçilen her proje kapısı `Decision` kaydına
`decided_by=default` yazılır ve raporda ayrıca listelenir. **Otonomi,
şeffaflığı azaltmaz; sadece bekleme süresini azaltır.**

## Alternatifler

- **C2'nin sabit kapıları (mevcut durum).** Öngörülebilir ama otonomi vaadini
  taşıyamıyor; "tek promptla ürün" ile "her koşuda iki kez dur" bir arada
  savunulamaz.
- **Tam otonomi, kapı yok.** Vaade en uygun; ama yanlış bir mimari varsayım
  veya bir ödeme hatası fark edilmeden ilerler. Otonom sistemlerde en pahalı
  başarısızlık, hızlı yanlış ilerlemedir.
- **Kapıları yalnızca kullanıcı tanımlasın.** Esnek; ama güvenli varsayılan
  yok ve `docs/06`'nın güvenli-varsayılan ilkesiyle çelişir.

## Sonuçlar

- (+) Ürün gerçekten otonom çalışabilir; `docs/00 §1` vaadi tutarlı hâle gelir
- (+) Risk sınıflandırması aynı zamanda routing girdisi olur (`docs/04 §5`)
- (+) Kullanıcı otonomiyi kademeli olarak artırabilir; güven kazanma yolu var
- (−) Risk sınıflandırması yanlışsa koruma da yanlış yerde olur → risk kuralları
  veri olarak tanımlanır ve gözden geçirilebilir olmalı
- (−) Üç seviye, test matrisini büyütür (Faz 2 çıkış kriterine eklendi)
