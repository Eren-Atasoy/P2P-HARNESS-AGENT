# 04 — Sağlayıcı, Bağlantı ve Runtime Mimarisi

> Bu belge, önceki "runtime adapter sözleşmesi" belgesinin yerini alır
> (2026-09-10, ADR-009). Kapsam genişledi: artık iki sabit runtime değil,
> **kullanıcının erişebildiği herhangi bir AI** hedefleniyor.

## 1. Yedi ayrı kavram

Bunları tek arayüzde toplamak, geri dönüşü olmayan bir hatadır. Her birinin
farklı bir ömrü, sahibi ve değişim hızı var.

| Kavram | Tanım | Örnek | Değişim hızı |
|---|---|---|---|
| **Capability** | Bir işin gerektirdiği yetenek | `architecture`, `browser` | Neredeyse hiç |
| **Agent** | Rol + kalıcı talimat kümesi | "Backend Engineer" | Nadiren |
| **Runtime** | Agent'ı çalıştıran yürütücü | `claude_code`, `gemini_cli`, `api`, `ollama` | Nadiren |
| **Connection** | Kullanıcının bir runtime'a somut erişimi | "Claude Pro oturumum" | Kullanıcı başına |
| **Provider** | Modellerin arkasındaki kuruluş | Anthropic, Google, OpenAI | Nadiren |
| **Model** | Somut ağırlıklar | runtime'ın `-m` parametresi | **Sürekli** |
| **Gateway** | Çok sağlayıcılı taşıma katmanı | OmniRoute vb. | Opsiyonel |

### İlişkiler

```
Task ──requires──> Capability[]
                        ^
                        | provides
Agent ──runs on──> Runtime ──reached through──> Connection
                        |                            |
                        | targets                    | authorizes
                        v                            v
                   Provider ──offers──> Model    Credential
                        ^
                        | (opsiyonel dolaylılık)
                    Gateway
```

### Değişmez kurallar

```
Role     != Model
Agent    != Provider
Runtime  != Model
Gateway  != Orchestrator
```

> **Çekirdek kodda hiçbir sağlayıcı veya model adı geçmez.** Ne
> `if provider == "claude"`, ne bir model adı sabiti. Bunların tek adresi
> `routing.yaml` ve kullanıcının bağlantı kaydıdır. Model adları en hızlı
> bayatlayan bilgidir; mimarinin doğruluğu asla bir model adının güncelliğine
> bağlanamaz.

## 2. Connection — kullanıcının AI erişimi

`Connection`, "bu kullanıcı hangi AI'ı, hangi yolla, hangi izinle
kullanabiliyor" sorusunun tek cevabıdır.

| Alan | Tip | Açıklama |
|---|---|---|
| `id` | string | `claude-pro-local` |
| `kind` | enum | `subscription` / `api` / `local` / `gateway` |
| `runtime` | enum | `claude_code` / `gemini_cli` / `api` / `ollama` / … |
| `credential_ref` | string | **Sırrın kendisi değil**, nereden okunacağı: `session`, `env:OPENAI_API_KEY`, `keychain:…` |
| `capabilities` | Capability[] | Beyan edilen veya yoklanan yetenekler |
| `quality` | map | Capability başına 0-1 kalite puanı (bkz. §5) |
| `limits` | object | `concurrency`, `daily_runs`, `rpm` |
| `cost_tier` | enum | `free` / `subscription` / `metered` |
| `automation_policy` | object | bkz. §3 |
| `health` | enum | `ok` / `degraded` / `unauthenticated` / `unavailable` |

**P2P hiçbir sırrı saklamaz.** `credential_ref` bir işaretçidir; gerçek değer
işletim sistemi anahtarlığında, ortam değişkeninde veya alt CLI'ın kendi
oturumunda kalır. Bu, `docs/06 §4`'ün doğrudan sonucudur.

### Aynı soyutlama, dört farklı erişim biçimi

```
Connection(kind=subscription, runtime=claude_code)  -> claude -p, oturum tabanlı
Connection(kind=subscription, runtime=gemini_cli)   -> gemini -p, oturum tabanlı
Connection(kind=api,          runtime=api)          -> HTTP + anahtar
Connection(kind=local,        runtime=ollama)       -> yerel süreç
Connection(kind=gateway,      runtime=api)          -> gateway üzerinden çoklu sağlayıcı
```

Orchestrator hepsini tek bir soruyla değerlendirir:

> *Bu bağlantı bu görevi çalıştırabilir mi?*

"Abonelik mi, API mi" sorusu orchestrator'a hiç ulaşmaz.

## 3. `automation_policy` — teknik olarak mümkün ≠ izinli

Bir tüketici AI aboneliğinin, üçüncü taraf bir yazılım tarafından otomatik
kullandırılmasının izinli olup olmadığı sağlayıcıya ve plana göre değişir.
Bu **hukuki** bir sorudur; teknik doğrulama onu cevaplamaz (`docs/11 V6`).

```yaml
automation_policy:
  third_party_automation: allowed | prohibited | unknown
  source: "sağlayıcı dokümantasyonu 2026-09 | kullanıcı beyanı | varsayılan"
  acknowledged_at: 2026-09-10T12:00:00Z
```

**P2P'nin tavrı: karar vermez, ama sessiz de kalmaz.**

| Değer | Davranış |
|---|---|
| `allowed` | Normal kullanım |
| `unknown` | İlk kullanımda tek seferlik uyarı + onay; kayda geçer |
| `prohibited` | Router bu bağlantıyı uygun bulmaz; kullanıcı zorlayamaz |

Varsayılan `unknown`'dır. Sistemin kullanıcı adına iyimser varsayım yapması,
onu bilmediği bir riske sokmaktır.

## 4. RuntimeAdapter sözleşmesi ve RuntimeFeatures

İki farklı runtime aynı temel fonksiyona sahip olsa bile yetenekleri (stream, cancel, pause, structured output, subagent, mcp) aynı olmayabilir. Bu nedenle runtime'ın teknik yetenekleri `RuntimeFeatures` ile tanımlanır.

### RuntimeFeatures (Özellik Sözleşmesi)

```yaml
RuntimeFeatures:
  can_stream: bool                # Canlı stdout/düşünce akışı verebiliyor mu
  can_cancel: bool                # Süreci temiz iptal edebiliyor mu
  can_pause: bool                 # Duraklatma desteği var mı
  can_resume: bool                # Oturumu devam ettirebiliyor mu
  supports_structured_output: bool# JSON/şema çıktısı garantisi
  supports_subagents: bool        # Alt agent delege edebiliyor mu
  supports_mcp: bool              # MCP araç protokolünü destekliyor mu
  can_execute: bool               # Yerel kabuk/araç komutu çalıştırabiliyor mu
```

### RuntimeAdapter Arayüzü

```python
class RuntimeAdapter(ABC):
    def run(task, agent, connection, workspace, run_id) -> AgentResult: ...
    def stream(task, agent, connection, workspace, run_id) -> AsyncIterator[StreamChunk]: ...
    def cancel(run_id) -> None: ...
    def status(run_id) -> RunStatus: ...
    def features() -> RuntimeFeatures: ...
    def capabilities() -> set[Capability]: ...
    def health(connection) -> HealthStatus: ...
    def doctor(connection) -> RuntimeDoctorResult: ...
```

### RuntimeDoctor (`p2p doctor` Kanıtı)

Bir bağlantının bu makinede gerçekten çalışıp çalışmadığı varsayıma bırakılamaz; `p2p doctor` ile somut olarak kanıtlanır:

```json
{
  "connection_id": "gemini-cli-local",
  "available": true,
  "authenticated": true,
  "can_read": true,
  "can_write": true,
  "can_execute": true,
  "supports_structured_output": true,
  "supports_cancellation": true
}
```

Adapter'ın sorumlulukları: çağrıyı kurmak, zaman aşımı uygulamak, ham çıktıyı
`.p2p/runs/<run_id>/` altına kaydetmek, sonucu türetmek (`docs/02 §3` — git +
kapılar + result.json), ve onay istemi geldiğinde **anında `ERROR`** vermek
(askıda kalmamak).

Sorumlu **olmadıkları:** hangi task'ın çalışacağı, promptun içeriği, sonucun
kabul edilip edilmeyeceği, hangi bağlantının seçileceği.

> Bir runtime'ın CLI mi, SDK mı (ör. Antigravity Python SDK), HTTP mi olduğu **adapter'ın iç meselesidir**.
> Bu sınır sayesinde `docs/11`'deki doğrulanmamış SDK iddiaları mimariyi
> etkilemez: Antigravity Python SDK doğrulandığında `GeminiCliRuntime`'ın yanına `AntigravitySdkRuntime` eklenir, çekirdek değişmez.

### v1'de hedeflenen adapterlar

| Adapter | Çağrı / Entegrasyon | Durum |
|---|---|---|
| `ClaudeCodeRuntime` | `claude -p … --output-format json` | `docs/11 V2` ✔ |
| `GeminiCliRuntime` | `gemini -p … --output-format json --approval-mode auto_edit --policy …` | `docs/11 V1` ✔ |
| `AntigravitySdkRuntime` | Antigravity Python SDK (`agent`, `tools`, `safety policies`) | `docs/11 V3` Spike |
| `MockRuntime` | kayıtlı yanıt oynatma (modelsiz testler için) | Faz 1'de tamamlandı |

`ApiRuntime`, `OllamaRuntime`, `GatewayRuntime` arayüzde tanımlıdır ama v1'de
uygulanmaz. Arayüzün doğru olduğunun kanıtı, Faz 9'da üçüncü bir adapter'ın
çekirdeğe dokunmadan eklenebilmesidir.

## 5. Capability routing

Model adına göre değil, **yeteneğe ve politikaya** göre seçim. İki aşamalı.

### Aşama 1 — Uygunluk süzgeci (ikili)

Şu koşulların hepsini sağlamayan bağlantı aday bile değildir:

```
✓ task.capabilities ⊆ connection.capabilities
✓ connection.health == ok
✓ automation_policy.third_party_automation != prohibited
✓ connection.limits içinde kalınıyor (kota, eşzamanlılık)
✓ task.risk seviyesi bu bağlantı için izinli
```

### Aşama 2 — Puanlama (sıralama)

```
score = capability_match
      × quality[capability]
      × reliability
      × availability
      ÷ (cost_weight × latency_weight)
```

v1'de `quality` ve `reliability` **elle tanımlı** bir tablodan gelir ve
kullanıcı düzenleyebilir. Telemetriden öğrenme Faz 9+'dır: önce ölçüm
altyapısı, sonra öğrenme.

### Uygun aday yoksa: `UNROUTABLE`

Task `ESCALATED` olur ve mesaj somut olur:

```
UNROUTABLE  E2E-001
  gerekli:  browser, test
  bağlantılarınızın hiçbiri 'browser' sağlamıyor.
  öneri:    gemini_cli bağlantısı ekleyin veya bu task'ı kapsam dışı bırakın.
```

Bu, "hiçbir şey olmuyor" hatasının önündeki tek savunmadır.

## 6. `routing.yaml`

```yaml
connections:
  - id: claude-pro
    kind: subscription
    runtime: claude_code
    credential_ref: session
    capabilities: [architecture, review, security, planning, research]
    quality: { architecture: 0.94, review: 0.93, security: 0.92 }
    limits: { concurrency: 2, daily_runs: 40 }
    automation_policy: { third_party_automation: unknown }

  - id: gemini-ultra
    kind: subscription
    runtime: gemini_cli
    credential_ref: session
    capabilities: [backend, frontend, database, test, browser, devops, docs]
    quality: { backend: 0.91, frontend: 0.90, browser: 0.88 }
    limits: { concurrency: 4, daily_runs: 400 }
    automation_policy: { third_party_automation: unknown }

policy:
  mode: auto                 # auto | manual
  risk_rules:
    high:   { require_quality_min: 0.90 }
    medium: {}
    low:    { prefer_cost_tier: [free, subscription] }

escalation:
  on_repeated_failure:
    backend:  claude-pro
    frontend: claude-pro
```

`mode: manual`, ileri kullanıcıya capability → connection eşlemesini doğrudan
yazma imkânı verir; `auto` puanlamayı kullanır. Her iki durumda da uygunluk
süzgeci atlanamaz.

## 7. Gateway'in yeri

```
Orchestrator ─▶ Router ─▶ Connection ─▶ Runtime ─▶ [Gateway] ─▶ Provider ─▶ Model
```

Gateway, `Connection`'ın **altında** bir taşıma detayıdır. Orchestrator onu
görmez; adapter görür.

**ADR-005 hâlâ geçerli:** gateway *"hangi sağlayıcıya nasıl ulaşırım"*
problemini çözer, P2P *"bu işi kim yapmalı"* problemini. Bir gateway'i
orchestrator konumuna koymak, bu ikisini karıştırmaktır.

v1'de gateway uygulanmaz; `kind: gateway` bir `Connection` türü olarak
tanımlıdır ve `GatewayRuntime` Faz 9'da eklenebilir.

## 8. `p2p doctor`

Her bağlantı için: ikili PATH'te mi · oturum açık mı · basit yazma testi
geçiyor mu · beyan edilen yetenekler yoklanabiliyor mu · kota kalmış mı ·
`automation_policy` `unknown` mı (uyarı).

Orchestrator, çalıştırmadan **önce** planın gerektirdiği her yeteneğin en az
bir sağlıklı bağlantısı olduğunu doğrular. Yarı yolda kota bitmesi veya
`UNROUTABLE`'a çarpmak en can sıkıcı başarısızlık modudur.

## 9. Maliyet muhasebesi

Abonelikte token maliyeti görünmez; ölçülen **çalıştırma sayısı ve süredir**.

```
connection_id, capability, task_id, duration_ms, outcome, timestamp
```

`p2p cost` bundan "hangi yetenek hangi bağlantının kotasını yiyor" raporunu
üretir. `routing.yaml`'ı ayarlamanın tek dürüst girdisi budur; tahminle
routing ayarlamak işe yaramaz.
