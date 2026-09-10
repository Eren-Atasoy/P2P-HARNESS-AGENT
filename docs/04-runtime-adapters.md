# 04 — Runtime Adapter Sözleşmesi

## 1. Dört ayrı kavram

Bunları tek arayüzde toplamak, sonradan geri dönüşü olmayan bir hatadır.

| Kavram | Tanım | Örnek |
|---|---|---|
| **Capability** | Yapılacak işin türü | `backend`, `review` |
| **Agent** | Bir rol + kalıcı talimat kümesi | "Backend Engineer" |
| **Runtime** | Agent'ı çalıştıran yürütücü | `claude -p`, `gemini -p` |
| **Model** | Runtime'ın kullandığı ağırlıklar | runtime'ın `-m` bayrağıyla seçilir |

Çekirdek kod yalnızca **Capability** ve **Runtime** bilir. Model adı hiçbir
zaman koda yazılmaz; `routing.yaml`'dan gelir. Bu kural sayesinde model
isimleri değiştiğinde (ki sürekli değişiyor) hiçbir şey kırılmaz.

## 2. RuntimeAdapter arayüzü

Kavramsal sözleşme (uygulama Gemini'ye ait):

```
run(task: TaskContract, prompt: str, workspace: Path, run_id: str)
    -> AgentResult

capabilities() -> set[Capability]     # bu runtime neyi yapabilir
health() -> HealthStatus              # kurulu mu, oturum açık mı
cost_hint() -> CostTier               # free | cheap | expensive
```

Adapter'ın sorumlulukları:

1. Komut satırını kurmak
2. Alt process'i başlatmak, zaman aşımı uygulamak
3. stdout/stderr'i `.p2p/runs/<run_id>/` altına ham kaydetmek
4. `result.json`'u okuyup `AgentResult`'a ayrıştırmak
5. `AgentResult`'ı türetmek — dosya yoksa git + kapı sonuçlarından
   çıkarmak (`docs/02 §3`), asla uydurmamak
6. **Onay istemi davranışını uygulamak:** stdin kapalı çalıştırılır; runtime
   bir onay istemi üretirse bu **anında başarısızlık**tır (`ERROR` sınıfı),
   zaman aşımına kadar beklenmez. Askıda kalan bir istem, her çalıştırmada
   20 dakika yakar ve sessizce yaşanır. (C1)

Adapter'ın sorumlu **olmadıkları**: hangi task'ın çalışacağı, promptun içeriği,
sonucun kabul edilip edilmeyeceği.

## 3. Somut adapterlar

### 3.1 `claude` — mimar / gözden geçiren

```
claude -p "<prompt>"
  --output-format json
  --add-dir <workspace>
  --allowedTools "Read Grep Glob Write(.p2p/docs/**) Write(.p2p/acr/**)"
  --append-system-prompt "<rol talimatı>"
```

Notlar:

- Mimarlık ve inceleme rollerinde **kod yazma izni verilmez**. Yazma izni
  yalnızca `.p2p/docs/**` ve `.p2p/acr/**` altına.
- `CLAUDE.md` workspace kökünde olduğu için otomatik yüklenir; rol talimatı
  `--append-system-prompt` ile eklenir.
- Uzun mimari üretimlerde `--output-format stream-json` ile ilerleme
  gösterilebilir; sonuç yine `result.json`'dan okunur.

### 3.2 `gemini` — uygulayıcı

```
gemini -p "<prompt>"
  --output-format json
  --approval-mode auto_edit
  --include-directories <worktree>
  [-m <model>]
```

Notlar:

- `--approval-mode auto_edit`: düzenlemeleri onaylar. `yolo` **kullanılmaz** —
  keyfi komut çalıştırma yetkisi tehdit modelimizin kabul etmediği bir risktir
  (`docs/06`).
- **Dar kapsamlı kabuk izni (C1, ADR-008).** Agent yalnızca **test koşucusunu**
  çalıştırabilir. `--policy` ile ikili adı ve argüman kalıbı sabitlenir:

  ```
  allow: ["pytest", "python -m pytest", "npx vitest run", "npm test"]
  deny:  ["*"]
  ```

  Gerekçe: yasakladığımız şey **keyfi** komut, tüm komutlar değil. Bu izin
  olmadan `GEMINI.md §3`'teki "testi bir kez kırmızı gör" kanıtı imkânsız hâle
  gelir ve sistem, çalıştırılmamış testler için "geçti" raporuna güvenmek
  zorunda kalır — projenin tolere edemeyeceği tek başarısızlık budur.
- Bağımlılık kurulumu, migration ve docker işleri agent'a **değil**, kapılara
  aittir; orchestrator çalıştırır. Dar izin bunları kapsamaz.
- `GEMINI.md` worktree kökünde otomatik yüklenir → kalıcı kurallar promptu
  şişirmez.
- `--policy` ile yol kısıtları ikinci savunma katmanı olarak tanımlanır.
  Birinci katman yine de orchestrator'ın git doğrulamasıdır (`docs/02 §3`).

### 3.3 `mock` — test runtime'ı

Kayıtlı yanıtları geri oynatır. P2P'nin kendi testleri gerçek model
çağırmaz; aksi hâlde test paketi hem yavaş hem non-deterministik olur.
Bu adapter Faz 1'de yazılır, sonradan eklenmez.

## 4. Prompt derleme — katmanlar

Prompt tek parça bir metin değildir. Beş katmandan derlenir ve her katmanın
farklı bir ömrü vardır:

```
1. KALICI KURALLAR      GEMINI.md / CLAUDE.md      (dosyadan, otomatik)
2. ROL                  prompts/roles/<rol>.md     (nadiren değişir)
3. GÖREV                TaskContract JSON          (task başına)
4. BAĞLAM               inputs → dosya içerikleri  (bütçelenir)
5. TUR                  fix/review geri bildirimi  (tur başına)
```

Her katman ayrı dosyada versiyonlanır. **Prompt metni koda gömülmez** —
gömülürse gözden geçirilemez ve A/B karşılaştırılamaz.

### 4.1 Bağlam bütçesi

Agent'a repo'nun tamamı verilmez. Kural:

| Öncelik | İçerik | Sınır |
|---|---|---|
| 1 | TaskContract | tam |
| 2 | `inputs` içindeki belgeler | tam |
| 3 | `allowed_paths` içindeki mevcut dosyalar | tam, 40k token'a kadar |
| 4 | Bağımlı task'ların arayüz özetleri | özet |
| 5 | Diğer her şey | **verilmez** |

Bütçe aşılırsa task çok büyüktür → bölünmelidir (`estimated_size=L` zaten
bunun sinyalidir).

Gerekçe: bağlam ne kadar büyükse, modelin talimatın ortasını kaçırma olasılığı
o kadar yüksek. Fazla bağlam vermek yardım değil, gürültüdür.

## 5. Sağlık kontrolü

`p2p doctor` her runtime için:

| Kontrol | Başarısızsa |
|---|---|
| İkili PATH'te mi | Kurulum talimatı, o runtime devre dışı |
| Oturum açık mı (kimlik doğrulama) | Giriş komutu gösterilir |
| Basit yazma testi geçiyor mu | İzin ayarı sorunu bildirilir |
| Kota kalmış mı (mümkünse) | Uyarı; koşu sırasında biterse `QUOTA` → `PAUSED` (`docs/03 §3.4`) |

Orchestrator, çalıştırmaya başlamadan önce **planın gerektirdiği tüm
runtime'ların** sağlıklı olduğunu doğrular. Yarısında kota bitmesi, en can
sıkıcı başarısızlık modudur.

## 6. Zaman aşımı ve iptal

| Katman | Sınır |
|---|---|
| Tek agent çalıştırması | 20 dk (yapılandırılabilir) |
| Tek kapı | 10 dk |
| Toplam task (tüm denemeler) | 90 dk |
| Tüm proje | kullanıcı tanımlı, varsayılan yok |

Zaman aşımında process ağacı sonlandırılır, worktree olduğu gibi bırakılır
(inceleme için), `TIMEOUT` olayı yazılır, task `ESCALATED` olur.

## 7. Maliyet ve kota muhasebesi

Abonelik tabanlı runtime'larda token maliyeti görünmez. Bu yüzden ölçülen
şey **çalıştırma sayısı ve süresidir**:

```
runtime, capability, task_id, duration_ms, timestamp
```

`p2p cost` bu günlükten şunu üretir: hangi yetenek hangi runtime'ın kotasını
yiyor. Bu rapor, `routing.yaml`'ı ayarlamanın tek dürüst girdisidir —
tahminle routing ayarlamak işe yaramaz.
