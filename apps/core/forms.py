from __future__ import annotations

from django import forms

from apps.core.forms_translation import apply_bootstrap_form_style
from apps.core.models import PlcSchemaConfig, TagConfig
from apps.core.tag_schema import CHART_GROUP_DEFINITIONS


def modbus_reference_text(register_type: str, address: int | None) -> str:
    safe_address = int(address or 0)
    prefix = "4" if register_type == TagConfig.RegisterType.HOLDING else "3"
    register_label = "Holding Register" if register_type == TagConfig.RegisterType.HOLDING else "Input Register"
    return f"{register_label} referansi: {prefix}{safe_address:05d}"


class PlcSchemaConfigForm(forms.ModelForm):
    SECTION_FIELDS: dict[str, list[str]] = {
        "connection_block": ["plc_host", "plc_port", "modbus_unit_id"],
        "status_block": ["status_address", "status_count"],
        "live_block": ["live_record_address", "live_record_count"],
        "history_block": ["history_base_address", "history_record_words", "history_capacity"],
        "command_block": [
            "cmd_circuit_select",
            "cmd_start_request",
            "cmd_stop_request",
            "cmd_abort_request",
            "cmd_test_phase",
            "cmd_test_active",
        ],
        "time_sync_block": [
            "cmd_time_sync_request",
            "cmd_time_sync_unix_high",
            "cmd_time_sync_unix_low",
        ],
    }

    class Meta:
        model = PlcSchemaConfig
        fields = [
            "plc_host",
            "plc_port",
            "modbus_unit_id",
            "status_address",
            "status_count",
            "live_record_address",
            "live_record_count",
            "history_base_address",
            "history_record_words",
            "history_capacity",
            "cmd_circuit_select",
            "cmd_start_request",
            "cmd_stop_request",
            "cmd_abort_request",
            "cmd_test_phase",
            "cmd_test_active",
            "cmd_time_sync_request",
            "cmd_time_sync_unix_high",
            "cmd_time_sync_unix_low",
        ]

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        apply_bootstrap_form_style(self)
        labels = {
            "plc_host": "PLC IP / Host",
            "plc_port": "PLC Port",
            "modbus_unit_id": "Modbus Unit ID",
            "status_address": "Durum Blogu Baslangic Adresi",
            "status_count": "Durum Blogu Register Sayisi",
            "live_record_address": "Canli Kayit Baslangic Adresi",
            "live_record_count": "Canli Kayit Register Sayisi",
            "history_base_address": "History Baslangic Adresi",
            "history_record_words": "History Kayit Basina Word",
            "history_capacity": "History Kayit Kapasitesi",
            "cmd_circuit_select": "Circuit Select Register",
            "cmd_start_request": "Start Request Register",
            "cmd_stop_request": "Stop Request Register",
            "cmd_abort_request": "Abort Request Register",
            "cmd_test_phase": "Test Phase Register",
            "cmd_test_active": "Test Active Register",
            "cmd_time_sync_request": "Time Sync Request Register",
            "cmd_time_sync_unix_high": "Time Sync Unix High",
            "cmd_time_sync_unix_low": "Time Sync Unix Low",
        }
        help_texts = {
            "plc_host": "PLC cihazinin IP adresi veya DNS host bilgisi. Ornek: 192.168.0.50",
            "plc_port": "Modbus TCP port bilgisi. Genelde 502 kullanilir.",
            "modbus_unit_id": "Modbus slave / unit kimligi. Genelde 1 kullanilir.",
            "status_address": "PLC durum alaninin ilk Modbus adresi. Ornek referans: Holding Register 400000.",
            "status_count": "Durum blogundan okunacak toplam register sayisi.",
            "live_record_address": "Canli kayit blogunun ilk Modbus adresi. Ornek referans: Holding Register 400100.",
            "live_record_count": "Canli kayit icin okunacak toplam register sayisi.",
            "history_base_address": "Ring buffer history blogunun ilk adresi. Ornek referans: Holding Register 400300.",
            "history_record_words": "Tek bir history kaydinin kac word tuttugu.",
            "history_capacity": "PLC ring buffer toplam kayit kapasitesi.",
            "cmd_circuit_select": "Python tarafinin devre secimi yazdigi register. Ornek referans: Holding Register 401000.",
            "cmd_start_request": "Test baslatma istegi register adresi. Ornek referans: Holding Register 401001.",
            "cmd_stop_request": "Test durdurma istegi register adresi. Ornek referans: Holding Register 401002.",
            "cmd_abort_request": "Abort istegi register adresi. Ornek referans: Holding Register 401003.",
            "cmd_test_phase": "Python tarafinin aktif fazi yazdigi register. Ornek referans: Holding Register 401004.",
            "cmd_test_active": "Test aktif bilgisinin yazildigi register. Ornek referans: Holding Register 401005.",
            "cmd_time_sync_request": "Zaman senkron talebi register adresi. Ornek referans: Holding Register 401010.",
            "cmd_time_sync_unix_high": "Unix zamaninin high word register adresi. Ornek referans: Holding Register 401011.",
            "cmd_time_sync_unix_low": "Unix zamaninin low word register adresi. Ornek referans: Holding Register 401012.",
        }
        for field_name, label in labels.items():
            self.fields[field_name].label = label
        for field_name, help_text in help_texts.items():
            self.fields[field_name].help_text = help_text
            self.fields[field_name].widget.attrs.setdefault("min", "0")

    def sections(self) -> list[dict[str, object]]:
        titles = {
            "connection_block": "PLC Haberlesme",
            "status_block": "Durum Blogu",
            "live_block": "Canli Kayit Blogu",
            "history_block": "History / Ring Buffer",
            "command_block": "Test Komut Registerlari",
            "time_sync_block": "Zaman Senkronu Registerlari",
        }
        descriptions = {
            "connection_block": "PLC IP, port ve Modbus unit bilgileri. Polling ve manuel zaman senkronu bu alanlari kullanir. Simulasyon modu icin ayri bir IP adresi gerekmez.",
            "status_block": "PLC genel durum, hazirlik ve buffer metadata alanlari.",
            "live_block": "Anlik proses kaydinin okundugu blok.",
            "history_block": "Ring buffer gecmis verilerinin tutuldugu blok.",
            "command_block": "Python tarafinin PLC'ye yazdigi ust seviye test komutlari.",
            "time_sync_block": "Python master clock icin zaman senkron registerlari.",
        }
        return [
            {
                "title": titles[key],
                "description": descriptions[key],
                "fields": [self[field_name] for field_name in field_names],
            }
            for key, field_names in self.SECTION_FIELDS.items()
        ]


class TagConfigForm(forms.ModelForm):
    class Meta:
        model = TagConfig
        fields = [
            "tag_id",
            "label",
            "label_en",
            "unit",
            "scale",
            "register_type",
            "source_block",
            "data_type",
            "word_order",
            "modbus_address",
            "register_offset",
            "validity_bit",
            "circuit_scope",
            "chart_group",
            "chart_group_title",
            "chart_group_title_en",
            "chart_color",
            "simulation_enabled",
            "simulation_base",
            "simulation_amplitude",
            "simulation_wave",
            "is_active",
            "include_in_limits",
            "include_in_reports",
        ]

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        apply_bootstrap_form_style(self)
        for field_name in ("tag_id", "chart_group_title", "chart_group_title_en", "chart_color", "unit"):
            self.fields[field_name].widget.attrs.setdefault("placeholder", "")
        chart_group_choices = [
            (group.slug, f"{self._chart_group_label(group.slug, 'tr')} / {self._chart_group_label(group.slug, 'en')}")
            for group in CHART_GROUP_DEFINITIONS
        ]
        self.fields["chart_group"] = forms.ChoiceField(
            choices=chart_group_choices,
            widget=forms.Select(attrs={"class": "form-select"}),
            required=True,
            label="Grafik Grubu",
        )
        self.fields["tag_id"].widget.attrs.setdefault("placeholder", "105")
        self.fields["tag_id"].widget.attrs.setdefault("min", "1")
        self.fields["modbus_address"].widget.attrs.setdefault("min", "0")
        self.fields["register_offset"].widget.attrs.setdefault("min", "0")
        self.fields["validity_bit"].widget.attrs.setdefault("min", "0")
        self.fields["validity_bit"].help_text = "0-15 = Validity Word 1, 16-31 = Validity Word 2"
        self.fields["chart_color"].widget = forms.TextInput(
            attrs={
                "type": "color",
                "class": "form-control form-control-color",
            }
        )
        self.fields["tag_id"].help_text = "Kalici sayisal teknik kimlik. Sistem icinde referans icin kullanilir."
        self.fields["label_en"].help_text = "Ingilizce arayuz ve raporlarda kullanilir."
        current_register_type = (
            str(self.instance.register_type)
            if self.instance and getattr(self.instance, "pk", None)
            else str(self.initial.get("register_type") or TagConfig.RegisterType.HOLDING)
        )
        current_address = (
            int(self.instance.modbus_address)
            if self.instance and getattr(self.instance, "pk", None)
            else int(self.initial.get("modbus_address") or 0)
        )
        self.fields["modbus_address"].help_text = (
            "PLC register haritasindaki mutlak Modbus adresi. "
            f"{modbus_reference_text(current_register_type, current_address)}. "
            "Ornek: adres 1030 ise Holding icin 401030, Input icin 301030 gorunur."
        )
        self.fields["register_offset"].help_text = "Kayit blogu icindeki kelime ofseti."
        self.fields["data_type"].help_text = "Parser bu veri tipine gore ham register okumasini cozer."
        self.fields["tag_id"].label = "Tag ID"
        self.fields["label"].label = "Turkce Etiket"
        self.fields["label_en"].label = "Ingilizce Etiket"
        self.fields["register_type"].label = "Register Tipi"
        self.fields["source_block"].label = "Kaynak Blogu"
        self.fields["data_type"].label = "Veri Tipi"
        self.fields["word_order"].label = "Word Sirasi"
        self.fields["modbus_address"].label = "Modbus Adresi"
        self.fields["register_offset"].label = "Kayit Ofseti"
        self.fields["validity_bit"].label = "Validity Bit"
        self.fields["circuit_scope"].label = "Devre Kapsami"
        self.fields["chart_group"].label = "Grafik Grubu"
        self.fields["chart_group"].help_text = "Grafiklerde hangi ana grupta gosterilecegini secin."
        self.fields["chart_group_title"].label = "Grup Basligi (TR)"
        self.fields["chart_group_title"].help_text = "Bos birakilirsa secilen grafik grubu icin varsayilan Turkce baslik kullanilir."
        self.fields["chart_group_title_en"].label = "Grup Basligi (EN)"
        self.fields["chart_group_title_en"].help_text = "Bos birakilirsa secilen grafik grubu icin varsayilan Ingilizce baslik kullanilir."
        self.fields["chart_color"].label = "Grafik Rengi"
        self.fields["simulation_enabled"].label = "Simulasyon Aktif"
        self.fields["simulation_enabled"].help_text = "Aciksa bu tag simulasyon verisi kullanir. Kapaliysa PLC'den okunur."
        self.fields["simulation_base"].label = "Simulasyon Baz"
        self.fields["simulation_amplitude"].label = "Simulasyon Genligi"
        self.fields["simulation_wave"].label = "Simulasyon Dalga"
        if self.instance and self.instance.pk:
            self.fields["tag_id"].disabled = True
            self.fields["tag_id"].help_text = (
                "Tag ID mevcut kayitlarda degistirilemez. Yeni tag icin yeni bir kayit olusturun."
            )

    def clean_tag_id(self) -> int:
        tag_id = int(self.cleaned_data["tag_id"])
        if self.instance and self.instance.pk and int(self.instance.tag_id) != tag_id:
            raise forms.ValidationError("Mevcut bir tag icin Tag ID degistirilemez.")
        return tag_id

    def clean(self) -> dict[str, object]:
        cleaned_data = super().clean()
        label = str(cleaned_data.get("label") or "").strip()
        label_en = str(cleaned_data.get("label_en") or "").strip()
        chart_group = str(cleaned_data.get("chart_group") or "").strip()
        chart_group_title = str(cleaned_data.get("chart_group_title") or "").strip()
        chart_group_title_en = str(cleaned_data.get("chart_group_title_en") or "").strip()
        if label and not label_en:
            cleaned_data["label_en"] = label
        if chart_group and not chart_group_title:
            cleaned_data["chart_group_title"] = self._chart_group_label(chart_group, "tr")
        if chart_group and not chart_group_title_en:
            cleaned_data["chart_group_title_en"] = self._chart_group_label(chart_group, "en")
        return cleaned_data

    @staticmethod
    def _chart_group_label(group_slug: str, language: str) -> str:
        labels = {
            "pressure": {"tr": "Basinc Sensorleri", "en": "Pressure Sensors"},
            "process_temperature": {"tr": "Proses Hat Sicakliklari", "en": "Process Line Temperatures"},
            "air_humidity": {"tr": "Hava Nem Sensorleri", "en": "Air Humidity Sensors"},
            "air_flow": {"tr": "Hava Akis Sensorleri", "en": "Air Flow Sensors"},
            "water_temperature": {"tr": "Kondenser Su Sicakliklari", "en": "Condenser Water Temperatures"},
            "air_temperature": {"tr": "Hava Sicaklik Sensorleri", "en": "Air Temperature Sensors"},
            "comp1_electrical": {"tr": "Devre 1 Elektriksel", "en": "Circuit 1 Electrical"},
            "comp2_electrical": {"tr": "Devre 2 Elektriksel", "en": "Circuit 2 Electrical"},
        }
        return labels.get(group_slug, {}).get(language, group_slug.replace("_", " ").title())
