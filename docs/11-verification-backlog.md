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

## V3 — Antigravity'nin programatik SDK'sı · **DOĞRULANDI** (2026-09-11)

**Bulgular & Kanıtlar:**
1. **Paket Adı & PyPI:** PyPI'da resmi paket mevcuttur: **`google-antigravity`** (sürüm 0.1.16). Bağımlılıkları arasında `google-genai>=1.0`, `mcp>=1.0`, `httpx2`, `uvicorn`, `sse-starlette` bulunur.
2. **Kullanım Sözleşmesi:** Antigravity Guide referans dokümantasyonuna (`references/sdk.md`) göre:
   ```python
   from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
   async with Agent(config) as agent:
       response = await agent.chat("...")
       async for token in response: ...
       async for thought in response.thoughts: ...
       async for call in response.tool_calls: ...
   ```
3. **P2P Uyumu:** P2P'nin Python 3.12+ mimarisi, Antigravity Python SDK ile tam uyumludur. Faz 5'te `GeminiCliRuntime`'ın yanına birinci sınıf `AntigravitySdkRuntime` adapter'ı doğrudan eklenebilir.

---

## V4 — Claude aboneliğiyle programatik kullanım · **DOĞRULANDI** (2026-09-11)

**Bulgular & Kanıtlar:**
1. **CLI Headless Yürütme:** `claude -p "..." --output-format json` çağrısı canlı ortamda başarıyla test edildi ve doğrulandı.
2. **Yapılandırılmış JSON Yanıtı:** CLI doğrudan zengin bir JSON nesnesi döner:
   ```json
   {
     "subtype": "success",
     "result": "P2P_CLAUDE_HEADLESS_OK",
     "duration_ms": 4633,
     "total_cost_usd": 0.538899,
     "usage": { "input_tokens": 2, "output_tokens": 22 }
   }
   ```
3. **Adapter Kuralı (Kritik Bulgular):**
   - Headless çağrılarda stdin askıda kalmaması için `stdin=subprocess.DEVNULL` (veya `< /dev/null`) yönlendirilmelidir.
   - Dönen `result`, `total_cost_usd` ve `duration_ms`, P2P'nin `AgentResult.usage` modeline birebir beslenir.
   - Claude abonelik oturumu üzerinden programatik review ve task üretimi fiziksel olarak doğrulanmıştır.

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
