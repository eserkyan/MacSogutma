# S7-1200 Modbus Server Paketi

Bu klasor, mevcut Django HVAC test uygulamasinin baglanabilecegi bir `S7-1200 Modbus TCP Server` tasarimini aciklar.

Amac:

- Python uygulamasi mevcut Modbus istemcisiyle PLC'ye baglanir.
- PLC `holding register` alanlarinda canli veri, status ve history buffer sunar.
- PLC sahadan gelen analog ve dijital verilerle beslenebilir.
- PLC test fazlarini saha tarafina duyurur, fakat test akisini Python yonetir.

## Temel Mimari

Python -> PLC komut register'lari:

- `CircuitSelect`
- `StartRequest`
- `StopRequest`
- `AbortRequest`
- `TestPhase`
- `TestActive`
- `TimeSyncRequest`
- `TimeSyncUnixHigh`
- `TimeSyncUnixLow`

## Komut Handshake Mantigi

Asagidaki komutlar `pulse` mantigiyla calisir:

- `StartRequest`
- `StopRequest`
- `AbortRequest`
- `TimeSyncRequest`

Onerilen davranis:

- Python bu bitleri `2 saniye boyunca 1` yapar, sonra tekrar `0` yapar.
- PLC bu sinyalleri `seviye` olarak degil, sadece `pozitif edge` olarak isler.
- Boylece bit 2 saniye boyunca `1` kalsa bile komut yalnizca bir kez uygulanir.

Ornek:

1. Python `StartRequest = 1` yazar.
2. PLC `FALSE -> TRUE` gecisini gorur ve `start command accepted` olayi olusturur.
3. Python 2 saniye sonunda `StartRequest = 0` yazar.
4. PLC yeni bir `TRUE` gecisi gorene kadar ikinci kez start islemez.

Seviye bilgisi olarak kalacak alanlar:

- `CircuitSelect`
- `TestPhase`
- `TestActive`
- `TimeSyncUnix`

PLC -> Python status ve veri alanlari:

- `PlcReady`
- `PlcFault`
- `Buf_WriteIndex`
- `Buf_RecordCount`
- `Buf_BufferSize`
- `Buf_LastSequenceNo`
- `TimeSyncDone`
- `PlcCurrentUnix`
- `LiveRecord`
- `HistoryBuffer`

## Dosya Yapisi

- [register-map.md](/d:/Python/MacSogutma/docs/s7-1200-modbus-server/register-map.md)
  Mevcut Python projesiyle uyumlu register haritasi
- [siemens/s7_1200_modbus_server/README.md](/d:/Python/MacSogutma/siemens/s7_1200_modbus_server/README.md)
  TIA Portal tarafinda nasil kullanilacagi
- `siemens/s7_1200_modbus_server/types/*.scl`
  UDT tipi yapilar
- `siemens/s7_1200_modbus_server/blocks/*.scl`
  FB/FC/OB iskeleti

## Modbus TCP Server Zinciri

PLC tarafinda veri akisinin onerilen sirasi:

1. `FB_HVAC_SignalSource`
   IO veya simulasyon verisini uretir
2. `FB_HVAC_ModbusServer`
   status/live/history kayitlarini doldurur
3. `FB_HVAC_ModbusRegisterMap`
   bu yapilari Modbus holding register dizisine map eder
4. `FB_HVAC_MB_ServerTcp` veya `FB_HVAC_MB_ServerTcp_Legacy`
   holding register dizisini Modbus TCP server olarak yayinlar

Bu yapiyla Python istemcisi dogrudan PLC'nin holding register alanini okur/yazar.

## Onerilen TIA Yapisi

1. Global DB:
   - `DB_HVAC_Command`
   - `DB_HVAC_Status`
   - `DB_HVAC_Live`
   - `DB_HVAC_History`
   - `DB_HVAC_IO`
2. FB:
   - `FB_HVAC_ModbusServer`
   - `FB_HVAC_RingBuffer`
   - `FB_HVAC_SignalSource`
3. OB:
   - `OB1` icinde periyodik cagrilar

## Besleme Senaryolari

Analog besleme ornekleri:

- Basinc transmitter 4-20 mA
- Sicaklik transmitter PT100 / transmitter cikisi
- Nem sensoru
- Akim trafosu / enerji analizoru degerleri

Dijital besleme ornekleri:

- Kompresor 1 run feedback
- Kompresor 2 run feedback
- Alarm dry contact
- Genel enable / ready bilgisi

## Onemli Not

Bu tasarim mevcut Python uygulamasinin su anki register bekleyisine gore hazirlandi. Python tarafinda register offset veya tag tanimi degisirse bu SCL tarafinin da ayni sekilde guncellenmesi gerekir.
