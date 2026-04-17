# HVAC Test System Skeleton

Bu proje, Django + PostgreSQL + Redis + Celery + Docker tabanlı HVAC test otomasyonu için modüler bir başlangıç iskeleti sunar.

## Modüller

- `core`: ortak enum, yardımcı model, settings ekranı, cleanup task
- `companies`: firma yönetimi
- `products`: ürün/model yönetimi
- `recipes`: faz süreleri ve limit JSON yapısı
- `plc`: Modbus istemcisi, parser, poller, time sync, PLC event log
- `tests`: test kaydı, sample, evaluation, state machine, orchestration
- `reports`: WeasyPrint ile PDF üretimi ve chart verisi
- `dashboard`: operasyon ana ekranı

## Öne Çıkan Mimari Kararlar

- Monitoring ve test execution ayrıdır. PLC runtime durumu `PlcRuntimeState` içinde tutulur.
- Idle canlı veri DB sample tablosuna yazılmaz; yalnızca aktif test varsa `TestSample` oluşur.
- Evaluation yalnızca `Stable` fazındaki geçerli sample ortalamaları üzerinden yapılır.
- Tag validity bilgisi `validity_word1` bitleri ile sample bazında kullanılır; genel `DataValid` alanı yoktur.
- Recipe canlı referans olarak değil snapshot olarak test kaydına kopyalanır.
- PLC tarafına sadece üst seviye komutlar yazılır.

## Hızlı Başlangıç

1. `.env.example` dosyasını `.env` olarak çoğaltın.
2. `docker compose up --build` çalıştırın.
3. `python manage.py seed_demo_data` ile demo veri yükleyin.

## Geliştirme Notları

- Gerçek `pymodbus` entegrasyonu için `apps/plc/services/modbus_client.py` içindeki simulation katmanı gerçek register okuma/yazma ile değiştirilmelidir.
- Production için migration dosyaları oluşturup sabitlemeniz önerilir.
- PDF içinde grafikler veri özeti olarak temsil ediliyor; istenirse server-side chart image üretimi eklenebilir.
