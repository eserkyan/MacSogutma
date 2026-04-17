function buildDatasets(source, key, label, color) {
    const phaseKeys = Object.keys(source || {});
    const labels = [];
    const values = [];
    phaseKeys.forEach((phase) => {
        (source[phase].labels || []).forEach((item, index) => {
            labels.push(`${phase} ${index + 1}`);
            values.push(source[phase][key][index]);
        });
    });
    return {
        labels,
        datasets: [{ label, data: values, borderColor: color, backgroundColor: color, tension: 0.25 }],
    };
}

function safeParseJson(rawValue, fallback = {}) {
    if (!rawValue) {
        return fallback;
    }
    try {
        return JSON.parse(rawValue);
    } catch (error) {
        console.warn("JSON parse warning", error);
        return fallback;
    }
}

function localizeTestStatus(status, language = "tr") {
    const labels = {
        DRAFT: { tr: "Taslak", en: "Draft" },
        START_REQUESTED: { tr: "Baslatiliyor", en: "Starting" },
        RUNNING: { tr: "Devam Ediyor", en: "Running" },
        COMPLETED_PASS: { tr: "Gecti", en: "Passed" },
        COMPLETED_FAIL: { tr: "Kaldi", en: "Failed" },
        ABORTED: { tr: "Iptal Edildi", en: "Aborted" },
        FAILED_TO_START: { tr: "Kaldi", en: "Failed to Start" },
    };
    return labels[status]?.[language] || status || "-";
}

function localizeStatusFlag(key, language = "tr") {
    const labels = {
        test_active: { tr: "Test Aktif", en: "Test Active" },
        alarm_active: { tr: "Alarm Aktif", en: "Alarm Active" },
        comp1_rng: { tr: "Comp1 RNG", en: "Comp1 RNG" },
        comp2_rng: { tr: "Comp2 RNG", en: "Comp2 RNG" },
    };
    return labels[key]?.[language] || key;
}

function circuitLabel(value, language = "tr") {
    const labels = {
        0: { tr: "-", en: "-" },
        1: { tr: "Devre 1", en: "Circuit 1" },
        2: { tr: "Devre 2", en: "Circuit 2" },
        3: { tr: "Devre 1 + Devre 2", en: "Circuit 1 + Circuit 2" },
    };
    return labels[value]?.[language] || String(value ?? "-");
}

function phaseLabelShort(phase, language = "tr") {
    const normalized = Number(phase);
    const trMap = { 0: "Bekleme", 1: "Start", 2: "Stable", 3: "Stop", 4: "Manuel", 5: "Abort" };
    const enMap = { 0: "Idle", 1: "Start", 2: "Stable", 3: "Stop", 4: "Manual", 5: "Abort" };
    return (language === "tr" ? trMap : enMap)[normalized] || String(phase ?? "-");
}

function resolveUiState(payload) {
    const state = payload?.ui_state || {};
    const active = state.active_test || payload?.active_test_summary || {};
    return {
        hasActiveTest: Boolean(state.has_active_test ?? payload?.has_active_test),
        id: active.id ?? payload?.active_test_id ?? null,
        testNo: active.test_no ?? payload?.active_test_no ?? "",
        status: active.status ?? "",
        selectedCircuit: resolveStableCircuitValue(active.selected_circuit, 0),
        currentPhase: Number(active.current_phase ?? payload?.active_test_meta?.current_phase ?? 0),
        companyName: active.company_name ?? "",
        modelName: active.model_name ?? "",
        recipeName: active.recipe_name ?? "",
    };
}

function applySharedUiState(payload) {
    const language = document.documentElement.lang || "tr";
    const state = resolveUiState(payload);

    const globalCard = document.getElementById("global-active-test-card");
    const globalBadge = document.getElementById("global-active-test-badge");
    const globalNo = document.getElementById("global-active-test-no");
    const globalRecipe = document.getElementById("global-active-test-recipe");
    const globalCircuit = document.getElementById("global-active-test-circuit");
    const globalPhase = document.getElementById("global-active-test-phase");
    if (globalCard && globalBadge && globalNo && globalRecipe && globalCircuit && globalPhase) {
        if (state.hasActiveTest) {
            globalCard.classList.remove("d-none");
            globalBadge.textContent = localizeTestStatus(state.status, language);
            globalBadge.className = "badge";
            if (state.status === "COMPLETED_PASS") {
                globalBadge.classList.add("text-bg-success");
            } else if (["COMPLETED_FAIL", "ABORTED", "FAILED_TO_START"].includes(state.status)) {
                globalBadge.classList.add("text-bg-danger");
            } else {
                globalBadge.classList.add("text-bg-primary");
            }
            globalNo.textContent = state.testNo || "-";
            globalRecipe.textContent = state.recipeName || "-";
            globalCircuit.textContent = circuitLabel(state.selectedCircuit, language);
            globalPhase.textContent = phaseLabelShort(state.currentPhase, language);
        } else {
            globalCard.classList.add("d-none");
            globalBadge.textContent = language === "tr" ? "Aktif Test Yok" : "No Active Test";
            globalBadge.className = "badge text-bg-secondary";
            globalNo.textContent = "-";
            globalRecipe.textContent = "-";
            globalCircuit.textContent = "-";
            globalPhase.textContent = "-";
        }
    }

    const activeTestCommandedCircuitNode = document.getElementById("active-test-commanded-circuit");
    if (activeTestCommandedCircuitNode) {
        activeTestCommandedCircuitNode.dataset.currentCircuit = String(state.selectedCircuit);
        activeTestCommandedCircuitNode.textContent = circuitLabel(state.selectedCircuit, language);
    }
    setText("active-test-status-label", localizeTestStatus(state.status, language));
    setText("active-test-phase", phaseLabelShort(state.currentPhase, language));
    setText("active-test-phase-top", phaseLabelShort(state.currentPhase, language));

    const metricCommandedCircuit = document.getElementById("metric-commanded-circuit");
    if (metricCommandedCircuit) {
        metricCommandedCircuit.dataset.currentCircuit = String(state.selectedCircuit);
        metricCommandedCircuit.textContent = circuitLabel(state.selectedCircuit, language);
    }

    const dashboardActiveTestCircuit = document.getElementById("dashboard-active-test-commanded-circuit");
    if (dashboardActiveTestCircuit) {
        dashboardActiveTestCircuit.dataset.currentCircuit = String(state.selectedCircuit);
        dashboardActiveTestCircuit.textContent = `${language === "tr" ? "Komutlanan Devre" : "Commanded Circuit"}: ${circuitLabel(state.selectedCircuit, language)}`;
    }
    const dashboardActiveTestStatus = document.getElementById("dashboard-active-test-status");
    if (dashboardActiveTestStatus) {
        dashboardActiveTestStatus.textContent = `${language === "tr" ? "Durum" : "Status"}: ${localizeTestStatus(state.status, language)}`;
    }
}

function resolveStableCircuitValue(incomingValue, fallbackValue = 0) {
    const parsedIncoming = Number(incomingValue ?? 0);
    if ([1, 2, 3].includes(parsedIncoming)) {
        return parsedIncoming;
    }
    const parsedFallback = Number(fallbackValue ?? 0);
    if ([1, 2, 3].includes(parsedFallback)) {
        return parsedFallback;
    }
    return 0;
}

function getJsonScriptData(scriptId, fallback = {}) {
    const node = document.getElementById(scriptId);
    if (!node) {
        return fallback;
    }
    return safeParseJson(node.textContent, fallback);
}

const phaseBandPlugin = {
    id: "phaseBandPlugin",
    beforeDatasetsDraw(chart) {
        const config = chart?.options?.plugins?.phaseBands;
        if (!config?.enabled) {
            return;
        }
        const labels = config.xValues || [];
        const phases = config.phases || [];
        if (!labels.length || labels.length !== phases.length) {
            return;
        }
        const xScale = chart.scales.x;
        const chartArea = chart.chartArea;
        if (!xScale || !chartArea) {
            return;
        }

        const { ctx } = chart;
        ctx.save();
        let startIndex = 0;
        for (let index = 1; index <= phases.length; index += 1) {
            const hasChanged = index === phases.length || phases[index] !== phases[startIndex];
            if (!hasChanged) {
                continue;
            }
            const startValue = labels[startIndex];
            const endValue = index < labels.length ? labels[index] : labels[labels.length - 1];
            const xStart = xScale.getPixelForValue(startValue);
            const xEnd = index === phases.length ? chartArea.right : xScale.getPixelForValue(endValue);
            ctx.fillStyle = startIndex % 2 === 0 ? "rgba(148, 163, 184, 0.10)" : "rgba(255, 255, 255, 0.0)";
            ctx.fillRect(xStart, chartArea.top, Math.max(1, xEnd - xStart), chartArea.bottom - chartArea.top);

            startIndex = index;
        }
        ctx.restore();
    },
};

const phaseMarkerPlugin = {
    id: "phaseMarkerPlugin",
    afterDatasetsDraw(chart) {
        const config = chart?.options?.plugins?.phaseMarkers;
        const markers = config?.markers || [];
        if (!markers.length) {
            return;
        }
        const xScale = chart.scales.x;
        const chartArea = chart.chartArea;
        if (!xScale || !chartArea) {
            return;
        }

        const { ctx } = chart;
        ctx.save();
        markers.forEach((marker) => {
            const xPosition = xScale.getPixelForValue(marker.position);
            ctx.strokeStyle = marker.color || "rgba(15, 23, 42, 0.95)";
            ctx.lineWidth = 2.5;
            ctx.setLineDash([8, 4]);
            ctx.beginPath();
            ctx.moveTo(xPosition, chartArea.top);
            ctx.lineTo(xPosition, chartArea.bottom);
            ctx.stroke();
            ctx.setLineDash([]);
            if (marker.label) {
                ctx.save();
                ctx.translate(xPosition + 12, chartArea.bottom - 8);
                ctx.rotate(-Math.PI / 2);
                ctx.fillStyle = marker.color || "rgba(15, 23, 42, 0.95)";
                ctx.font = "600 12px sans-serif";
                ctx.fillText(marker.label, 0, 0);
                ctx.restore();
            }
        });
        ctx.restore();
    },
};

const compressorRunPlugin = {
    id: "compressorRunPlugin",
    afterDraw(chart) {
        const config = chart?.options?.plugins?.compressorRuns;
        const rows = config?.rows || [];
        const segments = config?.segments || [];
        if (!rows.length || !segments.length) {
            return;
        }
        const xScale = chart.scales.x;
        const chartArea = chart.chartArea;
        if (!xScale || !chartArea) {
            return;
        }
        const { ctx } = chart;
        const rowGap = 12;
        const baseY = Math.max(10, chartArea.top - (rows.length * rowGap) - 8);
        ctx.save();
        rows.forEach((row, rowIndex) => {
            const y = baseY + (rowIndex * rowGap);
            ctx.strokeStyle = "rgba(148, 163, 184, 0.35)";
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.moveTo(chartArea.left, y);
            ctx.lineTo(chartArea.right, y);
            ctx.stroke();
            ctx.fillStyle = row.color || "#0f172a";
            ctx.font = "600 10px sans-serif";
            ctx.fillText(row.label || "", chartArea.left, y - 4);
        });
        segments.forEach((segment) => {
            const rowIndex = Number(segment.row || 0);
            const y = baseY + (rowIndex * rowGap);
            const xStart = xScale.getPixelForValue(segment.start);
            const xEnd = xScale.getPixelForValue(segment.end);
            ctx.strokeStyle = segment.color || "#2563eb";
            ctx.lineWidth = 5;
            ctx.lineCap = "round";
            ctx.beginPath();
            ctx.moveTo(xStart, y);
            ctx.lineTo(Math.max(xStart + 2, xEnd), y);
            ctx.stroke();
        });
        ctx.restore();
    },
};

Chart.register(phaseBandPlugin, phaseMarkerPlugin, compressorRunPlugin);

function createOrUpdateChart(canvas, chartConfig) {
    if (canvas._chartInstance) {
        canvas._chartInstance.data = chartConfig.data;
        canvas._chartInstance.options = chartConfig.options;
        canvas._chartInstance.update("none");
        return canvas._chartInstance;
    }
    canvas._chartInstance = new Chart(canvas, chartConfig);
    return canvas._chartInstance;
}

function renderLineChart(id, key, label, color) {
    const canvas = document.getElementById(id);
    if (!canvas) {
        return;
    }
    const source = getJsonScriptData("test-detail-chart-data", {});
    createOrUpdateChart(canvas, {
        type: "line",
        data: buildDatasets(source, key, label, color),
        options: { responsive: true, maintainAspectRatio: false, animation: false },
    });
}

function renderMultiDatasetChart(canvasId) {
    renderMultiDatasetChartFromSource(canvasId, "active-test-chart-data", canvasId);
}

function renderMultiDatasetChartFromSource(canvasId, scriptId, sourceChartId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        return;
    }
    const source = getJsonScriptData(scriptId, {});
    const chartEntry = (source.charts || []).find((item) => item.chart_id === sourceChartId);
    const labels = chartEntry?.labels || [];
    const datasets = chartEntry?.datasets || [];
    const phases = chartEntry?.phases || [];
    const phaseMarkers = chartEntry?.phase_markers || [];
    const compressorRunBands = chartEntry?.compressor_run_bands || {};
    canvas.dataset.lastSequence = String(labels.slice(-1)[0] || 0);
    canvas.dataset.windowEndSec = String(chartEntry?.window_end_sec ?? "");
    canvas.dataset.phaseOffsetSec = String(chartEntry?.phase_offset_sec ?? 0);
    createOrUpdateChart(canvas, {
        type: "line",
        data: {
            datasets: [
                ...datasets.flatMap((dataset) => {
                const baseDataset = {
                    label: dataset.label,
                    labelToKey: dataset.key,
                    data: dataset.data.map((value, index) => ({ x: labels[index], y: value })),
                    borderColor: dataset.borderColor,
                    backgroundColor: dataset.backgroundColor,
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.2,
                    fill: false,
                    spanGaps: true,
                };
                const alertDataset = {
                    type: "scatter",
                    label: `${dataset.label} Limit`,
                    data: dataset.alert_points || [],
                    borderColor: "#dc2626",
                    backgroundColor: "#dc2626",
                    pointRadius: 6,
                    pointHoverRadius: 9,
                    pointHitRadius: 16,
                    pointBorderWidth: 1.5,
                    pointBorderColor: "#ffffff",
                    pointStyle: "triangle",
                    showLine: false,
                    parsing: false,
                    order: 100,
                };
                return (dataset.alert_points || []).length ? [baseDataset, alertDataset] : [baseDataset];
                }),
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            layout: {
                padding: {
                    top: 14 + ((compressorRunBands.rows || []).length * 16),
                    right: 12,
                    bottom: 18,
                    left: 12,
                },
            },
            interaction: {
                mode: "nearest",
                axis: "xy",
                intersect: false,
                includeInvisible: true,
            },
            plugins: {
                legend: { position: "bottom" },
                tooltip: {
                    mode: "nearest",
                    intersect: false,
                    displayColors: true,
                    callbacks: {
                        title(items) {
                            const first = items?.[0];
                            const language = document.documentElement.lang || "tr";
                            const prefix = language === "tr" ? "Sure" : "Time";
                            return first ? `${prefix}: ${formatElapsedLabel(first.parsed?.x)}` : "";
                        },
                        label(item) {
                            const language = document.documentElement.lang || "tr";
                            const raw = item.raw || {};
                            if (raw.message) {
                                return `${item.dataset.label}: ${raw.message}`;
                            }
                            if (item.parsed?.y !== undefined) {
                                return `${item.dataset.label}: ${formatNumber(item.parsed.y)}`;
                            }
                            return item.dataset.label || "";
                        },
                        afterLabel(item) {
                            const language = document.documentElement.lang || "tr";
                            const raw = item.raw || {};
                            if (raw.phase_name && raw.limit_type) {
                                if (language === "tr") {
                                    return `Faz: ${raw.phase_name} | Limit: ${raw.limit_type} ${formatNumber(raw.limit_value)}`;
                                }
                                return `Phase: ${raw.phase_name} | Limit: ${raw.limit_type} ${formatNumber(raw.limit_value)}`;
                            }
                            return "";
                        },
                    },
                },
                phaseBands: {
                    enabled: true,
                    xValues: [...labels],
                    phases,
                    phaseLabels: source.phase_labels || {},
                },
                phaseMarkers: {
                    markers: phaseMarkers,
                },
                compressorRuns: {
                    rows: compressorRunBands.rows || [],
                    segments: compressorRunBands.segments || [],
                    lastFlags: compressorRunBands.last_flags || {},
                    lastX: compressorRunBands.last_x || 0,
                },
            },
            scales: {
                x: {
                    type: "linear",
                    min: chartEntry?.axis_min,
                    max: chartEntry?.axis_max,
                    title: { display: true, text: "Sure" },
                    ticks: {
                        callback(value) {
                            return formatElapsedLabel(value);
                        },
                        minRotation: 90,
                        maxRotation: 90,
                        autoSkip: true,
                    },
                },
                y: { beginAtZero: false },
            },
        },
    });
}

function renderSparklineCharts() {
    document.querySelectorAll(".sparkline-chart").forEach((canvas) => {
        const labels = safeParseJson(canvas.dataset.labels, []);
        const series = safeParseJson(canvas.dataset.series, []);
        const color = canvas.dataset.color || "#2563eb";
        const label = canvas.dataset.label || "";
        const unit = canvas.dataset.unit || "";
        const hasUsablePoint = series.some((value) => value !== null && value !== undefined);
        if (!labels.length || !series.length || !hasUsablePoint) {
            return;
        }
        const yBounds = calculateBufferedSparklineBounds(series, canvas);
        createOrUpdateChart(canvas, {
            type: "line",
            data: {
                labels,
                datasets: [{
                    label,
                    data: series,
                    borderColor: color,
                    backgroundColor: color,
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.35,
                    fill: false,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: {
                    mode: "index",
                    intersect: false,
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        enabled: true,
                        displayColors: false,
                        callbacks: {
                            title() {
                                return "";
                            },
                            label(item) {
                                const value = item.parsed?.y;
                                if (value === null || value === undefined) {
                                    return "";
                                }
                                return formatNumber(value);
                            },
                        },
                    },
                },
                scales: {
                    x: { display: false },
                    y: {
                        display: false,
                        min: yBounds.min,
                        max: yBounds.max,
                    },
                },
            },
        });
    });
}

function calculateBufferedSparklineBounds(series, canvas) {
    const numericValues = series
        .map((value) => Number(value))
        .filter((value) => Number.isFinite(value));
    if (!numericValues.length) {
        return { min: 0, max: 1 };
    }

    const currentMin = Math.min(...numericValues);
    const currentMax = Math.max(...numericValues);
    const currentRange = Math.max(currentMax - currentMin, Math.abs(currentMax) * 0.04, 0.5);
    const padding = Math.max(currentRange * 0.2, 0.25);

    let nextMin = currentMin - padding;
    let nextMax = currentMax + padding;

    if (currentMin >= 0) {
        nextMin = Math.max(0, nextMin);
    }

    const previousMin = Number(canvas.dataset.yMin);
    const previousMax = Number(canvas.dataset.yMax);
    const hasPreviousBounds = Number.isFinite(previousMin) && Number.isFinite(previousMax) && previousMax > previousMin;

    if (hasPreviousBounds) {
        const previousRange = previousMax - previousMin;
        const shrinkBuffer = Math.max(previousRange * 0.12, 0.2);

        if (nextMin > previousMin) {
            nextMin = Math.min(nextMin, previousMin + shrinkBuffer);
        } else {
            nextMin = Math.min(previousMin, nextMin);
        }

        if (nextMax < previousMax) {
            nextMax = Math.max(nextMax, previousMax - shrinkBuffer);
        } else {
            nextMax = Math.max(previousMax, nextMax);
        }

        if (nextMax <= nextMin) {
            nextMin = previousMin;
            nextMax = previousMax;
        }
    }

    canvas.dataset.yMin = String(nextMin);
    canvas.dataset.yMax = String(nextMax);

    return { min: nextMin, max: nextMax };
}

function boolText(value, language, trueTextTr, falseTextTr, trueTextEn, falseTextEn) {
    if (language === "tr") {
        return value ? trueTextTr : falseTextTr;
    }
    return value ? trueTextEn : falseTextEn;
}

function setText(id, value) {
    const node = document.getElementById(id);
    if (node) {
        node.textContent = value;
    }
}

function formatDashboardValue(value, language) {
    if (value === null || value === undefined || value === "") {
        return language === "tr" ? "Veri Yok" : "No Data";
    }
    const parsed = Number(value);
    if (!Number.isNaN(parsed) && value !== true && value !== false) {
        return parsed.toFixed(2);
    }
    return String(value);
}

function phaseText(phase) {
    const map = { 0: "IDLE", 1: "START", 2: "STABLE", 3: "STOP", 4: "MANUAL", 5: "ABORTED" };
    return map[phase] || String(phase ?? "");
}

function phaseLabel(phase, language) {
    const normalized = Number(phase);
    const trMap = { 0: "Bekleme", 1: "Start", 2: "Stable", 3: "Stop", 4: "Manuel", 5: "Abort" };
    const enMap = { 0: "Idle", 1: "Start", 2: "Stable", 3: "Stop", 4: "Manual", 5: "Abort" };
    const labels = language === "tr" ? trMap : enMap;
    return labels[normalized] || phaseText(phase);
}

function formatElapsedLabel(value) {
    const totalMilliseconds = Math.max(0, Math.round(Number(value || 0) * 1000));
    const totalSeconds = Math.floor(totalMilliseconds / 1000);
    const milliseconds = totalMilliseconds % 1000;
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    if (hours > 0) {
        return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    }
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}.${String(milliseconds).padStart(3, "0")}`;
}

function formatNumber(value, digits = 2) {
    const parsed = Number(value);
    if (Number.isNaN(parsed)) {
        return String(value ?? "");
    }
    return parsed.toFixed(digits);
}

function formatRemainingDuration(totalSeconds) {
    const safeSeconds = Math.max(0, Math.floor(totalSeconds || 0));
    const hours = Math.floor(safeSeconds / 3600);
    const minutes = Math.floor((safeSeconds % 3600) / 60);
    const seconds = safeSeconds % 60;
    if (hours > 0) {
        return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    }
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function parseDateValue(value) {
    if (!value) {
        return null;
    }
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function computeRemainingSeconds(meta) {
    if (!meta) {
        return 0;
    }
    const now = new Date();
    const startedAt = parseDateValue(meta.started_at);
    const stableStartedAt = parseDateValue(meta.stable_started_at);
    const stopStartedAt = parseDateValue(meta.stop_started_at);
    let endTime = null;

    if (stopStartedAt) {
        endTime = new Date(stopStartedAt.getTime() + Number(meta.stop_duration_sec || 0) * 1000);
    } else if (stableStartedAt) {
        endTime = new Date(
            stableStartedAt.getTime()
            + (Number(meta.stable_duration_sec || 0) + Number(meta.stop_duration_sec || 0)) * 1000
        );
    } else if (startedAt) {
        endTime = new Date(
            startedAt.getTime()
            + (
                Number(meta.start_duration_sec || 0)
                + Number(meta.stable_duration_sec || 0)
                + Number(meta.stop_duration_sec || 0)
            ) * 1000
        );
    }

    if (!endTime) {
        return 0;
    }
    return Math.max(0, Math.floor((endTime.getTime() - now.getTime()) / 1000));
}

let activeTestCountdownTimer = null;

function renderActiveTestCountdown() {
    const activeConfig = document.getElementById("active-test-live-config");
    if (!activeConfig) {
        return;
    }
    const language = document.documentElement.lang || "tr";
    const meta = safeParseJson(activeConfig.dataset.countdownMeta, {});
    const phase = meta.current_phase ?? 0;
    setText("active-test-phase", phaseLabel(phase, language));
    setText("active-test-phase-top", phaseLabel(phase, language));
    setText("active-test-remaining", formatRemainingDuration(computeRemainingSeconds(meta)));
}

function startActiveTestCountdown() {
    const activeConfig = document.getElementById("active-test-live-config");
    if (!activeConfig) {
        return;
    }
    if (activeTestCountdownTimer) {
        window.clearInterval(activeTestCountdownTimer);
    }
    renderActiveTestCountdown();
    activeTestCountdownTimer = window.setInterval(renderActiveTestCountdown, 1000);
}

function buildSeriesFromLiveHistory(liveHistory, primaryKey, secondaryKey = null) {
    const labels = liveHistory.map((item, index) => item.sequence_no ?? index + 1);
    const series = liveHistory.map((item) => {
        const values = item.values || {};
        const primary = values[primaryKey];
        const secondary = secondaryKey ? values[secondaryKey] : null;
        return primary ?? secondary ?? null;
    });
    return { labels, series };
}

function updateActiveTestChart(canvasId, labels, series, label, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        return;
    }
    const hasUsablePoint = series.some((value) => value !== null && value !== undefined);
    if (!labels.length || !hasUsablePoint) {
        return;
    }
    createOrUpdateChart(canvas, {
        type: "line",
        data: {
            labels,
            datasets: [{
                label,
                data: series,
                borderColor: color,
                backgroundColor: color,
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.3,
                fill: false,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false },
                y: { display: true },
            },
        },
    });
}

function appendLivePointToActiveCharts(liveRecord) {
    const activeConfig = document.getElementById("active-test-live-config");
    const meta = activeConfig ? safeParseJson(activeConfig.dataset.countdownMeta, {}) : {};
    const startedAt = parseDateValue(meta.started_at);
    const currentTimestamp = parseDateValue(liveRecord.timestamp);
    if (!startedAt || !currentTimestamp) {
        return;
    }
    const elapsedSeconds = Math.max(0, (currentTimestamp.getTime() - startedAt.getTime()) / 1000);
    const values = liveRecord.values || {};
    document.querySelectorAll(".active-test-chart").forEach((canvas) => {
        const chart = canvas._chartInstance;
        if (!chart) {
            return;
        }
        const phaseSlug = canvas.dataset.phaseSlug || "";
        const windowEndSec = Number(canvas.dataset.windowEndSec || 0);
        const phaseOffsetSec = Number(canvas.dataset.phaseOffsetSec || 0);
        const isPhaseSpecific = phaseSlug === "start" || phaseSlug === "stable" || phaseSlug === "stop";
        if (isPhaseSpecific && elapsedSeconds > windowEndSec) {
            return;
        }
        const chartX = elapsedSeconds - phaseOffsetSec;
        const lastSequence = Number(canvas.dataset.lastSequence || 0);
        if (lastSequence >= Number(chartX)) {
            return;
        }
        chart.data.datasets.forEach((dataset) => {
            if (dataset.labelToKey) {
                const matchedValue = values[dataset.labelToKey || ""];
                if (matchedValue !== undefined) {
                    dataset.data.push({ x: chartX, y: matchedValue });
                    return;
                }
                dataset.data.push({ x: chartX, y: null });
                return;
            }
        });
        const phaseBands = chart.options?.plugins?.phaseBands;
        if (phaseBands?.xValues) {
            phaseBands.xValues.push(chartX);
        }
        if (phaseBands?.phases) {
            phaseBands.phases.push(Number(liveRecord.test_phase ?? 0));
        }
        const compressorRuns = chart.options?.plugins?.compressorRuns;
        if (compressorRuns?.rows) {
            const statusFlags = liveRecord.status_flags || {};
            const previousLastX = Number(compressorRuns.lastX ?? chartX);
            compressorRuns.rows.forEach((row, rowIndex) => {
                const key = row.key;
                const isRunning = Boolean(statusFlags[key]);
                const wasRunning = Boolean((compressorRuns.lastFlags || {})[key]);
                compressorRuns.lastFlags[key] = isRunning;
                if (!isRunning) {
                    return;
                }
                const segments = compressorRuns.segments || [];
                const lastSegment = [...segments].reverse().find((segment) => Number(segment.row) === rowIndex);
                if (wasRunning && lastSegment) {
                    lastSegment.end = chartX;
                    return;
                }
                segments.push({
                    row: rowIndex,
                    label: row.label,
                    color: row.color,
                    start: wasRunning ? previousLastX : chartX,
                    end: chartX,
                });
                compressorRuns.segments = segments;
            });
            compressorRuns.lastX = chartX;
        }
        canvas.dataset.lastSequence = String(chartX);
        chart.update("none");
    });
}

function replaceJsonScriptData(scriptId, payload) {
    const node = document.getElementById(scriptId);
    if (!node || !payload) {
        return;
    }
    node.textContent = JSON.stringify(payload);
}

function refreshActiveTestCharts(chartData) {
    if (!chartData) {
        return "";
    }
    replaceJsonScriptData("active-test-chart-data", chartData);
    document.querySelectorAll(".active-test-chart").forEach((canvas) => {
        renderMultiDatasetChart(canvas.id);
    });
    return getChartDataSignature(chartData);
}

function getChartDataSignature(chartData) {
    const firstChart = chartData?.charts?.[0];
    if (!firstChart) {
        return "";
    }
    const labels = firstChart.labels || [];
    const lastLabel = labels.length ? labels[labels.length - 1] : "";
    return `${labels.length}:${lastLabel}`;
}

function reloadActiveTestPageOnPhaseChange(activeConfig, nextMeta) {
    const previousMeta = safeParseJson(activeConfig.dataset.countdownMeta, {});
    const previousPhase = Number(previousMeta.current_phase ?? 0);
    const nextPhase = Number(nextMeta?.current_phase ?? previousPhase);
    if (previousPhase && nextPhase && previousPhase !== nextPhase) {
        window.location.reload();
        return true;
    }
    return false;
}

function scheduleActiveTestRedirect(activeConfig) {
    const notice = document.getElementById("active-test-redirect-notice");
    const titleNode = document.getElementById("active-test-redirect-title");
    const messageNode = document.getElementById("active-test-redirect-message");
    const buttonNode = document.getElementById("active-test-redirect-button");
    if (notice) {
        notice.classList.remove("d-none");
    }
    if (titleNode) {
        titleNode.textContent = activeConfig.dataset.redirectTitle || "";
    }
    if (messageNode) {
        messageNode.textContent = activeConfig.dataset.redirectMessage || "";
    }
    if (buttonNode && activeConfig.dataset.historyUrl) {
        buttonNode.href = activeConfig.dataset.historyUrl;
    }
}

function applyDashboardUpdate(payload) {
    const dashboardConfig = document.getElementById("dashboard-live-config");
    applySharedUiState(payload);
    if (!dashboardConfig) {
        return;
    }
    const language = document.documentElement.lang || "tr";
    setText("metric-ready", boolText(payload.plc_ready, language, "EVET", "HAYIR", "YES", "NO"));
    setText("metric-comp1-rng", boolText(Boolean(payload.live_record?.status_flags?.comp1_rng), language, "ON", "OFF", "ON", "OFF"));
    setText("metric-comp2-rng", boolText(Boolean(payload.live_record?.status_flags?.comp2_rng), language, "ON", "OFF", "ON", "OFF"));
    setText("metric-fault", boolText(payload.plc_fault, language, "EVET", "HAYIR", "YES", "NO"));
    setText("metric-connection", boolText(payload.connection_ok, language, "AKTIF", "PASIF", "ACTIVE", "DOWN"));
    setText("metric-stale", boolText(payload.stale_data, language, "EVET", "HAYIR", "YES", "NO"));
    const uiState = resolveUiState(payload);
    const summaryCircuit = uiState.selectedCircuit;

    const activeTestEmpty = document.getElementById("dashboard-active-test-empty");
    const activeTestNo = document.getElementById("dashboard-active-test-no");
    const activeTestCompany = document.getElementById("dashboard-active-test-company");
    const activeTestRecipe = document.getElementById("dashboard-active-test-recipe");
    const activeTestCommandedCircuit = document.getElementById("dashboard-active-test-commanded-circuit");
    const activeTestStatus = document.getElementById("dashboard-active-test-status");
    const activeTestLink = document.getElementById("dashboard-active-test-link");
    const activeTestSummary = payload.active_test_summary || {};
    if (activeTestNo && activeTestCompany && activeTestRecipe && activeTestCommandedCircuit && activeTestStatus && activeTestLink) {
        if (payload.has_active_test) {
            activeTestNo.textContent = payload.active_test_no || "";
            activeTestCompany.textContent = `${activeTestSummary.company_name || ""} / ${activeTestSummary.model_name || ""}`;
            activeTestRecipe.textContent = activeTestSummary.recipe_name || "";
            const stableCircuit = uiState.selectedCircuit;
            activeTestCommandedCircuit.dataset.currentCircuit = String(stableCircuit);
            activeTestCommandedCircuit.textContent = `${language === "tr" ? "Komutlanan Devre" : "Commanded Circuit"}: ${circuitLabel(stableCircuit, language)}`;
            activeTestStatus.textContent = `${language === "tr" ? "Durum" : "Status"}: ${localizeTestStatus(uiState.status, language)}`;
            activeTestNo.classList.remove("d-none");
            activeTestCompany.classList.remove("d-none");
            activeTestRecipe.classList.remove("d-none");
            activeTestCommandedCircuit.classList.remove("d-none");
            activeTestStatus.classList.remove("d-none");
            activeTestLink.classList.remove("d-none");
            if (activeTestEmpty) {
                activeTestEmpty.classList.add("d-none");
            }
        } else {
            activeTestNo.classList.add("d-none");
            activeTestCompany.classList.add("d-none");
            activeTestRecipe.classList.add("d-none");
            activeTestCommandedCircuit.classList.add("d-none");
            activeTestStatus.classList.add("d-none");
            activeTestLink.classList.add("d-none");
            if (activeTestEmpty) {
                activeTestEmpty.classList.remove("d-none");
            }
        }
    }

    const recentTestsRoot = document.getElementById("dashboard-recent-tests");
    if (recentTestsRoot && Array.isArray(payload.recent_tests)) {
        recentTestsRoot.innerHTML = payload.recent_tests.map((item) => {
            const href = item.is_active ? "/tests/active/" : `/tests/${item.id}/`;
            return `
                <a class="list-group-item list-group-item-action" href="${href}">
                    <div class="d-flex justify-content-between">
                        <strong>${item.test_no}</strong>
                        <span class="badge text-bg-primary">${localizeTestStatus(item.status, language)}</span>
                    </div>
                    <div class="small text-muted">${item.company_name} / ${item.model_name}</div>
                </a>
            `;
        }).join("");
    }

    const liveRecord = payload.live_record || {};
    const values = liveRecord.values || {};
    const validity = liveRecord.validity || {};
    document.querySelectorAll("[data-param-code]").forEach((row) => {
        const code = row.dataset.paramCode;
        const valueNode = row.querySelector(".dashboard-value-text");
        const badgeNode = row.closest("tr")?.querySelector(".dashboard-validity-badge");
        if (valueNode) {
            const value = values[code];
            valueNode.textContent = formatDashboardValue(value, language);
            if (value == null) {
                valueNode.classList.add("text-danger");
            } else {
                valueNode.classList.remove("text-danger");
            }
        }
        if (badgeNode) {
            const valid = validity[code];
            badgeNode.className = "dashboard-validity-badge badge";
            if (valid === true) {
                badgeNode.classList.add("text-bg-success");
                badgeNode.textContent = language === "tr" ? "Gecerli" : "Valid";
            } else if (valid === false) {
                badgeNode.classList.add("text-bg-danger");
                badgeNode.textContent = language === "tr" ? "Gecersiz" : "Invalid";
            } else {
                badgeNode.classList.add("text-bg-secondary");
                badgeNode.textContent = language === "tr" ? "Yok" : "N/A";
            }
        }
    });

    const liveFlagsRoot = document.getElementById("dashboard-live-flags");
    if (liveFlagsRoot) {
        const flags = liveRecord.status_flags || {};
        const entries = Object.entries(flags);
        if (entries.length) {
            liveFlagsRoot.innerHTML = `<div class="d-flex flex-wrap gap-2">${entries.map(([key, value]) => `<span class="badge ${value ? "text-bg-success" : "text-bg-secondary"}">${localizeStatusFlag(key, language)}: ${value}</span>`).join("")}</div>`;
        }
    }

    const liveMetaMap = {
        "Sira Numarasi": liveRecord.sequence_no,
        "Timestamp Unix": liveRecord.timestamp_unix,
        "Zaman Damgasi": liveRecord.timestamp_unix,
        "Kayit Fazi": liveRecord.test_phase,
        "Durum Word": liveRecord.status_word,
        "Validity Word 1": liveRecord.validity_word1,
        "Validity Word 2": liveRecord.validity_word2,
        "Son Veri Zamani": payload.last_seen_at,
        "PLC Zaman Damgasi": (payload.status_json || {}).PlcCurrentUnix,
        "Zaman Senkron Sapmasi": "",
    };
    document.querySelectorAll("[data-live-meta]").forEach((row) => {
        const key = row.dataset.liveMeta;
        const valueNode = row.querySelector(".live-meta-value");
        if (valueNode && key in liveMetaMap) {
            valueNode.textContent = liveMetaMap[key] ?? "";
        }
    });

    const statusMetaMap = {
        "Hazir": payload.plc_ready,
        "Ariza": payload.plc_fault,
        "Comp1 RNG": Boolean(payload.live_record?.status_flags?.comp1_rng),
        "Comp2 RNG": Boolean(payload.live_record?.status_flags?.comp2_rng),
        "Komutlanan Devre": circuitLabel(summaryCircuit, language),
        "Baglanti Durumu": payload.connection_ok,
        "Bayat Veri": payload.stale_data,
        "Izleme Aktif": payload.monitoring_active,
        "Yazma Indeksi": (payload.status_json || {}).Buf_WriteIndex,
        "Kayit Sayisi": (payload.status_json || {}).Buf_RecordCount,
        "Buffer Boyutu": (payload.status_json || {}).Buf_BufferSize,
        "Son Sekans": (payload.status_json || {}).Buf_LastSequenceNo,
        "Veri Yasi Sn": payload.data_age_seconds ?? 0,
        "Data Age Sec": payload.data_age_seconds ?? 0,
    };
    document.querySelectorAll("[data-status-meta]").forEach((row) => {
        const key = row.dataset.statusMeta;
        const valueNode = row.querySelector(".status-meta-value");
        if (valueNode && key in statusMetaMap) {
            valueNode.textContent = statusMetaMap[key] ?? "";
        }
    });

    const liveHistory = payload.live_history || [];
    const labels = liveHistory.map((item, index) => item.sequence_no ?? index + 1);
    document.querySelectorAll(".sparkline-inline").forEach((canvas) => {
        const paramCode = canvas.closest("[data-param-code]")?.dataset.paramCode;
        if (!paramCode) return;
        const series = liveHistory.map((item) => {
            const value = (item.values || {})[paramCode];
            return value ?? null;
        });
        canvas.dataset.labels = JSON.stringify(labels);
        canvas.dataset.series = JSON.stringify(series);
    });
    renderSparklineCharts();
}

function applyActiveTestUpdate(payload) {
    const activeConfig = document.getElementById("active-test-live-config");
    applySharedUiState(payload);
    if (!activeConfig) {
        return;
    }
    const language = document.documentElement.lang || "tr";
    const activeTestId = activeConfig.dataset.testId;
    const payloadActiveTestId = payload.active_test_id;
    if (!payload.has_active_test || (activeTestId && String(payloadActiveTestId || "") !== String(activeTestId))) {
        scheduleActiveTestRedirect(activeConfig);
        return;
    }
    if (payload.active_test_meta) {
        if (reloadActiveTestPageOnPhaseChange(activeConfig, payload.active_test_meta)) {
            return;
        }
        activeConfig.dataset.countdownMeta = JSON.stringify(payload.active_test_meta);
    }
    const liveRecord = payload.live_record || {};
    const liveJsonNode = document.getElementById("active-test-live-json");
    if (liveJsonNode) {
        liveJsonNode.textContent = JSON.stringify(liveRecord, null, 2);
    }
    setText("active-test-fault", String(payload.plc_fault ?? ""));
    setText("active-test-ready", String(payload.plc_ready ?? ""));
    setText("active-test-stale", String(payload.stale_data ?? ""));
    setText("active-test-last-seen", String(payload.last_seen_at ?? ""));
    const uiState = resolveUiState(payload);
    const selectedCircuit = resolveStableCircuitValue(uiState.selectedCircuit, activeConfig.dataset.selectedCircuit);
    if ([1, 2, 3].includes(selectedCircuit)) {
        activeConfig.dataset.selectedCircuit = String(selectedCircuit);
    }
    setText("active-test-comp1-rng", boolText(Boolean(payload.live_record?.status_flags?.comp1_rng), language, "ON", "OFF", "ON", "OFF"));
    setText("active-test-comp2-rng", boolText(Boolean(payload.live_record?.status_flags?.comp2_rng), language, "ON", "OFF", "ON", "OFF"));
    renderActiveTestCountdown();

    try {
        if (liveRecord && Object.keys(liveRecord).length) {
            appendLivePointToActiveCharts(liveRecord);
        }
    } catch (error) {
        console.warn("Active test chart update warning", error);
    }
}

let wsUpdateTimer = null;
let pendingWsPayload = null;

function bindLiveSocket(configNodeId) {
    const configNode = document.getElementById(configNodeId);
    if (!configNode) {
        return;
    }
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${scheme}://${window.location.host}${configNode.dataset.wsPath}`);
    socket.onmessage = (event) => {
        try {
            const payload = safeParseJson(event.data, null);
            if (!payload) {
                return;
            }
            pendingWsPayload = payload;
            if (wsUpdateTimer) {
                return;
            }
            wsUpdateTimer = window.setTimeout(() => {
                if (pendingWsPayload) {
                    applyDashboardUpdate(pendingWsPayload);
                    applyActiveTestUpdate(pendingWsPayload);
                }
                pendingWsPayload = null;
                wsUpdateTimer = null;
            }, 400);
        } catch (error) {
            console.error("Live websocket parse error", error);
        }
    };
    socket.onerror = () => {
        console.warn("Live websocket connection failed");
    };
}

document.addEventListener("DOMContentLoaded", () => {
    renderLineChart("detailChart", "pressure", "Pressure", "#7c3aed");
    document.querySelectorAll(".active-test-chart").forEach((canvas) => {
        renderMultiDatasetChart(canvas.id);
    });
    document.querySelectorAll(".detail-test-chart").forEach((canvas) => {
        renderMultiDatasetChartFromSource(
            canvas.id,
            "test-detail-chart-data",
            canvas.dataset.sourceChartId,
        );
    });
    renderSparklineCharts();
    startActiveTestCountdown();
    bindLiveSocket("global-live-config");
});
