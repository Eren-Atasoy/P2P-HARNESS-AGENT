# 11 — Doğrulama Borcu (Verification Backlog)

Bu belge, mimarinin **dayandığı ama henüz kanıtlanmamış** varsayımları tutar.
Amacı tek: bir varsayımın "biliyoruz" ile "duyduk" arasındaki farkını görünür
kılmak. Bir madde kanıtlanana kadar hiçbir faz onun üstüne kurulmaz.

Her madde şu üç durumdan birindedir:
`DOĞRULANDI` · `DOĞRULANMADI` · `YANLIŞ ÇIKTI`

---

## V1 — `gemini` CLI headless çalışıyor · **KISMEN** (2026-09-10)

> **Faz 0 Test 3 bulgusu:** İkili ve bayraklar doğru, ama **kimlik doğrulaması
> yok**. Headless çağrı şu hatayla düşüyor:
> *"Please set an Auth method in your `.gemini/settings.json` or specify one of:
> GEMINI_API_KEY, GOOGLE_GENAI_USE_VERTEXAI, GOOGLE_GENAI_USE_GCA"*
>
> `.gemini/settings.json` yok, OAuth kaydı yok. Antigravity kendi kimliğini
> `.gemini/antigravity/` altında tutuyor ve **CLI onu kullanmıyor** — ayrı
> oturum gerekiyor.
>
> **Çözüm:** bir kez interaktif `gemini` çalıştırıp *Login with Google* seçmek.
> Sonrasında headless çağrılar aynı oturumu kullanır.
>
> Bu, `Connection.health = unauthenticated` durumunun (`docs/04 §2`) gerçek
> hayattaki ilk örneği; `p2p doctor`'ın yakalaması gereken şey tam olarak budur.

### Bayraklar (doğrulandı)

`@google/gemini-cli` 0.58.0 kurulu. `--help` çıktısı şunları doğruluyor:
`-p/--prompt` (headless), `--output-format json|stream-json`,
`--approval-mode default|auto_edit|yolo|plan`, `--policy`, `--include-directories`,
`-w/--worktree`, `-s/--sandbox`, `--acp`, ayrıca `mcp` / `skills` / `hooks`
alt komutları.

**Sonuç:** Google tarafındaki programatik yüzey budur. Mimarinin
`AntigravityRuntime` yerine **`GeminiCliRuntime`** üzerine kurulması gerekir.

---

## V2 — `claude` CLI headless çalışıyor · **DOĞRULANDI** (2026-09-09)

Claude Code 2.1.266 kurulu; `-p/--print`, `--output-format`, `--allowedTools`,
`--append-system-prompt`, `--add-dir`, `--agents`, `--bg` mevcut.

---

## V3 — Antigravity'nin programatik SDK'sı · **DOĞRULANMADI**

**İddia:** Antigravity, Python'dan agent çalıştırmayı sağlayan bir SDK sunuyor
(tool execution, subagent delegation, MCP, safety policies, lifecycle hooks).

**Bilinen durum:** Makinede Antigravity IDE kurulu ama `bin/` dizini **yok**;
çalıştırılabilir tek dosya `Antigravity.exe` (GUI). Komut satırı girişi
bulunamadı.

> ⚠️ **TUZAK:** PyPI'daki `antigravity` paketi **Google'ın SDK'sı değildir.**
> Python'un standart kütüphanesindeki xkcd şakasının paket karşılığıdır
> (sürüm 0.1). `pip install antigravity` yanlış şeyi kurar ve hiçbir hata
> vermez. Uygulayıcı agent'a bu paket adı asla verilmemeli.

**Nasıl doğrulanır (Faz 0):** Resmî dokümantasyondan doğru paket adı ve
kurulum yolu teyit edilir; boş bir dizinde bir agent çalıştırılıp dosya
yazdırılır. Doğrulanana kadar Google tarafı **yalnızca `gemini` CLI**
üzerinden kullanılır.

**Mimariye etkisi:** Yok. `RuntimeAdapter` sınırı, "CLI mi SDK mı" sorusunu
bir uygulama detayı hâline getirir (ADR-009). SDK doğrulanırsa
`GeminiCliRuntime`'ın yanına ikinci bir adapter eklenir; hiçbir çekirdek
modül değişmez.

---

## V4 — Claude aboneliğiyle programatik kullanım · **KISMEN DOĞRULANDI**

| Alt iddia | Durum |
|---|---|
| `claude -p` abonelik oturumuyla çalışır | **Doğrulandı** — CLI kurulu ve oturum açık |
| Claude **Agent SDK** (kütüphane olarak) abonelik altında çalışır | **Doğrulanmadı** — paket kurulu değil, limit/faturalama davranışı teyit edilmedi |

**Nasıl doğrulanır (Faz 0):** Kendi hesabında tek bir çağrı ile test edilir ve
kullanım/limit davranışı gözlenir. Doğrulanana kadar Claude tarafı **yalnızca
`claude -p`** üzerinden kullanılır.

---

## V5 — Model adları · **DOĞRULANMADI, KULLANILMIYOR**

"Gemini 3.8 Flash" gibi belirli model adları hiçbir belgede ve hiçbir kodda
geçmez. Model seçimi `routing.yaml`'dan gelen bir parametredir (ADR-009).

**Bu bir eksiklik değil, bir tasarım kararıdır.** Model adları hızla değişir;
mimarinin doğruluğu hiçbir zaman bir model adının güncel olmasına bağlı
olmamalıdır. Kullanıcı `gemini` interaktif oturumunda `/model` ile kendi
erişebildiği modelleri görür.

---

## V6 — Abonelik otomasyonunun **lisans** durumu · **DOĞRULANMADI**

**Bu, teknik değil hukuki bir sorudur ve teknik doğrulama onu cevaplamaz.**

Bir tüketici AI aboneliğinin, üçüncü taraf bir yazılım tarafından otomatik
olarak kullandırılmasının izinli olup olmadığı sağlayıcıya ve plana göre
değişir. "Teknik olarak çalışıyor" ile "izinli" aynı şey değildir.

**P2P'nin tavrı (ADR-010):** Sistem bu soruya **karar vermez**. Her
`Connection` üzerinde bir `automation_policy` alanı tutar
(`allowed | prohibited | unknown`), kaynağını kaydeder ve `unknown` olan bir
bağlantıyı ilk kullanımda kullanıcıya bildirir. Sorumluluk kullanıcıdadır;
sistemin sorumluluğu **sessiz kalmamaktır**.

---

## V7 — `gemini --sandbox` Windows'ta çalışıyor mu · **DOĞRULANMADI**

ADR-008'in yükseltme yolu buna bağlı. Sandbox genellikle Docker/Podman
gerektirir; worktree erişimiyle sandbox sınırının nasıl kesiştiği de
bilinmiyor. Faz 0'da denenir; çalışmazsa ADR-008'in dar politika yaklaşımı
kalıcı çözüm olur.

---

## V8 — Paralel headless oturum sınırı · **DOĞRULANMADI**

`docs/03 §2.6` en fazla 4 paralel worker öngörüyor. Aynı abonelikle 4 eşzamanlı
headless oturumun kabul edilip edilmediği (hız sınırı, eşzamanlılık kotası)
bilinmiyor.

**Nasıl doğrulanır (Faz 0):** 2, sonra 4 eşzamanlı `gemini -p` çağrısı;
hata veya kuyruklanma gözlenir. Sonuç `Connection.limits.concurrency`
varsayılanını belirler.

---

## Kural

> Bu listedeki bir maddeye dayanan hiçbir faz, madde `DOĞRULANDI` olmadan
> başlamaz. Bir madde `YANLIŞ ÇIKTI` olursa, ona dayanan kararlar yeniden
> açılır ve ilgili ADR güncellenir — sessizce etrafından dolanılmaz.
