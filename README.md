# HVAC Test System Skeleton

Bu proje, Django + PostgreSQL + Redis + Celery + Docker tabanli HVAC test otomasyonu icin moduler bir baslangic iskeleti sunar.

## Moduller

- `core`: ortak enum, yardimci model, ayarlar ekrani, cleanup task
- `companies`: firma yonetimi
- `products`: urun/model yonetimi
- `recipes`: faz sureleri ve limit yapisi
- `plc`: Modbus istemcisi, parser, poller, time sync, PLC event log
- `tests`: test kaydi, sample, evaluation, state machine, orchestration
- `reports`: PDF ve Excel rapor uretimi
- `dashboard`: operasyon ana ekrani

## One Cikan Mimari Kararlar

- Monitoring ve test execution birbirinden ayridir.
- Idle durumdaki canli veri DB sample tablosuna yazilmaz; yalnizca aktif test varsa `TestSample` olusur.
- Evaluation varsayilan olarak ilgili fazdaki gecerli sample ortalamalari uzerinden yapilir.
- Tag validity bilgisi sample bazli kullanilir; genel tekil `DataValid` alani yoktur.
- Recipe canli referans olarak degil, snapshot olarak test kaydina kopyalanir.
- PLC tarafina sadece ust seviye komutlar yazilir.
- Raporlar PDF ve Excel olarak host makinede saklanir.

## Hizli Baslangic

1. `.env.example` dosyasini `.env` olarak kopyalayin.
2. Gerekirse `.env` icindeki ayarlari guncelleyin.
3. `docker compose up --build -d` komutunu calistirin.
4. `docker compose exec web python manage.py migrate` ile migration uygulayin.
5. `docker compose exec web python manage.py seed_demo_data` ile demo veri yukleyin.
6. Uygulamayi `http://localhost:8000` adresinden acin.

## Yeni Bilgisayarda Kurulum

Projeyi baska bir bilgisayarda calistirmak icin asagidaki adimlari izleyin:

1. Repo'yu klonlayin:
   `git clone https://github.com/KULLANICI_ADINIZ/MacSogutma.git`
2. Proje klasorune girin:
   `cd MacSogutma`
3. Ortam dosyasini olusturun:
   `copy .env.example .env`
4. Gerekirse `.env` icindeki ayarlari guncelleyin.
   Ozellikle:
   `HOST_MEDIA_PATH`, `PLC_HOST`, `PLC_PORT`, `MODBUS_UNIT_ID`, `DJANGO_ALLOWED_HOSTS`
5. Servisleri ayaga kaldirin:
   `docker compose up --build -d`
6. Veritabani migration'larini uygulayin:
   `docker compose exec web python manage.py migrate`
7. Demo veri yuklemek isterseniz:
   `docker compose exec web python manage.py seed_demo_data`
8. Uygulamayi tarayicidan acin:
   `http://localhost:8000`

## Ortam Degiskenleri

Temel olarak su alanlarin kontrol edilmesi gerekir:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `PLC_HOST`
- `PLC_PORT`
- `MODBUS_UNIT_ID`
- `MODBUS_TIMEOUT_SEC`
- `PLC_SIMULATION_ENABLED`
- `FAST_POLL_MS`
- `HISTORY_SYNC_ENABLED`
- `MAX_HISTORY_RECORDS_PER_CYCLE`
- `HISTORY_SYNC_BATCH_SIZE`
- `TIME_SYNC_ENABLED`
- `TIME_SYNC_INTERVAL_SEC`
- `TIME_SYNC_DRIFT_THRESHOLD_SEC`
- `REPORT_ROOT_PATH`
- `HOST_MEDIA_PATH`
- `STATIC_ROOT`
- `MEDIA_ROOT`
- `LOG_LEVEL`

## Gelistirme Notlari

- Gercek `pymodbus` entegrasyonu icin `apps/plc/services/modbus_client.py` icindeki simulation katmani gercek register okuma/yazma ile degistirilmelidir.
- Production icin migration dosyalari sabit ve tutarli sekilde repo icinde tutulmalidir.
- Docker ile rapor ciktilari host makinede `HOST_MEDIA_PATH` altina yazilir.
- Yeni bilgisayarda kurulum yaparken `.env.example` dosyasini baz almaniz yeterlidir.
