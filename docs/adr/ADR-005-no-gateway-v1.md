# ADR-005 — v1'de model gateway yok (OmniRoute dâhil)

**Durum:** Kabul edildi · 2026-09-10

## Bağlam
Bir model gateway (OmniRoute vb.) çok sağlayıcılı erişimi tek API arkasında
toplar ve cazip görünür.

## Karar
v1'de gateway **kullanılmayacak**. Soyutlama noktası `RuntimeAdapter`'dır.

## Gerekçe
Gateway'ler **API anahtarı** tabanlı erişimi birleştirir. Bizim birincil
kullanım senaryomuz **abonelik oturumu** üzerinden çalışan yerel CLI'lardır
(`claude`, `gemini`). Gateway bu senaryoda hiçbir problemi çözmez; yalnızca
bir dolaylılık katmanı ve bir bağımlılık ekler.

## Alternatifler
- **Gateway'i çekirdeğe koymak:** Çözmediği bir problem için kalıcı bağlanım.
- **Kendi gateway'imizi yazmak:** Kapsam dışı; problemimiz yönlendirme değil.

## Sonuçlar
- (+) Bir bağımlılık ve bir hata kaynağı eksik
- (+) Abonelik senaryosu birinci sınıf kalır
- (−) API tabanlı çok modelli kullanım isteyen kullanıcı kendi adapter'ını yazar
- Gelecek: gateway gerekirse **bir RuntimeAdapter olarak** eklenir; çekirdek
  değişmez. Bu ADR'yi geçersiz kılmaz, genişletir.
