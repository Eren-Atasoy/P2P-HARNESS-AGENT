# ADR-007 — Mimari değişiklik talebi (ACR) mekanizması

**Durum:** Kabul edildi · 2026-09-10

## Bağlam
Uygulayıcı agent, mimarinin eksik veya yanlış olduğu bir durumla karşılaşır.
İki kötü seçenek: (a) sessizce kendi çözümünü uydurur, (b) takılıp kalır.

## Karar
Uygulayıcı, mimariyi değiştiremez ama **itiraz edebilir**. `.p2p/acr/` altına
yapılandırılmış bir talep yazar, `outcome=blocked` döner; task `BLOCKED` olur
ve mimar agent talebi karara bağlar (`docs/03 §4`).

## Alternatifler
- **Uygulayıcı serbest:** Mimari birkaç task içinde sessizce erozyona uğrar;
  ölçekte en yaygın başarısızlık biçimi budur.
- **Katı yasak, itiraz yok:** Yanlış mimari fark edilmeden uygulanır; agent
  kabul kriterlerini karşılayamayıp döngüye girer.

## Sonuçlar
- (+) Mimari bütünlük ölçekte korunur
- (+) Mimarinin yanlış olduğu durumlar **görünür** hâle gelir ve kayda geçer
- (+) İki agent arasındaki tek meşru "itiraz" kanalı; başka kanal yok
- (−) Ek gecikme → `DEFERRED` kararı geçici çözümle devam etmeyi sağlar
