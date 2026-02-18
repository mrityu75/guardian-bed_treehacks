# Guardian Bed

**AI-Powered Continuous Patient Monitoring System**

Guardian Bed is a full-stack healthcare system that transforms patient care from **reactive monitoring → proactive intervention**. By integrating multimodal sensors, AI models, and secure infrastructure, the system continuously tracks patient conditions across both hospital and home environments.

---

## Overview

Healthcare systems today rely on **intermittent monitoring**, leaving critical gaps where complications go undetected.

Guardian Bed solves this by enabling:

* Continuous real-time monitoring
* Intelligent patient prioritization
* Early detection of deterioration
* Prevention of pressure ulcers and hospital readmissions

---

## Key Features

### Multimodal Monitoring

* Pressure mat (ulcer risk detection)
* Wearable wristband (HR, HRV, motion)
* Temperature sensors (inflammation detection)
* mmWave radar (contactless movement & breathing)
* Voice AI agent (clinical conversation tracking)

---

### Intelligent Prioritization

The system computes a unified risk score:

```math
R_{\text{total}} = \alpha R_{\text{ulcer}} + \beta R_{\text{health}}
```

Where:

```math
R_{\text{ulcer}} = f(\text{pressure}, \text{time}, \text{temperature})
```

```math
R_{\text{health}} = f(\text{HR}, \text{HRV}, \text{movement}, \text{temperature})
```

Patients are ranked in real-time:

```math
\text{Priority Score} = (1 - R_{\text{total}}) + \text{Immobility} + \text{Urgency}
```

---

### Voice AI Clinical Agent

* Converts speech → structured notes
* Tracks medication timing and symptoms
* Enables cross-shift communication for nurses

---

### Continuous Monitoring Beyond Hospital

* Deployable in both hospital and home
* Supports critical **30-day post-surgery recovery window**
* Reduces preventable readmissions

---

### Quantum-Safe Security

```math
\text{Secure System} = \text{BB84} + \text{Kyber-768}
```

Ensures future-proof protection against quantum attacks.

---

## System Architecture

```
Sensors (Pressure + Wearable + Radar + Audio)
        ↓
Data Pipeline (Real-time Streaming @ 10Hz)
        ↓
AI Models (Risk Scoring + Classification + NLP)
        ↓
Backend (FastAPI + Processing Layer)
        ↓
Dashboard + Alerts + Reports
```

---

## Tech Stack

### Hardware

* ESP32 microcontrollers
* FSR pressure sensors
* MPU6050 accelerometer
* MAX30102 (HR, HRV)
* MAX30205 (temperature)
* mmWave radar
* Microphones

---

### Software

* Python (data processing, ML)
* FastAPI (backend)
* SMTP (alerts & reporting)

---

### AI / ML

* Classification models for:

  * ulcer risk
  * patient deterioration
* Few-shot learning (speech summarization)
* Reinforcement learning (report generation)

---

### Algorithms

* Segment Tree (efficient time-series queries)
* Longest Common Subsequence (LCS) for:

  * consistency verification
  * redundancy removal

---

### Security

* BB84 quantum key distribution
* Kyber-768 post-quantum encryption

---

## Impact

Guardian Bed addresses three major healthcare problems:

### 1. Post-Surgery Complications

```math
\text{Early Detection} \rightarrow \text{Timely Intervention} \rightarrow \text{Better Outcomes}
```

---

### 2. Hospital Readmissions

```math
\text{Continuous Monitoring} \rightarrow \text{Fewer Readmissions}
```

* Targets preventable readmissions (~27–40%)
* Reduces $50B+ annual burden

---

### 3. Pressure Ulcers

```math
\text{Pressure + Time + Temperature} \rightarrow \text{Ulcer Risk}
```

* Detects prolonged pressure early
* Prevents tissue damage

---

## What Makes Guardian Bed Different

| Feature        | Existing Systems | Guardian Bed      |
| -------------- | ---------------- | ----------------- |
| Monitoring     | Intermittent     | Continuous (24/7) |
| Scope          | Hospital only    | Hospital + Home   |
| Data           | Fragmented       | Multimodal fusion |
| Prioritization | Manual           | AI-driven         |
| Detection      | Reactive         | Predictive        |
| Communication  | Manual           | Voice AI          |
| Security       | Standard         | Quantum-safe      |

---

## Future Work

* Train models on real clinical datasets
* Deploy pilot in hospitals
* Build digital twin patient system
* Improve personalized risk modeling
* Scale home monitoring infrastructure

---

## Team

* **Quynh Anh Nguyen** — AI, ML, Quantum Security
* **Aditya Garg** — Hardware & Sensor Systems
* **Jay** — Backend, Frontend, Prioritization Systems

---

## Vision

> A future where no critical signal is missed—and every patient is continuously protected.

---

## License

MIT License

---

## Acknowledgments

Built for healthcare innovation and patient safety.


