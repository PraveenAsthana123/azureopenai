# Project 9: Predictive Maintenance for IoT Manufacturing

## Executive Summary

An end-to-end IoT predictive maintenance platform that ingests sensor data from manufacturing equipment, predicts failures using ML models, and provides GenAI-powered insights for maintenance planning.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                  PREDICTIVE MAINTENANCE IoT PLATFORM                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           EDGE / FACTORY FLOOR                                       │
│                                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │ CNC Machines │  │ Conveyors    │  │ Pumps/Motors │  │ HVAC Systems           │   │
│  │              │  │              │  │              │  │                        │   │
│  │ Sensors:     │  │ Sensors:     │  │ Sensors:     │  │ Sensors:               │   │
│  │ - Vibration  │  │ - Speed      │  │ - Pressure   │  │ - Temperature          │   │
│  │ - Temperature│  │ - Load       │  │ - Flow rate  │  │ - Humidity             │   │
│  │ - Spindle    │  │ - Alignment  │  │ - Vibration  │  │ - Energy               │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘   │
│         │                 │                  │                      │               │
│         └─────────────────┴──────────────────┴──────────────────────┘               │
│                                      │                                              │
│                           ┌──────────▼──────────┐                                   │
│                           │   Azure IoT Edge    │                                   │
│                           │   (Edge Gateway)    │                                   │
│                           │                     │                                   │
│                           │ - Data aggregation  │                                   │
│                           │ - Edge ML inference │                                   │
│                           │ - Protocol convert  │                                   │
│                           │ - Store & forward   │                                   │
│                           └──────────┬──────────┘                                   │
└──────────────────────────────────────┼──────────────────────────────────────────────┘
                                       │
                              MQTT/AMQP/HTTPS
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────────────┐
│                           AZURE IoT HUB                                              │
│                                      │                                              │
│                   ┌──────────────────▼──────────────────┐                           │
│                   │         IoT Hub                      │                           │
│                   │                                      │                           │
│                   │  - Device management (10K+ devices)  │                           │
│                   │  - Device twin (desired/reported)    │                           │
│                   │  - Cloud-to-device messaging         │                           │
│                   │  - Message routing                   │                           │
│                   └──────────────────┬──────────────────┘                           │
│                                      │                                              │
│                    ┌─────────────────┼─────────────────┐                           │
│                    │                 │                 │                           │
│                    ▼                 ▼                 ▼                           │
│             ┌───────────┐     ┌───────────┐     ┌───────────┐                      │
│             │ Hot Path  │     │ Warm Path │     │ Cold Path │                      │
│             │ Event Hub │     │ Storage   │     │ Archive   │                      │
│             └─────┬─────┘     └─────┬─────┘     └─────┬─────┘                      │
│                   │                 │                 │                            │
└───────────────────┼─────────────────┼─────────────────┼────────────────────────────┘
                    │                 │                 │
┌───────────────────┼─────────────────┼─────────────────┼────────────────────────────┐
│                   │    STREAM PROCESSING              │                            │
│                   │                 │                 │                            │
│                   ▼                 │                 │                            │
│  ┌─────────────────────────────┐    │                 │                            │
│  │   Azure Stream Analytics    │    │                 │                            │
│  │                             │    │                 │                            │
│  │  Real-time Analytics:       │    │                 │                            │
│  │  - Anomaly detection        │    │                 │                            │
│  │  - Threshold alerts         │    │                 │                            │
│  │  - Rolling aggregations     │    │                 │                            │
│  │  - Pattern detection        │    │                 │                            │
│  └──────────────┬──────────────┘    │                 │                            │
│                 │                    │                 │                            │
│                 ▼                    ▼                 ▼                            │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                      DATA LAKE (ADLS Gen2)                                   │   │
│  │                                                                              │   │
│  │  /raw/                     /processed/              /models/                 │   │
│  │  └── {device}/             └── aggregated/          └── trained/             │   │
│  │      └── {date}/               └── features/            └── versions/        │   │
│  │          └── data.parquet      └── predictions/                              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                              │
└──────────────────────────────────────┼──────────────────────────────────────────────┘
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────────────┐
│                    ML PREDICTION PIPELINE                                            │
│                                      │                                              │
│  ┌───────────────────────────────────▼───────────────────────────────────────────┐  │
│  │                        Azure Machine Learning                                  │  │
│  │                                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                    FEATURE ENGINEERING                                   │  │  │
│  │  │                                                                          │  │  │
│  │  │  Raw Sensor Data                                                         │  │  │
│  │  │       │                                                                  │  │  │
│  │  │       ▼                                                                  │  │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │  │  │
│  │  │  │ Time-based  │  │ Statistical │  │ Frequency   │  │ Rolling Window  │ │  │  │
│  │  │  │             │  │             │  │ Domain      │  │                 │ │  │  │
│  │  │  │ - Hour      │  │ - Mean      │  │ - FFT       │  │ - 1h, 6h, 24h   │ │  │  │
│  │  │  │ - Day       │  │ - Std Dev   │  │ - Peak freq │  │ - Trend         │ │  │  │
│  │  │  │ - Runtime   │  │ - Skewness  │  │ - Power     │  │ - Rate change   │ │  │  │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  │                                      │                                        │  │
│  │                                      ▼                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                    PREDICTION MODELS                                     │  │  │
│  │  │                                                                          │  │  │
│  │  │  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────┐ │  │  │
│  │  │  │ Remaining Useful │  │ Anomaly          │  │ Failure Classification │ │  │  │
│  │  │  │ Life (RUL)       │  │ Detection        │  │                        │ │  │  │
│  │  │  │                  │  │                  │  │ - Bearing failure      │ │  │  │
│  │  │  │ - LSTM           │  │ - Isolation      │  │ - Motor burnout        │ │  │  │
│  │  │  │ - Survival       │  │   Forest         │  │ - Sensor drift         │ │  │  │
│  │  │  │   analysis       │  │ - Autoencoder    │  │ - Calibration needed   │ │  │  │
│  │  │  │                  │  │                  │  │                        │ │  │  │
│  │  │  │ Output:          │  │ Output:          │  │ Output:                │ │  │  │
│  │  │  │ Days until fail  │  │ Anomaly score    │  │ Failure type + prob    │ │  │  │
│  │  │  └──────────────────┘  └──────────────────┘  └────────────────────────┘ │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  │                                      │                                        │  │
│  │  ┌───────────────────────────────────▼───────────────────────────────────┐    │  │
│  │  │              ML Endpoints (Real-time Inference)                        │    │  │
│  │  │              Batch scoring daily for all equipment                     │    │  │
│  │  └───────────────────────────────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                              │
└──────────────────────────────────────┼──────────────────────────────────────────────┘
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────────────┐
│                    GENAI INSIGHTS & RECOMMENDATIONS                                  │
│                                      │                                              │
│                   ┌──────────────────▼──────────────────┐                           │
│                   │        Azure OpenAI (GPT-4o)        │                           │
│                   │                                      │                           │
│                   │  Input:                              │                           │
│                   │  - Equipment profile                 │                           │
│                   │  - Sensor trends                     │                           │
│                   │  - ML predictions                    │                           │
│                   │  - Maintenance history               │                           │
│                   │                                      │                           │
│                   │  Output:                             │                           │
│                   │  - Natural language summary          │                           │
│                   │  - Maintenance recommendations       │                           │
│                   │  - Root cause analysis               │                           │
│                   │  - Spare parts suggestion            │                           │
│                   └──────────────────┬──────────────────┘                           │
│                                      │                                              │
└──────────────────────────────────────┼──────────────────────────────────────────────┘
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────────────┐
│                    VISUALIZATION & ALERTING                                          │
│                                      │                                              │
│         ┌────────────────────────────┼────────────────────────────────┐            │
│         │                            │                                │            │
│         ▼                            ▼                                ▼            │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────────────────┐ │
│  │ Power BI        │      │ Azure Monitor   │      │ Mobile App                  │ │
│  │ Dashboards      │      │ Alerts          │      │ (Technician)                │ │
│  │                 │      │                 │      │                             │ │
│  │ - Equipment     │      │ - Critical      │      │ - Work orders               │ │
│  │   health        │      │   failure alert │      │ - Equipment status          │ │
│  │ - Predictions   │      │ - SMS/Email     │      │ - GPT recommendations       │ │
│  │ - Trends        │      │ - Teams         │      │ - AR guidance               │ │
│  └─────────────────┘      └─────────────────┘      └─────────────────────────────┘ │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Sensor Data Schema

```json
{
  "deviceId": "cnc_machine_001",
  "timestamp": "2024-01-15T14:30:00Z",
  "sensors": {
    "vibration_x": 2.34,
    "vibration_y": 1.87,
    "vibration_z": 0.92,
    "temperature": 67.5,
    "spindle_speed": 12000,
    "spindle_load": 45.2,
    "power_consumption": 8.7
  },
  "metadata": {
    "plant": "seattle_plant_1",
    "line": "assembly_line_3",
    "equipment_type": "cnc_5axis"
  }
}
```

---

## ML Model Performance

| Model | Use Case | Metric | Value |
|-------|----------|--------|-------|
| RUL Prediction | Days to failure | MAE | 3.2 days |
| Anomaly Detection | Unusual patterns | F1 Score | 0.94 |
| Failure Classification | Failure type | Accuracy | 91% |

---

## Azure Services Used

| Service | Purpose |
|---------|---------|
| IoT Hub | Device connectivity, messaging |
| IoT Edge | Edge processing, local ML |
| Event Hub | High-throughput streaming |
| Stream Analytics | Real-time processing |
| ADLS Gen2 | Time-series data lake |
| Azure ML | Model training, deployment |
| Azure OpenAI | Natural language insights |
| Power BI | Operational dashboards |
| Azure Monitor | Alerting |

---

## Interview Talking Points

1. **Edge vs Cloud processing:**
   - Edge: Latency-sensitive anomaly detection
   - Cloud: Complex ML predictions
   - Store-and-forward for connectivity issues

2. **Why LSTM for RUL?**
   - Captures temporal dependencies
   - Handles variable-length sequences
   - Good for degradation patterns

3. **Feature engineering for vibration:**
   - FFT for frequency domain features
   - Rolling statistics (mean, std, peak)
   - Rate of change trends
