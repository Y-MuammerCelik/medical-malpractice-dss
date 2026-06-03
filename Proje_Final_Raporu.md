# BİTİRME PROJESİ FİNAL RAPORU

**Proje Adı:** Tıbbi Hasar Analizi ve Malpraktis Tespiti İçin Kural Tabanlı Karar Destek Sistemi (MalpraktisDSS)
**Öğrenci Adı Soyadı:** Muammer ÇELİK
**Öğrenci Numarası:** 22430070028
**Bölüm:** Bilişim Sistemleri ve Teknolojileri

---

## 1. Özet
Bu proje kapsamında, hastanelerde uygulanan tıbbi tedavilerin Uluslararası Hastalık Sınıflandırması (ICD-10) standartlarına ve tıbbi protokollere uygunluğunu otonom olarak denetleyen, yapay zeka destekli bir Karar Destek Sistemi (DSS) geliştirilmiştir. Sistem; hekimlerin yazdığı serbest metin formatındaki klinik raporları Doğal Dil İşleme (NLP) yöntemleriyle analiz edip anlamlandırarak, olası malpraktis (tıbbi hata veya ihmal) durumlarını tespit etmekte ve risk derecelendirmesi yapmaktadır.

## 2. Projenin Amacı ve Motivasyonu
Tıbbi hatalar, dünya genelinde hasta güvenliğini tehdit eden en önemli faktörlerden biridir. Yanlış ilaç kullanımı, eksik prosedürler veya gereksiz uzun yatış süreleri hem hasta sağlığını tehlikeye atmakta hem de hastanelere ciddi hukuki/maddi külfetler getirmektedir. 
Bu projenin temel amacı; insan gözünden kaçabilecek tıbbi kural ihlallerini, standart tedavi protokolleri (ICD-10) ile karşılaştırmalı olarak analiz eden algoritmik bir denetim mekanizması (Kural Motoru) oluşturmaktır.

## 3. Sistem Mimarisi ve Kullanılan Teknolojiler
Proje, yüksek performanslı ve ölçeklenebilir bir mimari ile geliştirilmiştir:
- **Backend:** Python, Django 4.2 ve Django REST Framework (DRF) kullanılarak 20'den fazla RESTful API ucu geliştirilmiştir.
- **Veritabanı:** Geliştirme ortamında SQLite kullanılmış olup, yapısal olarak PostgreSQL entegrasyonuna tam uyumlu tasarlanmıştır.
- **Yapay Zeka & NLP:** `spaCy` kütüphanesi ve Regex algoritmaları kullanılarak, yapılandırılmamış klinik metinlerden (epikriz) varlık çıkarımı (Entity Extraction) yapan hibrid bir NLP servisi yazılmıştır.
- **Frontend (Arayüz):** Modern, duyarlı (responsive) ve dinamik bir kullanıcı deneyimi sunmak amacıyla Vanilla HTML/CSS/JS ile harici bağımlılık olmadan (dependency-free) geliştirilmiştir.

## 4. Geliştirilen Temel Modüller ve Kritik Noktalar

### 4.1. Doğal Dil İşleme (NLP) Belge Analiz Modülü
Hekimlerin sisteme yapıştırdığı düz metin (epikriz) raporları sistem tarafından saniyeler içinde analiz edilir. Modülün yapabildikleri:
- **Hastalık Tespiti:** Metin içindeki teşhisleri ICD-10 kodlarına çevirir (Örn: "Zatürre" -> J18.9 Pnömoni).
- **Varlık Çıkarımı:** Metindeki ilaçları (Etken madde bazlı) ve tıbbi prosedürleri (Örn: EKG, Anjiyografi) tespit eder.
- **Süre ve Kimlik Çıkarımı:** Hastanın yatış süresini, yaşını ve kimlik bilgilerini hesaplayarak sisteme yapılandırılmış veri (JSON) olarak sunar.
- **Güven Skoru:** Yapılan analizin doğruluğunu hesaplayarak kullanıcıya bir "Güven Yüzdesi" sunar.

### 4.2. Algoritmik Kural Motoru (Rule Engine)
Sistemin beyni olan bu modül, elde edilen hasta verilerini veritabanındaki standart ICD-10 protokolleriyle çarpıştırır. *Kritik Kontrol Noktaları:*
- **Süre Sapması:** Belirlenen protokolden %20 daha uzun veya kısa yatışlar tespit edilir.
- **Eksik veya Yanlış İlaç:** Hastaya verilmesi gereken hayati bir ilaç verilmemişse veya protokole aykırı bir ilaç verilmişse sistem log oluşturur.
- **Risk Derecelendirmesi:** Hataların ağırlığına göre yatış dosyasını `Risk Yok`, `Düşük`, `Orta`, `Yüksek` veya `Malpraktis (Kritik)` olarak derecelendirir.

### 4.3. Karar Destek Gösterge Paneli (Dashboard)
Yöneticiler ve denetçiler için tasarlanan canlı yönetim panelidir. Panel üzerinde:
- Hastanenin genel risk dağılımı (Donut grafik ile),
- Riskli hastaların uyum skorları (Yüzdelik bar grafikleri),
- Tespit edilen kural sapmalarının (Deviation Logs) detaylı dökümü tek ekranda izlenebilmektedir.

## 5. Sonuç ve Kazanımlar
Bu proje ile karmaşık tıbbi dokümanların bilgisayar tarafından anlaşılabilir yapısal verilere dönüştürülmesi ve kural tabanlı bir motor ile tıbbi hataların otonom tespiti başarıyla sağlanmıştır. Test edilen 6 farklı senaryoda (uyumlu, eksik ilaçlı, süresi uzatılmış vb.) sistem %100 doğrulukla beklenen risk skorlarını ve uyarı loglarını üretmiştir. Proje, sağlık sektöründe denetim süreçlerini hızlandıracak ve hasta güvenliğini artıracak dijital bir asistan niteliği taşımaktadır.
