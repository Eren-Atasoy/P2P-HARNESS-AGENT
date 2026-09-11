# 02 — Veri Modeli ve Sözleşmeler

Bu belge, sistemin **değişmez arayüzüdür**. Buradaki alan adları koda birebir
yansır. Bir alan eklemek geriye dönük uyumludur; bir alanı silmek veya anlamını
değiştirmek ADR gerektirir.

Genel kurallar:

- Tüm zaman damgaları ISO-8601 UTC (`2026-09-10T14:03:11Z`).
- Tüm id'ler `^[A-Z]+-[0-9]{3}$` (task) veya UUIDv4 (run).
- Tüm yollar workspace köküne **göreli**, POSIX ayırıcı (`/`) ile.
- Bilinmeyen alanlar ayrıştırmada **reddedilir** (`extra="forbid"`).
  Agent uydurma alan üretirse sessizce yutulmaz, hemen kırılır.

---

## 1. ProjectSpec — `.p2p/project.json`

Bir kere yazılır, sonra salt-okunur. Değişmesi projenin yeniden planlanması
demektir.

| Alan | Tip | Açıklama |
|---|---|---|
| `id` | uuid | Proje kimliği |
| `name` | string | Kebab-case proje adı |
| `prompt` | string | Kullanıcının orijinal isteği, değiştirilmeden |
| `created_at` | datetime | — |
| `p2p_version` | semver | Üreten P2P sürümü |
| `stack` | object | Seçilen teknoloji yığını (aşağıda) |
| `decisions` | array | İnsanın verdiği kararlar (bkz. §6) |
| `targets` | array | `web` \| `api` \| `mobile` \| `cli` |

`stack` örneği:

```json
{
  "backend":  { "language": "python", "framework": "fastapi", "version": "0.115" },
  "frontend": { "language": "typescript", "framework": "next", "version": "15",
                "ui": "tailwind + radix", "tokens": "docs/12" },
  "database": { "engine": "postgres", "version": "16", "orm": "sqlalchemy" },
  "auth":     { "strategy": "jwt", "provider": "self" },
  "infra":    { "runtime": "docker-compose" }
}
```

---

## 2. TaskContract — `.p2p/tasks/<id>.json`

Sistemin kalbi. Bir agent'a verilen **tek** talimat kaynağı budur.

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| `id` | string | ✔ | `API-001` |
| `title` | string | ✔ | Tek satır, emir kipi |
| `capabilities` | enum[] | ✔ | Gerekli yeteneklerin **tamamı**: `architecture` \| `planning` \| `backend` \| `frontend` \| `database` \| `migration` \| `test` \| `browser` \| `security` \| `review` \| `docs` \| `devops` \| `research` \| `ui` \| `design-system` |
| `risk` | enum | ✔ | `low` \| `medium` \| `high` — otonomi ve routing bunu kullanır (`docs/03 §5`) |
| `depends_on` | string[] | ✔ | Task id listesi (boş olabilir) |
| `intent` | string | ✔ | 2-5 cümle: ne ve **neden**. Uygulama detayı yok |
| `acceptance_criteria` | AC[] | ✔ | Bkz. §2.1 — en az 1 tane |
| `inputs` | path[] | ✔ | Agent'ın okuyacağı belge/dosyalar |
| `allowed_paths` | glob[] | ✔ | Yazma izni olan yollar |
| `forbidden_paths` | glob[] | ✔ | Açıkça yasaklı (kural: `allowed`'ı ezer) |
| `gates` | string[] | ✔ | Çalıştırılacak kalite kapıları (`docs/05`). UI dokunan task'lar için `G_UI_1..4` (`docs/12 §4`) |
| `estimated_size` | enum | ✔ | `S` \| `M` \| `L` — `L` ise bölünmelidir |
| `max_attempts` | int | ✔ | Varsayılan 3 |
| `human_approval` | bool | ✔ | Birleştirme öncesi insan onayı gerekli mi |
| `result_path` | path | ✔ | Agent'ın sonucunu yazacağı dosya |
| `acr_path` | path | ✔ | Agent'ın ACR yazacağı dosya |
| `notes` | string | ✖ | Mimarın serbest notu |
| `github` | object? | ✖ | GitHub entegrasyonu: `{ issue: int?, pr: int?, repo: string? }` |

> **`result_path` ve `acr_path` yol politikasından muaftır.** `forbidden_paths`
> bunları hiçbir zaman kapsamaz, `allowed_paths` içinde tekrarlanmaları
> gerekmez. Aksi hâlde `.p2p/**` yasağı, agent'ın rapor vermesini de yasaklar. (M7)

### 2.1 AcceptanceCriterion

Bir kabul kriteri **gözlemlenebilir** olmak zorundadır. "Hızlı", "güvenli",
"temiz" yasaktır.

| Alan | Tip | Açıklama |
|---|---|---|
| `id` | string | `AC-1` |
| `statement` | string | Gözlemlenebilir davranış |
| `verified_by` | enum | `test` \| `gate` \| `manual` |
| `test_ref` | string? | `verified_by=test` ise: test dosyası::test adı |
| `gate_ref` | string? | `verified_by=gate` ise: kapı adı |

> **Kritik kural:** `verified_by=manual` olan bir kriter, `human_approval=true`
> yapmak zorundadır. Aksi hâlde asla doğrulanmamış bir kriterle "DONE"
> durumuna geçilir. Bu, en sinsi kalite kaçağıdır.

### 2.2 Örnek

```json
{
  "id": "API-001",
  "title": "Randevu CRUD uçlarını uygula",
  "capabilities": ["backend", "security"],
  "risk": "high",
  "depends_on": ["DB-001"],
  "intent": "Randevu kaynağı üzerinde kimliği doğrulanmış CRUD sağlanacak. Sahiplik kontrolü zorunlu; bir kullanıcı başkasının randevusunu göremez veya değiştiremez.",
  "acceptance_criteria": [
    { "id": "AC-1", "statement": "POST /appointments geçerli gövdeyle 201 ve gövdede id döner",
      "verified_by": "test", "test_ref": "tests/api/test_appointments.py::test_create_returns_201" },
    { "id": "AC-2", "statement": "Token olmadan istek 401 döner",
      "verified_by": "test", "test_ref": "tests/api/test_appointments.py::test_requires_auth" },
    { "id": "AC-3", "statement": "Başka kullanıcının randevusuna GET 404 döner (403 değil, varlık sızdırılmaz)",
      "verified_by": "test", "test_ref": "tests/api/test_appointments.py::test_cross_tenant_is_404" }
  ],
  "inputs": [".p2p/docs/architecture.md", ".p2p/docs/api-contract.md", "backend/models/"],
  "allowed_paths": ["backend/api/**", "backend/services/**"],
  "forbidden_paths": ["backend/models/**", "tests/**", ".p2p/**", "frontend/**", "infra/**"],
  "result_path": ".p2p/runs/{run_id}/result.json",
  "acr_path": ".p2p/acr/",
  "gates": ["lint", "typecheck", "unit", "contract"],
  "estimated_size": "M",
  "max_attempts": 3,
  "human_approval": false
}
```

`forbidden_paths`'te `backend/models/**` olması bilinçli: şema `DB-001`'in
sorumluluğu. API agent'ı şemayı "biraz düzeltmek" isterse yapamaz — ACR açar.
Bu, üretimde en sık görülen sessiz mimari kaymayı engeller.

`tests/**` de yasaklı: kabul kriterine bağlı testleri **ayrı bir `TEST-`
task'ı** yazar (`docs/05 §7`). Uygulayıcı yalnızca kendi iç birim testlerini
`allowed_paths` içinde tutabilir ve bunlar kabul kriteri sayılmaz. Kuralın
tamamı için bkz. `docs/05 §7`. (M2)

---

## 3. AgentResult — `.p2p/runs/<run_id>/result.json`

Agent'ın yapılandırılmış çıktısı. stdout log'dur, veri değildir.

> **Tamamlayıcıdır, zorunlu değildir. (C4)**
> Bir task'ın gerçek durumu **üç bağımsız kaynaktan** türetilir:
> (1) `git status` — ne değişti, (2) kapı sonuçları — çalışıyor mu,
> (3) `result.json` — agent ne düşünüyor.
>
> Dosya yoksa veya ayrıştırılamıyorsa `outcome`, ilk iki kaynaktan çıkarılır;
> `assumptions` / `acr` kaybı bir uyarı olarak kaydedilir. Bilinmeyen alanlar
> loglanıp atılır — `extra="forbid"` yalnızca **bilinen** alanların tipine
> uygulanır. Aksi hâlde şema katılığı, 20 dakikalık doğru bir işi tek bir
> fazladan alan yüzünden çöpe atar.

| Alan | Tip | Açıklama |
|---|---|---|
| `task_id` | string | — |
| `run_id` | uuid | — |
| `outcome` | enum | `completed` \| `blocked` \| `failed` |
| `summary` | string | ≤ 5 satır, ne yapıldı |
| `files_changed` | string[] | Agent'ın kendi beyanı (doğrulanır, güvenilmez) |
| `criteria_addressed` | string[] | Ele alınan AC id'leri |
| `assumptions` | string[] | Yapılan varsayımlar — boş bırakmak yasak değil ama şüphelidir |
| `acr` | string? | `outcome=blocked` ise ACR dosya yolu |
| `failure_reason` | string? | `outcome=failed` ise |
| `usage` | RunUsage? | Harcama/kullanım kaydı: `{ tokens, duration_ms, estimated_cost, model }` |

`RunUsage` genişletilebilir bir yapıdır; v1'de temel süre ve token takibi sağlar, ileride kota ve faturalandırma için zemin hazırlar.

### Doğrulama kuralı

Orchestrator `files_changed` alanına **inanmaz**. `git status --porcelain` ile
karşılaştırır. Uyuşmazlık varsa:

- Beyan edilmeyen değişiklik varsa → `POLICY_VIOLATION` olayı, task `BLOCKED`
- `allowed_paths` dışında değişiklik varsa → değişiklik geri alınır, `FAILED`

Bu kontrol, "agent nazikçe başka bir dosyayı da düzeltti" senaryosunun tek
savunmasıdır ve atlanamaz.

---

## 4. GateResult — doğrulama çıktısı

| Alan | Tip | Açıklama |
|---|---|---|
| `gate` | string | `unit`, `lint`, `typecheck`, `e2e`, `security`… |
| `status` | enum | `PASS` \| `WARN` \| `FAIL` \| `SKIPPED` \| `ERROR` |
| `exit_code` | int | Ham çıkış kodu |
| `duration_ms` | int | — |
| `log_path` | string | `.p2p/runs/<run_id>/gates/<gate>.log` |
| `failures` | Failure[] | Ayrıştırılmış hatalar (varsa) |

`Failure`: `{ file, line, rule, message }`

`ERROR` ile `FAIL` farklıdır ve karıştırılırsa sistem yanlış öğrenir:

- `FAIL` → kod yanlış. Fix döngüsüne git.
- `ERROR` → kapı çalıştırılamadı (araç yok, ortam bozuk). Fix döngüsüne
  **gitme**; bu bir altyapı sorunudur, insana escalate et.
- `QUOTA` → runtime kotası bitti. Ne kod ne altyapı sorunu; **zaman** sorunu.
  Task `PAUSED` olur, `docs/03 §3.4`'teki davranış uygulanır. (M6)

---

## 5. ReviewResult — `.p2p/reviews/<task_id>-<n>.json`

| Alan | Tip | Açıklama |
|---|---|---|
| `task_id` | string | — |
| `attempt` | int | — |
| `verdict` | enum | `APPROVED` \| `CHANGES_REQUESTED` \| `REJECTED` |
| `findings` | Finding[] | — |
| `architecture_compliance` | bool | Mimariye uyuyor mu |

`Finding`: `{ severity: CRITICAL|HIGH|MEDIUM|LOW, file, line, issue, suggestion }`

Karar kuralı (gözden geçiren agent'a bırakılmaz, orchestrator uygular):

| Bulgu | Sonuç |
|---|---|
| ≥1 CRITICAL | `REJECTED` — yeniden uygula, gerekirse task'ı böl |
| ≥1 HIGH | `CHANGES_REQUESTED` |
| Sadece MEDIUM/LOW | `APPROVED`, bulgular teknik borç olarak kaydedilir |

> Gözden geçiren "verdict" alanını doldurur ama orchestrator onu **yeniden
> hesaplar**. Model kendi kuralını esnetemez.

---

## 6. Decision — insan kararları

Belirsizlik çözümü bir birinci sınıf kayıttır; prompt geçmişinde kaybolamaz.

| Alan | Tip |
|---|---|
| `id` | `DEC-001` |
| `question` | string |
| `options` | string[] |
| `chosen` | string |
| `rationale` | string |
| `decided_by` | `human` \| `default` |
| `kind` | `ambiguity` \| `gate` \| `steer` \| `retro` |
| `decided_at` | datetime |

`decided_by=default` → sistem varsayılanı kullandı, insan görmedi. Bu kayıtlar
`p2p status` çıktısında ayrıca listelenir; sessiz varsayılan tehlikelidir.

---

## 7. Event — `.p2p/events.jsonl`

Her satır bağımsız bir JSON nesnesi. **Asla güncellenmez, asla silinmez.**

| Alan | Tip |
|---|---|
| `seq` | int (monoton artan — tek yazar, yazım kilitli) |
| `ts` | datetime |
| `type` | enum (aşağıda) |
| `task_id` | string? |
| `run_id` | uuid? |
| `payload` | object |

Olay türleri:

```
PROJECT_CREATED      TASK_CREATED         TASK_STATE_CHANGED
RUN_STARTED          RUN_FINISHED         GATE_FINISHED
REVIEW_FINISHED      DECISION_RECORDED    ACR_OPENED
ACR_RESOLVED         POLICY_VIOLATION     MERGE_COMPLETED
HUMAN_APPROVED       HUMAN_REJECTED       ESCALATED
TASK_PAUSED          TASK_UNROUTABLE      HUMAN_STEERED
RETRO_APPLIED        CONNECTION_HEALTH    BUDGET_EXCEEDED
ISSUE_CREATED        PR_CREATED           PR_MERGED
```

`state.json` bu günlüğün baştan oynatılmasıyla üretilir. Bu tasarımın
pratik faydası: bir hatayı incelerken "sistem o an ne biliyordu" sorusunun
kesin cevabı vardır.

---

## 8. RoutingConfig — `.p2p/routing.yaml`

> Tam şema ve seçim algoritması `docs/04`'tedir. Burada yalnızca veri modeli
> açısından bağlayıcı olan kısım tutulur.

Yönlendirme **capability tabanlıdır**: bir task hangi yetenekleri gerektirdiğini
bildirir, router hangi `Connection`'ın onları sağladığına bakar. Çekirdek kodda
hiçbir sağlayıcı veya model adı geçmez.

```yaml
# capability -> uygun bağlantılar (öncelik sırasıyla); tam şema: docs/04 §6
defaults:
  architecture: [claude-pro]
  review:       [claude-pro]
  security:     [claude-pro]
  backend:      [gemini-ultra, claude-pro]
  frontend:     [gemini-ultra, claude-pro]
  browser:      [gemini-ultra]
```

`escalation.on_repeated_failure` küçük ama yüksek getirili bir mekanizmadır:
ucuz model iki kez takılırsa pahalı modele geçilir. Böylece maliyet, işin
gerçek zorluğuna göre kendiliğinden ayarlanır.
