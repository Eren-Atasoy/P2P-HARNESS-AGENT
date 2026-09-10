# ADR-008 — Uygulayıcı agent'a dar kapsamlı kabuk izni

**Durum:** Kabul edildi · 2026-09-10 · **Kaynak:** architecture-review C1

## Bağlam

`docs/06`'daki tehdit modeli, agent'a keyfi kabuk erişimi vermeyi reddediyor
(T4, T5, T9). Bu doğru. Ancak `GEMINI.md §3`, "bitti" tanımının parçası olarak
agent'ın testlerini çalıştırmasını ve **implementasyon bozukken bir kez kırmızı
görmesini** istiyor. Bu iki kural aynı anda sağlanamıyordu.

Sonuç, gözden geçirmede ortaya çıktı: agent ya hiçbir zaman `completed` dönemez,
ya da çalıştırmadığı testler için "geçti" der. İkincisi olursa doğrulama
zincirinin tamamı yalan bir raporun üstüne kurulur.

## Karar

Uygulayıcı agent'a **yalnızca test koşucusunu** çalıştırma izni verilir.
İkili adı ve argüman kalıbı `--policy` ile sabitlenir; diğer tüm komutlar
reddedilir. Yeni bir eylem sınıfı tanımlanır: `NARROW` (`docs/06 §6`).

```
allow: ["pytest", "python -m pytest", "npx vitest run", "npm test"]
deny:  ["*"]
```

Bağımlılık kurulumu, migration, docker ve git orchestrator'da kalır.

## Alternatifler

- **Kabuk tamamen kapalı, doğrulamayı kapılar yapar.** En güvenli. Ama
  "kırmızı-yeşil kanıtı" kaybolur; bu, `docs/05 §7`'deki test kalitesi
  savunmasının en güçlü maddesiydi. AI'ın kendi kodunu doğrulayan sahte test
  yazma eğilimine karşı elimizde yalnızca statik tautoloji taraması kalırdı.
- **Sandbox içinde geniş izin (`gemini -s`).** Doğrulama gücü en yüksek,
  izolasyon en güçlü seçenek. Reddedilme gerekçesi kapasite değil, bağımlılık:
  Windows'ta Docker/Podman zorunluluğu getiriyor ve worktree erişimiyle sandbox
  sınırının nasıl kesişeceği Faz 0'da ayrıca doğrulanmalı. Faz 9 sertleştirmesi
  için açık bir yükseltme yolu olarak kalıyor.

## Sonuçlar

- (+) Kırmızı-yeşil kanıtı korunur; test kalitesi savunması ayakta kalır
- (+) Yasaklanan şey **keyfi** komut olmaya devam eder; tehdit modeli bozulmaz
- (−) Kabuk yüzeyi sıfır değil. Test koşucusunun kendisi keyfi kod çalıştırır
  (test dosyaları koddur) — yani bu izin, "agent yazdığı kodu çalıştırabilir"
  demenin dolaylı yoludur. Bunu kabul ediyoruz; agent zaten o kodu repoya
  yazabiliyor ve kapılar onu nasılsa çalıştıracak
- (−) Politika kalıbı yığına özgü; her Blueprint kendi izin listesini bildirmeli
- Yükseltme yolu: sandbox (`gemini -s`) doğrulandığında bu ADR genişletilir
