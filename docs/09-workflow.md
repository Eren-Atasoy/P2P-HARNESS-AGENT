# 09 — Günlük Çalışma Akışı (p2p-dev)

Bu belge, **P2P'yi geliştirirken** senin ve iki agent'ın nasıl çalışacağını
anlatır. Ürünün kendi çalışma akışı değil; onun için `docs/03`.

## 1. Rol dağılımı

| Rol | Kim | Yetki |
|---|---|---|
| **Ürün sahibi / karar verici** | Sen | Tüm G kapıları, ADR onayı, kapsam |
| **Mimar / gözden geçiren** | Claude Code | `docs/**` ve `.p2p/**` yazar; **uygulama kodu yazmaz** |
| **Uygulayıcı** | Gemini CLI | `src/**`, `tests/**` yazar; **mimari değiştirmez** |


Bu ayrımın tek amacı var: **tek bir modelin hem kararı hem uygulamayı hem
denetimi yapmasını engellemek.** Aynı model her üçünü yaparsa kendi hatasını
göremez; sistemin tüm kalite iddiası buraya dayanır.

## 2. Faz 0-5 döngüsü (P2P henüz yok, elle sürülür)

```
1. SEN          Bir sonraki task'ı seç (docs/08 roadmap)
2. CLAUDE       Task sözleşmesini yaz  → .p2p/tasks/<id>.json
                (prompts/02-task-planning.md)
3. SEN          Sözleşmeyi oku, onayla veya düzelt        ← 2 dakika, atlanmaz
4. GEMINI       Uygula (worktree içinde)
                (prompts/03-implement.md)
5. SEN/SCRIPT   Kapıları çalıştır (pytest, ruff, mypy)
6. CLAUDE       İncele → .p2p/reviews/<id>-1.json
                (prompts/04-review.md)
7.              APPROVED  → birleştir, commit
                CHANGES   → GEMINI fix (prompts/05-fix.md), 4'e dön
                BLOCKED   → CLAUDE ACR değerlendirir
```

**3. adım pazarlık konusu değildir.** Sözleşmeyi okumadan Gemini'ye vermek,
yanlış işi hızlıca yapmak demektir. Sözleşmeyi okumak 2 dakika, yanlış
uygulamayı geri almak 2 saattir.

## 3. Somut komut şablonları

Mimarlık / planlama (repo kökünde):

```
claude -p "$(cat prompts/02-task-planning.md)  Task: <hedef>"
```

Uygulama (worktree içinde):

```
git worktree add .p2p/wt/API-001 -b p2p/task/API-001
cd .p2p/wt/API-001
gemini -p "$(cat ../../../prompts/03-implement.md)" --approval-mode auto_edit
```

İnceleme:

```
claude -p "$(cat prompts/04-review.md)  Task: API-001  Diff: $(git diff p2p/integration...HEAD --stat)"
```

Bu komutlar Faz 5'te `p2p implement API-001` haline gelir. Şimdilik elle
çalıştırılması **iyidir** — otomatikleştirmeden önce akışın nerede
takıldığını görmen gerekiyor.

## 4. Neyi ne zaman otomatikleştirmeli

| Sinyal | Aksiyon |
|---|---|
| Aynı komutu 3. kez elle yazdın | Script'e al |
| Aynı düzeltmeyi 2 farklı task'ta yaptın | `GEMINI.md`'ye kural olarak ekle |
| Claude aynı mimari sorusunu 2 kez sordu | `docs/`'a ekle, ADR yaz |
| Bir kapı 2 kez elle kontrol edildi | Kapı tanımına ekle |

**Kural yazmayı promptu uzatmaya tercih et.** `GEMINI.md`'ye eklenen bir kural
kalıcıdır ve her çalıştırmada bedavaya gelir; prompta eklenen bir cümle
bir sonraki sefer unutulur.

## 5. Kota yönetimi

| Runtime | Nerede kullan | Nerede kullanma |
|---|---|---|
| **Claude** | Mimari, task sözleşmesi, inceleme, ACR, güvenlik analizi, kök neden | Toplu kod yazımı, biçimlendirme, tekrarlayan refactor |
| **Gemini** | Uygulama, test yazımı, refactor, migration, tarayıcı işleri | Geri dönüşü pahalı mimari kararlar |


Pratik kural: **Claude'a token değil, karar harcat.** Claude'un çıktısı
bir dosya değil, bir sözleşme olmalı. Bir gününde 40 Claude çağrısı yapıyorsan
muhtemelen ona Gemini'nin işini yaptırıyorsun.

## 6. Oturum hijyeni

- Claude oturumunu mimari fazlarında **uzun** tut (bağlam birikmeli)
- Gemini oturumunu task başına **sıfırla** (bağlam sızıntısı = kapsam kayması)
- Her fazın sonunda `docs/` güncelle — mimari belgeler bayatlarsa iki agent
  farklı gerçekliklerde çalışmaya başlar ve bu sessizce olur

## 7. Haftalık ritim (öneri)

| Gün | Odak |
|---|---|
| Pazartesi | Faz hedefini netleştir, task sözleşmelerini Claude ile yaz |
| Salı-Perşembe | Gemini ile uygulama + inceleme döngüsü |
| Cuma | Regresyon, `docs/` güncelleme, ADR yazımı, faz çıkış kriteri kontrolü |

Cuma'yı atlama. Belge borcu, kod borcundan daha hızlı birikir ve bu projede
belgeler **çalışma girdisidir**, dokümantasyon değil.
