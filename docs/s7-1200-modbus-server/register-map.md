# S7-1200 Register Haritasi

Bu harita su an Python uygulamasindaki kaynak tanima gore hazirlanmistir:

- status blok baslangici: `0`
- live record baslangici: `100`
- history base: `300`
- command register baslangici: `1000`

## 1. Status Block

Holding register araligi: `0..11`

| Register | Alan | Tip | Aciklama |
|---|---|---|---|
| 0 | PlcReady | UINT | PLC test servisi hazir |
| 1 | Reserved | UINT | Ileride circuit run feedback icin ayrildi |
| 2 | PlcFault | UINT | Genel fault |
| 3 | Reserved | UINT | Ileride alarm detaylari icin ayrildi |
| 4 | Buf_WriteIndex | UINT | Ring buffer yazma indexi |
| 5 | Buf_RecordCount | UINT | Mevcut kayit sayisi |
| 6 | Buf_BufferSize | UINT | Buffer kapasitesi |
| 7 | Buf_LastSequenceNo_H | UINT | Sequence high word |
| 8 | Buf_LastSequenceNo_L | UINT | Sequence low word |
| 9 | TimeSyncDone | UINT | Son time sync tamamlandi |
| 10 | PlcCurrentUnix_H | UINT | Unix time high word |
| 11 | PlcCurrentUnix_L | UINT | Unix time low word |

## 2. Live Record Block

Holding register araligi: `100..133`

Kayit yapisi 34 word:

| Offset | Register | Alan |
|---|---|---|
| 0 | 100 | SequenceNo high |
| 1 | 101 | SequenceNo low |
| 2 | 102 | TimestampUnix high |
| 3 | 103 | TimestampUnix low |
| 4 | 104 | TestPhase |
| 5 | 105 | StatusWord |
| 6 | 106 | ValidityWord1 |
| 7 | 107 | ValidityWord2 |
| 8 | 108 | Circuit 1 HP bar x10 |
| 9 | 109 | Circuit 1 LP bar x10 |
| 10 | 110 | Circuit 2 HP bar x10 |
| 11 | 111 | Circuit 2 LP bar x10 |
| 12 | 112 | Temp 1 C x10 |
| 13 | 113 | Temp 2 C x10 |
| 14 | 114 | Temp 3 C x10 |
| 15 | 115 | Temp 4 C x10 |
| 16 | 116 | Humidity RH x10 |
| 17 | 117 | AirVelocity m/s x10 |
| 18 | 118 | Comp1 Voltage V x10 |
| 19 | 119 | Comp1 Current A x100 |
| 20 | 120 | Comp1 ActivePower kW x10 |
| 21 | 121 | Comp1 ReactivePower kVAr x10 |
| 22 | 122 | Comp1 ApparentPower kVA x10 |
| 23 | 123 | Comp1 PowerFactor x1000 |
| 24 | 124 | Comp1 Frequency Hz x10 |
| 25 | 125 | Comp1 Energy kWh x10 |
| 26 | 126 | Comp2 Voltage V x10 |
| 27 | 127 | Comp2 Current A x100 |
| 28 | 128 | Comp2 ActivePower kW x10 |
| 29 | 129 | Comp2 ReactivePower kVAr x10 |
| 30 | 130 | Comp2 ApparentPower kVA x10 |
| 31 | 131 | Comp2 PowerFactor x1000 |
| 32 | 132 | Comp2 Frequency Hz x10 |
| 33 | 133 | Comp2 Energy kWh x10 |

## 3. History Buffer

- Base address: `300`
- Record size: `34 word`
- Capacity: `300 record`

Bir kayit adresi:

`record_address = 300 + (slot_index * 34)`

Ornek:

- Slot 0 -> `300..333`
- Slot 1 -> `334..367`
- Slot 2 -> `368..401`

## 4. Command Registers

Holding register araligi: `1000..1012`

| Register | Alan | Tip | Aciklama |
|---|---|---|---|
| 1000 | CircuitSelect | UINT | 0 none, 1 circuit1, 2 circuit2, 3 both |
| 1001 | StartRequest | UINT | Python tarafindan 2 sn pulse, PLC rising edge ile isler |
| 1002 | StopRequest | UINT | Python tarafindan 2 sn pulse, PLC rising edge ile isler |
| 1003 | AbortRequest | UINT | Python tarafindan 2 sn pulse, PLC rising edge ile isler |
| 1004 | TestPhase | UINT | 0 idle, 1 start, 2 stable, 3 stop, 4 manual, 5 aborted |
| 1005 | TestActive | UINT | Test aktif bilgisi |
| 1006 | Reserved | UINT | Bos |
| 1007 | Reserved | UINT | Bos |
| 1008 | Reserved | UINT | Bos |
| 1009 | Reserved | UINT | Bos |
| 1010 | TimeSyncRequest | UINT | Python tarafindan pulse, PLC rising edge ile saat gunceller |
| 1011 | TimeSyncUnixHigh | UINT | Unix high word |
| 1012 | TimeSyncUnixLow | UINT | Unix low word |

## 4.1 Komut Isleme Kurali

PLC su alanlari sadece `positive edge` ile islemelidir:

- `StartRequest`
- `StopRequest`
- `AbortRequest`
- `TimeSyncRequest`

Yani PLC tarafinda su mantik kullanilir:

- `FALSE -> TRUE` gecisi varsa komut bir kez kabul edilir
- bit uzun sure `TRUE` kalsa bile komut tekrar edilmez
- Python komut bitini yaklasik `2 saniye` sonra tekrar `FALSE` yapar

## 5. StatusWord Bitleri

| Bit | Alan |
|---|---|
| 0 | TestActive |
| 1 | AlarmActive |
| 2 | Comp1_Rng |
| 3 | Comp2_Rng |

## 6. ValidityWord1 Bitleri

| Bit | Alan |
|---|---|
| 0 | Circuit1_HP_Valid |
| 1 | Circuit1_LP_Valid |
| 2 | Circuit2_HP_Valid |
| 3 | Circuit2_LP_Valid |
| 4 | Temp1_Valid |
| 5 | Temp2_Valid |
| 6 | Temp3_Valid |
| 7 | Temp4_Valid |
| 8 | Humidity_Valid |
| 9 | AirVelocity_Valid |
| 10 | Comp1_Current_Valid |
| 11 | Comp1_Power_Valid |
| 12 | Comp2_Current_Valid |
| 13 | Comp2_Power_Valid |

## 7. Onerilen Veri Tipi Donusumu

PLC icinde engineering unit -> Modbus raw:

- `bar` -> `bar * 10`
- `C` -> `C * 10`
- `RH` -> `RH * 10`
- `m/s` -> `m/s * 10`
- `V` -> `V * 10`
- `A` -> `A * 100`
- `kW` -> `kW * 10`
- `kVAr` -> `kVAr * 10`
- `kVA` -> `kVA * 10`
- `PF` -> `PF * 1000`
- `Hz` -> `Hz * 10`
- `kWh` -> `kWh * 10`
