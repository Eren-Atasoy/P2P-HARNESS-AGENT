# 09 — Geliştirme Çalışma Akışı

Bu belge **P2P'yi geliştirirken** senin ve agent'ların nasıl çalıştığını
anlatır. Ürünün kendi otonom akışı için `docs/03 §7`.

Kritik nokta: bu akış **geçicidir**. Faz 5 bittiğinde P2P kendi döngüsünü
çalıştırır ve buradaki elle adımların çoğu ortadan kalkar. Faz 10'da bu belge
tamamen `docs/03`'e devredilir.

## 1. Rol dağılımı

| Rol | Kim | Yetki |
|---|---|---|
| **Ürün sahibi** | Sen | Otonomi seviyesi, G kapıları, ADR onayı, kapsam |
| **Mimar / gözden geçiren** | `claude -p` | `docs/**`, `.p2p/docs/**`, `.p2p/reviews/**`, `.p2p/acr/**`; **uygulama kodu yazmaz** |
| **Uygulayıcı** | `gemini -p` | `src/**`, kendi `allowed_paths`'i; **mimari değiştirmez** |

Bu ayrımın tek amacı: **tek bir modelin hem kararı, hem uygulamayı, hem
denetimi yapmasını engellemek.** Aynı model üçünü de yaparsa kendi hatasını
göremez; sistemin tüm kalite iddiası buraya dayanır.

> Roller **runtime'a değil, yeteneğe** bağlıdır. Bugün mimar Claude, uygulayıcı
> Gemini; yarın `routing.yaml`'da bu değişebilir ve hiçbir belge veya kod
> değişmez (`docs/04 §1`).

## 2. Faz 0-4 döngüsü — elle sürülür

P2P henüz yok; döngüyü sen çeviriyorsun.

```
1. SEN      Sıradaki task'ı seç (docs/08)
2. CLAUDE   Task sözleşmesini taslakla → .p2p/docs/task-graph/<id>.json
            (prompts/03-task-planning.md)
3. SEN      Sözleşmeyi oku, onayla       ← 2 dakika, atlanmaz
4. GEMINI   Uygula (worktree içinde)     (prompts/04-implement.md)
5. SCRIPT   Kapıları çalıştır
6. CLAUDE   İncele → .p2p/reviews/<id>-1.json  (prompts/05-review.md)
7.          APPROVED → birleştir, commit
            CHANGES  → GEMINI fix (prompts/06-fix.md), 4'e dön
            BLOCKED  → CLAUDE ACR değerlendirir (prompts/07-acr-review.md)
```

**3. adım pazarlık konusu değildir.** Sözleşmeyi okumadan uygulamaya geçmek,
yanlış işi hızlıca yapmaktır. Sözleşmeyi okumak 2 dakika; yanlış uygulamayı
geri almak 2 saat.

## 3. Faz 5'ten sonra — döngü kendini çevirir

```
p2p run --autonomy guarded
```

Adım 1, 4, 5, 6, 7 orchestrator'a geçer. Sende kalan: otonomi seviyesini
seçmek, G kapılarını cevaplamak, `ESCALATED` task'ları çözmek.

Bu geçiş bir "iyileştirme" değil, **ürünün kendisinin doğrulanması**dır.
Elle çevirdiğin döngü ile P2P'nin çevirdiği döngü aynı şekle sahip olmalı;
değilse ya belge ya uygulama yanlıştır.

## 4. Somut komut şablonları

Planlama (repo kökünde):
```
claude -p "$(cat prompts/03-task-planning.md)  Task: <hedef>"
```

Uygulama (worktree içinde):
```
git worktree add .p2p/wt/API-001 -b p2p/task/API-001
cd .p2p/wt/API-001
gemini -p "$(cat ../../../prompts/04-implement.md)" \
  --approval-mode auto_edit --policy ../../../.p2p/policy/implementer.yaml
```

İnceleme:
```
claude -p "$(cat prompts/05-review.md)  Task: API-001"
```

Bunlar Faz 5'te `p2p run` içine gömülür. Şimdilik elle çalıştırılması
**iyidir** — otomatikleştirmeden önce akışın nerede takıldığını görmen gerekir.

## 5. Neyi ne zaman otomatikleştirmeli

| Sinyal | Aksiyon |
|---|---|
| Aynı komutu 3. kez elle yazdın | Script'e al |
| Aynı düzeltmeyi 2 farklı task'ta yaptın | `GEMINI.md`'ye kural olarak ekle |
| Mimar aynı soruyu 2 kez sordu | `docs/`'a ekle, gerekirse ADR |
| Bir kapı 2 kez elle kontrol edildi | Kapı tanımına ekle |
| Bir varsayıma 2 kez güvendin | `docs/11`'e doğrulama maddesi olarak ekle |

**Kural yazmayı promptu uzatmaya tercih et.** `GEMINI.md`'ye eklenen kural
kalıcıdır ve her çalıştırmada bedavaya gelir; prompta eklenen cümle bir
sonraki sefer unutulur.

## 6. Bağlantı ve kota yönetimi

| Bağlantı | Nerede kullan | Nerede kullanma |
|---|---|---|
| `claude-pro` | Mimari, task sözleşmesi, inceleme, ACR, güvenlik analizi, kök neden | Toplu kod yazımı, biçimlendirme, tekrarlayan refactor |
| `gemini-ultra` | Uygulama, test yazımı, refactor, migration, tarayıcı işleri | Geri dönüşü pahalı mimari kararlar |

Pratik kural: **Claude'a token değil, karar harcat.** Çıktısı bir dosya değil,
bir sözleşme olmalı. Günde 40 Claude çağrısı yapıyorsan muhtemelen ona
uygulayıcının işini yaptırıyorsun.

Kota bittiğinde sistem durmaz: `QUOTA` → `PAUSED` → alternatif bağlantı →
yoksa `SUSPENDED` + `p2p resume` (`docs/03 §3.4`).

## 7. Oturum hijyeni

- Mimar oturumunu mimari fazlarında **uzun** tut (bağlam birikmeli)
- Uygulayıcı oturumunu task başına **sıfırla** (bağlam sızıntısı = kapsam kayması)
- Her fazın sonunda `docs/` güncelle — mimari belgeler bayatlarsa iki agent
  farklı gerçekliklerde çalışmaya başlar ve bu **sessizce** olur

## 8. Haftalık ritim (öneri)

| Gün | Odak |
|---|---|
| Pazartesi | Faz hedefi, task sözleşmeleri |
| Salı-Perşembe | Uygulama + inceleme döngüsü |
| Cuma | Regresyon, `docs/` güncelleme, ADR yazımı, faz çıkış kriteri kontrolü |

Cuma'yı atlama. Belge borcu kod borcundan hızlı birikir ve bu projede belgeler
**çalışma girdisidir**, dokümantasyon değil.
