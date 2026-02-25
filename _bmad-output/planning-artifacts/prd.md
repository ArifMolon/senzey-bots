---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-e-01-discovery
  - step-e-02-review
  - step-e-03-edit
lastEdited: '2026-02-25'
editHistory:
  - date: '2026-02-25'
    changes: 'Added Risk & Profit Management guardrails, expanded scope to include CFD asset classes and Phase 2 ERC20 vision'
classification:
  date: '2026-02-25'
  projectType: 'Web App'
  domain: 'Fintech'
  complexity: 'High'
  projectContext: 'Brownfield'
inputDocuments:
  - _bmad-output/project-context.md
  - _bmad-output/freqtrade/project-context.md
documentCounts:
  briefCount: 0
  researchCount: 0
  brainstormingCount: 0
  projectDocsCount: 2
workflowType: 'prd'
---

# Product Requirements Document - senzey-bots

**Author:** Senzey
**Date:** 2026-02-25

## Executive Summary

`senzey-bots` projesi, tek bir kullanıcı (Senzey) için tasarlanmış uçtan uca otonom bir algoritmik ticaret ve strateji yönetim platformudur. Bu sistem, strateji geliştirme, geriye dönük test (backtest) yapma ve canlı işlemlere (production) alma süreçlerindeki manuel iş yükünü ortadan kaldırır. Arka planda `freqtrade` (ticaret motoru) ve `trading-ig` (broker API) kullanarak kesintisiz bir otomasyon sağlar.

**What Makes This Special:**
Sistemi benzersiz kılan unsur, "Human-in-the-Loop" (Döngüdeki İnsan) prensibiyle çalışan esnek strateji üretim yeteneğidir. Kullanıcının girdiği teknik gösterge (indikatör) kurallarını doğrudan çalışabilir Freqtrade stratejilerine çeviren entegre bir Yapay Zeka (LLM) Kod Üretici Ajan barındırır. Bu yapı, mevcut analiz bilgisini anında test edilebilir ve otonom ticarete uygun hale getirir.

## Success Criteria

### User & Business Success
- **Mimari Tamamlanma:** Arayüz, LLM (strateji üretici), Freqtrade ve IG API uçtan uca entegre edilerek ilk otonom işlemin (trade) başarılı şekilde açılıp kapanması.
- **Zaman Tasarrufu:** Yeni bir strateji fikrinin canlıya alınma süresinin, LLM ve otomasyon sayesinde dakikalar seviyesine inmesi.
- **Finansal Getiri:** Canlıya alınan istatistiksel stratejilerin pozitif net getiri (ROI) sağlaması.

### Technical Success
- Modüler ve genişletilebilir bir 'Agentic' mimari (AI ajanlarının birbiriyle haberleştiği yapı) kurulması.
- Freqtrade ile IG broker API'si arasında kesintisiz ve hatasız bir emir akışının sağlanması.

## Product Scope

### MVP (Phase 1)
- TradingView PineScript / Python kodu yapıştırılabilen veya prompt ile strateji üreten UI (Streamlit).
- İndikatör kurallarını Freqtrade stratejisine dönüştüren Kod Üretici LLM Ajanı.
- Arayüz üzerinden backtest yapma ve sonuçları görüntüleme.
- "Human in the loop" onayıyla IG broker üzerinden canlı (production) işlemlere başlama ve "Kill-Switch".
- Varlık Sınıfları: IG Markets üzerinden Altın (Gold), Gümüş (Silver) ve Kripto Paralar (Bitcoin vb.) CFD işlemleri.
- Sermaye Yönetimi: Aylık 10.000 TL bütçe enjeksiyonu ile test ve mikro-canlı (micro-live) aşamaları. (İlk 3 ay ROI zorunluluğu yok, öğrenme odaklı).

### Growth (Phase 2)
- Test sonuçlarına dayanarak market/coin önerisi yapan analiz motoru.
- Yeni ajan türleri için Agent Registry.
- Phase 2: OpenZeppelin standartlarında (ERC20) kendi özel topluluk token'ımız için otomatik piyasa yapıcılık (market making) ve alım stratejileri (IG Markets dışı DEX/Web3 entegrasyonu gerektirir).

### Vision (Phase 3)
- Haber/X (Twitter) üzerinden sentiment analizi yapan otonom araştırma ajanları.
- Dış katılımcılar için Community Revenue Sharing (Gelir Paylaşımı) modeli.

## User Journeys

### 1. Strateji Geliştiricisi (Primary Path)
Senzey'in aklına kârlı bir indikatör kombinasyonu gelir. Arayüze girip kuralları yazar. LLM saniyeler içinde Freqtrade stratejisini üretir. "Backtest Et" butonuna basılır. Yüksek WinRate ve ROI görülünce "Canlıya Al" denilerek bot IG broker'da başlatılır.

### 2. Hata Giderici (Edge Case / Recovery)
Senzey, GitHub'dan bir strateji kopyalar ancak kod hatalıdır. Test sırasında hata fırlatılır. Entegre LLM ajanı hatayı otomatik analiz edip düzeltilmiş kodu önerir. Senzey onaylar, test tekrar başlar ve başarıyla sonuçlanır.

### 3. Sistem Yöneticisi (Operations)
Senzey dışarıdayken piyasada ani bir çöküş yaşanır. Telefondan mobil uyumlu arayüze giriş yapar. "Kill-Switch" butonuna basarak tüm açık işlemleri piyasa fiyatından kapatır ve botları durdurur. Risk saniyeler içinde sıfırlanır.

### 4. Topluluk Katkıcısı (Future Vision)
Dış kaynaklı bir geliştirici sisteme strateji yükler. Sistem stratejiyi test eder ve havuza alır. Strateji kâr ettikçe geliştiriciye otomatik "Revenue Share" yansıtılır.

## Domain-Specific Requirements

### Compliance & Constraints
- **Fintech Compliance Matrix:**
  - **PCI-DSS:** N/A (No card storage).
  - **SOC2:** N/A (Personal internal tool).
  - **GDPR:** Minimal (Single user).
  - **AML/KYC:** IG Markets handles this at the broker level; this tool is exempt as it is strictly for personal execution.
- **Kişisel Kullanım:** Platform kişisel kullanım amaçlıdır, dışarıya açık KYC/AML ihtiyacı yoktur.
- **Secret Yönetimi:** IG Broker ve LLM API key'leri uzaktaki bir veritabanına kaydedilmeyecek, arayüzden adım adım alınarak yerel bir `SQLite` veritabanında şifreli (AES-256) tutulacaktır.
- **Rate-Limits:** `freqtrade` motoruna entegre IG API sınırlarına tam uyulacak, by-pass edilmeyecektir.

## Innovation Analysis

### Agent-to-Agent (A2A) Mimarisi
Projenin en yenilikçi yönü `Claude Code SDK` ve Model Context Protocol (MCP) kullanılarak bir "Ajan Takımı" (Agentic Team) kurulmasıdır. Ajanlar kendi aralarında haberleşerek otonom strateji yazar ve test eder.

### Otonom Doğrulama ve Risk Yönetimi (Auto-fix)
Test (backtest) logları ve syntax hataları ajanlar arasında JSON formatında iletilerek otonom doğrulama (self-correction) döngüleri yaratılır. Sonsuz hata döngüsü ve API maliyeti (cost) riskine karşı iterasyon sınırı (örn: max 3 deneme) uygulanır.

## Project-Type Requirements (Backend / Web UI)

- **Kullanıcı Arayüzü:** Geliştirme hızı ve Python uyumu sebebiyle **Streamlit** kullanılacaktır. Arayüz ajanlar arası mesajlaşmaları ve test akışını (Agent Flow) canlı görselleştirecektir.
- **İletişim Protokolü:** Streamlit uygulaması ve arka plandaki ajanlar/servisler arasındaki iletişim standart **MCP (Model Context Protocol)** üzerinden `stdio` veya yerel ağ `SSE/HTTP` ile sağlanacaktır.
- **Kimlik Doğrulama:** Streamlit'in sunduğu basit bir parola veya Localhost/IP tabanlı erişim kısıtlaması uygulanacaktır.

## Risk & Profit Management Architecture

- **Profit Locking ("Kâr Cebe Yakışır"):** Varsayılan olarak agresif `minimal_roi` tablosu (ör: 30 dk içinde %5 kâr ise çık) ve `trailing_stop_positive_offset` (ör: %1 kârda izlemeye başla) uygulanır.
- **Capital Protection:** Varsayılan günlük maksimum drawdown %5 olarak ayarlanır. Bu seviyeye ulaşılırsa o gün için yeni işlem açılması durdurulur (Halt).
- **Staged Rollout:** Aylık 10.000 TL bütçe göz önüne alınarak, LLM stratejileri önce `dry_run` (14 gün), ardından 500-1000 TL'lik "Micro-live" aşaması, sonrasında tam sermaye tahsisi şeklinde kademelendirilir.
- **CFD Margin Rules:** IG Markets üzerindeki işlemlerde pozisyon büyüklüğü hesabın serbest marjininin %50'sini aşamaz.

## Functional Requirements

### Strategy & Testing
- **FR1:** Kullanıcı, TradingView/PineScript veya düz metin kurallarını arayüze girebilir veya hazır Python kodlarını yükleyebilir.
- **FR2:** Sistem (LLM Ajanı), girilen kuralları Freqtrade Python stratejisi koduna dönüştürebilir.
- **FR3:** Kullanıcı, seçtiği strateji için Freqtrade backtest sürecini başlatabilir ve sonuçları (ROI, WinRate vb.) görsel özet olarak görebilir.
- **FR4:** Sistem (Analiz Ajanı), hatalı backtest loglarını okuyarak hatayı tespit edip düzeltebilir (maksimum 3 iterasyon sınırı ile).

### Trading & Operations
- **FR5:** Kullanıcı, testleri geçen stratejileri IG Broker üzerinden canlı piyasada (production) otonom çalışmaya başlatabilir.
- **FR6:** Sistem, canlıya alınan stratejiler için Freqtrade Stop-Loss ve Drawdown kısıtlamalarını otomatik olarak uygulayabilir.
- **FR7:** Kullanıcı, canlı işlemleri dashboard üzerinden izleyebilir ve acil durumlarda "Kill-Switch" ile tüm işlemleri kapatabilir.

### System & Security
- **FR8:** Kullanıcı, arayüz üzerinden aktif ajanların iletişim loglarını anlık izleyebilir.
- **FR9:** Sistem, alt servisler arasında standart protokoller üzerinden görev ataması ve sonuç iletimi yapabilir.
- **FR10:** Kullanıcı, API anahtarlarını arayüzden sisteme tanımlayabilir; sistem bunları yerel veritabanında şifreli saklar ve erişimi parola/IP ile kısıtlar.
- **FR11:** Sistem, her strateji için zorunlu dinamik kâr alma (Trailing Stop-Loss) ve zamana bağlı kâr realizasyonu (Time-based ROI) kuralları uygular; kâra geçmiş bir pozisyonun başa baş (break-even) noktasının altına düşmesine izin vermez ("Kâr cebe yakışır" felsefesi).
- **FR12:** Sistem, Freqtrade koruma eklentileri (MaxDrawdown, StoplossGuard, vb.) aracılığıyla otomatik devre kesici (circuit breaker) devreye alabilir.
- **FR13:** Kullanıcı, her strateji için ayrı maksimum sermaye tavanı tanımlayabilir; sistem bu tavanı aşan emir girişimlerini reddeder.
- **FR14:** LLM tarafından üretilen stratejiler canlıya alınmadan önce otomatik statik kod analizi (yasaklı kütüphane kontrolü) ve zorunlu backtest eşik doğrulamasından (Sharpe, Max Drawdown) geçer.
- **FR15:** Yeni stratejiler canlı sermayeye geçmeden önce minimum 14 günlük zorunlu kuru çalışma (dry_run) sürecinden geçirilir.
- **FR16:** IG Markets hesabındaki serbest marjin seviyesi izlenir; kritik eşiğin altına düştüğünde yeni pozisyon açılması engellenir.
## Security & Audit Architecture

### Data Flow & Access Controls
- Tüm API anahtarları (Broker, LLM) arayüzden alındıktan sonra anında şifrelenir ve bellekte (memory) açık halde tutulma süresi minimumda tutulur.
- Arayüze erişim, güvenilir yerel ağ (localhost) veya güçlü parola doğrulaması ile sınırlandırılmalıdır.

### Audit Requirements
- Sistem, ajanların aldığı kararları, API'ye gönderilen işlem (trade) emirlerini ve hataları zaman damgalı (timestamp) olarak değişmez (immutable) bir log dosyasına kaydetmelidir.
- Bu loglar, geriye dönük finansal denetimlere (audit trail) ve hata ayıklamaya olanak tanımalıdır.

### Fraud Prevention & Risk Control
- Freqtrade'in sağladığı Drawdown ve Stop-Loss kısıtlamalarına ek olarak, günlük maksimum işlem hacmi (volume) sınırı konulmalıdır.
- Acil durumlar için "Kill-Switch", tüm açık pozisyonları anında piyasa fiyatından kapatmalı ve botların yeni işlem açmasını engellemelidir.

## Non-Functional Requirements

### Performance & Reliability
- **NFR1 (Execution Latency):** Arayüz üzerinden "Canlıya Al" emri verildiğinde, emrin IG Broker API'sine iletilme süresi (network gecikmesi hariç) 500 ms'nin altında olmalı ve bu durum APM/log analizleriyle ölçülmelidir.
- **NFR2 (LLM Timeout):** Kod üretici ajanın indikatör kurallarını koda dönüştürme süresi maksimum 60 saniye olmalıdır, as measured by integration test timing.
- **NFR3 (Uptime):** Freqtrade motoru ve Ajanlar, geçici ağ kesintilerinde en fazla 30 saniye içinde en az 5 kez otomatik yeniden bağlanmayı (auto-reconnect) denemeli ve bu durum sistem loglarıyla ölçülmelidir.
- **NFR4 (Graceful Degradation):** LLM API yanıt vermediğinde, sistem 5 saniye içinde hata fırlatmadan manuel kod giriş arayüzüne (fallback) geçiş yapabilmeli ve bu durum entegrasyon testleriyle doğrulanmalıdır.

### Security & Integration
- **NFR5 (Encryption):** Tüm API anahtarları yerel veritabanında AES-256 veya eşdeğer algoritmayla şifrelenmiş olarak (Data at Rest) tutulmalı ve bu durum kod incelemesiyle (code audit) doğrulanmalıdır.
- **NFR6 (Rate Limits):** Sistem, IG Broker'ın saniyelik/dakikalık istek sınırlarını hiçbir koşulda aşmamalıdır (Dakikada max 30 request IG limitlerine uygun olarak) ve bu durum API kullanım loglarıyla (API logs) doğrulanmalıdır.
- **NFR7 (Drawdown Protection):** Günlük drawdown -%5 eşiğini aştığında 24 saat yeni emir yasağı devreye girer; -%10 aştığında tüm açık pozisyonlar acil durum piyasa emriyle (market order) kapatılır.
- **NFR8 (Broker Stoploss):** Broker tarafında (IG Markets) on-exchange stoploss (Garantili Stop veya Normal Stop) aktif olmalıdır; sistem çökmesi durumunda pozisyonlar korunmalıdır.
- **NFR9 (Order Timeout):** Bekleyen (unfilled) alım emirleri 10 dakika, satış emirleri 30 dakika içinde otomatik olarak iptal edilir (zombie order prevention).
- **NFR10 (Backtest Thresholds):** LLM stratejileri canlıya alınmadan önce backtest sonuçları şu eşikleri sağlamalıdır: Sharpe ≥ 0.5, Max Drawdown ≤ %25, Win Rate ≥ %35.
- **NFR11 (System Heartbeat):** Sistem 60 saniyede bir heartbeat (sağlık) sinyali üretir; 120 saniye kesinti durumunda Telegram/E-posta üzerinden acil durum uyarısı gönderilir.
- **NFR12 (Order Rate Limits):** Sistem IG Markets API'sine dakikada maksimum 10 emir (order) gönderecek şekilde rate-limit uygular ve aynı sinyal için mükerrer (duplicate) emir açılmasını engeller.