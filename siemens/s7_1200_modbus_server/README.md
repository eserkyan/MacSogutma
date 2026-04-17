# Siemens S7-1200 Modbus Server Ornek Projesi

Bu klasordeki SCL dosyalari, TIA Portal tarafinda elle yeni blok olarak olusturulup icerigi yapistirilacak sekilde hazirlanmistir.

## Onerilen Bloklar

- `types/udt_hvac_command.scl`
- `types/udt_hvac_status.scl`
- `types/udt_hvac_record.scl`
- `types/udt_hvac_io.scl`
- `types/udt_hvac_holding_registers.scl`
- `types/udt_hvac_runtime.scl`
- `types/udt_hvac_modbus_runtime.scl`
- `db/*.scl`
- `blocks/fb_hvac_ring_buffer.scl`
- `blocks/fb_hvac_runtime.scl`
- `blocks/fb_hvac_signal_source.scl`
- `blocks/fb_hvac_modbus_server.scl`
- `blocks/fb_hvac_modbus_register_map.scl`
- `blocks/fb_hvac_mb_server_tcp.scl`
- `blocks/fc_mb_server_side.scl`
- `blocks/fc_hvac_command_edge_example.scl`
- `blocks/fc_hvac_digital_examples.scl`
- `blocks/fc_hvac_analog_examples.scl`

## Kullanim Mantigi

1. Saha IO degerlerini `DB_HVAC_IO` icinde engineering unit olarak toplayin.
2. `FB_HVAC_Runtime` ile timer tabanli `Tick500ms`, `Tick1s` ve `UnixNow` degerlerini uretin.
3. `FB_HVAC_SignalSource` ile isterseniz simulasyon veya gercek IO secimi yapin.
4. `FB_HVAC_ModbusServer` status, live record ve history buffer alanlarini doldursun.
5. `FB_HVAC_ModbusRegisterMap` command, status, live ve history yapilarini tek holding register alanina map etsin.
6. `FB_HVAC_MB_ServerTcp` ayni holding register alanini Modbus TCP server olarak yayinlasin.
7. `FC_MB_Server_Side` bu zinciri tek noktadan cagiracak orchestration FC olarak kullanilsin.
8. `FC_HVAC_CommandEdgeExample`, `FC_HVAC_DigitalExamples` ve `FC_HVAC_AnalogExamples` dosyalari yardimci referans bloklar olarak korunur.

## Fiziksel IO Esleme

Bu paket, verdigin son saha tablosuna gore asagidaki fiziksel adreslerle hizalandi.

TIA icinde hata almamak icin son referans surumde fiziksel adresler dogrudan degil, sembolik PLC tag isimleri uzerinden kullanilir. Repo icindeki `FC_MB_Server_Side` dosyasi buna gore duzenlenmistir.

### Dijital girisler

- `%I0.0` -> `Comp1_Rng`
- `%I0.1` -> `Comp2_Rng`
- `%I0.2` -> `Alarm`
- `%I0.3` -> `Ready`
- `%I0.4..%I1.5` -> yedek

Sembolik tag onerisi:

- `I0_0_Comp1_Rng`
- `I0_1_Comp2_Rng`
- `Plc_Alarm`
- `Plc_Ready`

### Dijital cikisler

- `%Q0.0` -> `Circuit1_Run`
- `%Q0.1` -> `Circuit2_Run`
- `%Q0.2..%Q1.1` -> yedek

Sembolik tag onerisi:

- `Q0_0_Circuit1_Run`
- `Q0_1_Circuit2_Run`

`Q0.0` ve `Q0.1`, PLC icinde su mantikla surulur:

- `TestActive = 1` ve `CircuitSelect = 1` ise `Q0.0 = 1`
- `TestActive = 1` ve `CircuitSelect = 2` ise `Q0.1 = 1`
- `TestActive = 1` ve `CircuitSelect = 3` ise ikisi birlikte `1`
- test aktif degilse ikisi de `0`

### Analog girisler

- `%IW54` -> `Circuit1_HP`
- `%IW56` -> `Circuit1_LP`
- `%IW58` -> `Circuit2_HP`
- `%IW60` -> `Circuit2_LP`
- `%IW62` -> `Air_Flow_Sensor`
- `%IW64` -> `Inlet_Air_Humidity_Sensor`
- `%IW66` -> `Outlet_Air_Humidity_Sensor`
- `%IW70` -> `C1_DischargeLine_Temp`
- `%IW72` -> `C2_DischargeLine_Temp`
- `%IW74` -> `C1_SuctionLine_Temp`
- `%IW76` -> `C2_SuctionLine_Temp`
- `%IW78` -> `Condenser_Water_Inlet_Temp`
- `%IW80` -> `Condenser_Water_Outlet_Temp`
- `%IW82` -> `Air_Inlet_Temp`
- `%IW84` -> `Air_Outlet_Temp`

Sembolik tag onerisi:

- `IW54_C1_HP`
- `IW56_C1_LP`
- `IW58_C2_HP`
- `IW60_C2_LP`
- `IW62_Air_Flow_Sensor`
- `IW64_Inlet_Air_Humidty_Sensor`
- `IW66_Outlet_Air_Humidty_Sensor`
- `IW70_C1_DischargeLine_Temp`
- `IW72_C2_DischargeLine_Temp`
- `IW74_C1_SuctionLine_Temp`
- `IW76_C2_SuctionLine_Temp`
- `IW78_Condencer_Water_Inlet_Temp`
- `IW80_Condencer_Water_Outlet_Temp`
- `IW82_Air_Inlet_Temp`
- `IW84_Air_Outlet_Temp`

## Python ile mevcut veri modeli eslestirmesi

Python tarafindaki mevcut canli kayit modeli korunmustur:

- `Temp1` -> `C1_DischargeLine_Temp`
- `Temp2` -> `C2_DischargeLine_Temp`
- `Temp3` -> `C1_SuctionLine_Temp`
- `Temp4` -> `C2_SuctionLine_Temp`
- `Humidity` -> `Inlet_Air_Humidity_Sensor`
- `AirVelocity` -> `Air_Flow_Sensor`

Ek saha sensorleri PLC icinde ayri alanlarda tutulur:

- `Outlet_Air_Humidity`
- `Condenser_Water_Inlet_Temp`
- `Condenser_Water_Outlet_Temp`
- `Air_Inlet_Temp`
- `Air_Outlet_Temp`

Bu ek alanlar mevcut Python parser yapisini bozmadan, PLC tarafinda ve Modbus diagnostic register alaninda da yayinlanir.

Elektriksel parametreler mevcut yapidaki gibi korunur:

- Devre 1 elektriksel parametreleri ayri
- Devre 2 elektriksel parametreleri ayri

## Compact Bellek Surumu

Bu klasor compact PLC bellek kullanimina gore duzenlenmistir.

Adres ozetleri:

- Status block: `0..11`
- Live record: `100..133`
- Extended physical IO diagnostics: `140..147`
- History block base: `300`
- Command block: `1000..1012`

Extended diagnostics:

- `140` -> `InletAirHumidity_RH_x10`
- `141` -> `OutletAirHumidity_RH_x10`
- `142` -> `CondenserWaterInletTemp_C_x10`
- `143` -> `CondenserWaterOutletTemp_C_x10`
- `144` -> `AirInletTemp_C_x10`
- `145` -> `AirOutletTemp_C_x10`
- `146` -> dijital giris bit paketi
- `147` -> dijital cikis bit paketi

Bit paketi:

- Register `146` bit0 `Comp1_Rng`
- Register `146` bit1 `Comp2_Rng`
- Register `146` bit2 `Alarm`
- Register `146` bit3 `Ready`
- Register `147` bit0 `Circuit1_RunCommand`
- Register `147` bit1 `Circuit2_RunCommand`

Validity bit plani:

- `ValidityWord1 bit0` -> `Circuit1_HP_Valid`
- `ValidityWord1 bit1` -> `Circuit1_LP_Valid`
- `ValidityWord1 bit2` -> `Circuit2_HP_Valid`
- `ValidityWord1 bit3` -> `Circuit2_LP_Valid`
- `ValidityWord1 bit4` -> `Temp1_Valid`
- `ValidityWord1 bit5` -> `Temp2_Valid`
- `ValidityWord1 bit6` -> `Temp3_Valid`
- `ValidityWord1 bit7` -> `Temp4_Valid`
- `ValidityWord1 bit8` -> `Humidity_Valid`
- `ValidityWord1 bit9` -> `AirVelocity_Valid`
- `ValidityWord1 bit10` -> `Comp1_Current_Valid`
- `ValidityWord1 bit11` -> `Comp1_Power_Valid`
- `ValidityWord1 bit12` -> `Comp2_Current_Valid`
- `ValidityWord1 bit13` -> `Comp2_Power_Valid`

- `ValidityWord2 bit0` -> `InletAirHumidity_Valid`
- `ValidityWord2 bit1` -> `OutletAirHumidity_Valid`
- `ValidityWord2 bit2` -> `CondenserWaterInletTemp_Valid`
- `ValidityWord2 bit3` -> `CondenserWaterOutletTemp_Valid`
- `ValidityWord2 bit4` -> `AirInletTemp_Valid`
- `ValidityWord2 bit5` -> `AirOutletTemp_Valid`
- `ValidityWord2 bit6` -> `Comp1_Voltage_Valid`
- `ValidityWord2 bit7` -> `Comp1_Frequency_Valid`
- `ValidityWord2 bit8` -> `Comp1_Energy_Valid`
- `ValidityWord2 bit9` -> `Comp2_Voltage_Valid`
- `ValidityWord2 bit10` -> `Comp2_Frequency_Valid`
- `ValidityWord2 bit11` -> `Comp2_Energy_Valid`

Gercek sensorde validity kurali:

- Analog sensorler icin raw deger `1..30000` araligindaysa valid kabul edilir
- Simulasyonda validity alanlari `TRUE` uretir
- Elektriksel alanlar icin gercek olcum bagliysa `deger > 0` oldugunda valid kabul edilir

Bellek ayarlari:

- History kapasitesi: `100` kayit
- History record size: `34 word`
- History son adresi: `3699`
- Holding register boyutu: `Array[0..4095] of Word`
- `Buf_BufferSize`: `100`

## Source Olarak Olusturulan DB'ler

Bu paket icinde gerekli temel DB source dosyalari da verildi:

- `DB_HVAC_Command`
- `DB_HVAC_Status`
- `DB_HVAC_Live`
- `DB_HVAC_History`
- `DB_HVAC_IO`
- `DB_HVAC_Runtime`
- `DB_HVAC_Modbus`
- `MB_SERVER_DB2`
- `FB_HVAC_Runtime_DB`

Notlar:

- Bu DB'lerde ana veri alanlari `Data` altinda tutulur.
- `DB_HVAC_History` dogrudan `Buffer` alanini tasir.
- `DB_HVAC_Modbus.Data.Holding` Modbus holding register alani olarak kullanilir.
- `MB_SERVER_DB2` S7-1200 `MB_SERVER` instruction instance DB kaynagidir.
- `FB_HVAC_Runtime_DB` runtime FB instance DB kaynagidir.
- Buyuk DB ve history alanlari `NON_RETAIN` tutulmalidir.

## Komut Isleme Kurali

`StartRequest`, `StopRequest`, `AbortRequest` ve `TimeSyncRequest` alanlari PLC tarafinda sadece `pozitif edge` olarak islenmelidir.

Beklenen protokol:

- Python komut bitini yaklasik `2 saniye` boyunca `1` yapar.
- PLC ilgili biti onceki durum ile karsilastirarak bir kez yakalar.
- Komut biti uzun sure `1` kalsa bile ikinci kez isleme sebep olmaz.

## Modbus TCP Server Notlari

Bu proje, S7-1200 `MB_SERVER` yardimina gore su imzayi kullanir:

- `DISCONNECT`
- `CONNECT_ID`
- `IP_PORT`
- `MB_HOLD_REG`
- `NDR`
- `DR`
- `ERROR`
- `STATUS`

Notlar:

- `MB_SERVER` pasif TCP baglanti olarak kullanilir.
- Port olarak tipik Modbus TCP portu `502` kullanilir.
- `MB_HOLD_REG` parametresi holding register bellek alanina pointer verir.
- Holding register icin global DB ve standard access kullanilmalidir.

## Onemli

- `OB1` icinde dogrudan `MB_SERVER(...)` cagirmak yerine `FC_MB_Server_Side` veya zincirdeki wrapper bloklarini cagirin.
- `Tick500ms` ve `UnixNow` icin scan suresinden bagimsiz, timer tabanli `FB_HVAC_Runtime` blogu kullanilir.
- Python tarafi compact yapidaki `100` kayitlik buffer mantigina gore ayarlanmistir.
