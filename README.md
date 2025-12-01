# ⏱️ Real-Time Scheduling Simulator (ITU RTSS Project)

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Completed-success.svg)
![University](https://img.shields.io/badge/University-ITU-red.svg)

A comprehensive simulation tool developed for the **Real-Time Systems Software** course at **Istanbul Technical University (İTÜ)**.  
This application visualizes various real-time scheduling algorithms on both **Single-core** and **Multi-core** architectures with a modern GUI.
---

### 🌐 Try It Live! (Web Application)

You can run the full simulator directly in your browser without installing anything.

> **[Click Here to Launch Web App 🚀](https://realtime-scheduling-visualizer-iupupgyeettbgfq5xinukt.streamlit.app/)**

---
## 📥 Download

You can download the ready-to-run application (Windows & macOS) along with the full report from the link below:

[![Download Release](https://img.shields.io/badge/Download-RTSS__Simulator__v1.0.0-blue?style=for-the-badge&logo=github)]([BURAYA_KOPYALADIGIN_RELEASE_LINKINI_YAPISTIR](https://github.com/karakushbatu/RealTime-Scheduling-Visualizer/releases/tag/1.0.0))

**Note:** If the link above doesn't work, please check the [Releases Page](../../releases/latest).

---

## 🚀 Features

- **Multi-Core Support:** Simulates global scheduling on 1–4 processor cores.
- **Advanced Scheduling Algorithms:**
  - **Static Priority:** Rate Monotonic (RM), Deadline Monotonic (DM)
  - **Dynamic Priority:** Earliest Deadline First (EDF)
  - **Server Mechanisms:** Poller, Deferrable Server, Sporadic Server
  - **Analysis Mode:** RM Baseline (Utilization Test)
- **Interactive Visualization:**
  - **Smart Gantt Chart:** Task-centric (1 CPU) or Core-centric (Multi-CPU)
  - **Tooltips:** Job start/end, preemption, completion information
  - **Modern UI:** Dark-themed, flat-design interface
- **Task Creator Studio:**
  - Manual text-based editor
  - Smart random task generator using UUniFast-inspired logic
- **Reporting:**
  - High-resolution **PNG** export
  - Detailed **TXT** simulation reports

---

## 📂 Input File Format

The simulator uses `.txt` files describing task sets.  
Format is **space-separated**.

| Code | Type | Format | Description |
| :---: | :--- | :--- | :--- |
| **P** | Periodic | `P r e p d` | r: Release, e: Execution, p: Period, d: Deadline |
| **D** | Deadline Periodic | `D e p d` | Deadline-based periodic task (r = 0 implicit) |
| **S** | Server | `S e p` | e: Server capacity (budget), p: Replenishment period |
| **A** | Aperiodic Job | `A r e` | r: Arrival time, e: Execution time |

### Example: `input.txt`
```text
# High Priority Periodic Task (r=0, e=10, p=50, d=50)
P 0 10 50 50

# Server Task (Capacity=5, Period=50)
S 5 50

# Aperiodic Job (Arrives at t=12, Exec=2)
A 12 2
```

---

## 🛠️ Installation & Usage

### **Method 1 — Running from Source (Recommended)**

1. **Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/ITU-RTSS-Scheduler-Sim.git
cd ITU-RTSS-Scheduler-Sim
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run**
```bash
python main.py
```

---

### **Method 2 — Running Executables**

- **macOS:** Run `RTSS_Simulator.app` in `Executables/macOS`.
- **Windows:** Run `RTSS_Simulator.exe` in `Executables/Windows`.

---

## 📸 Usage Tips

- **Load/Create:** Use **✨ Create** to edit or randomly generate tasks.
- **Configure:** Select core count (1–4) and an algorithm.
- **Simulate:** Watch the Gantt chart (hover for job details).
- **Export:** Save PNG charts and TXT analysis reports.

---

## 👨‍💻 Author

**Batuhan Karakuş**  
Computer Engineering Student @ Istanbul Technical University (İTÜ)

This project is based on concepts from **“Real-Time Systems” — Jane W. S. Liu**.

---

# 📂 Test Cases (Professional Scenarios)

Place these files under the `Test_Cases/` directory.

---

## **1️⃣ RM vs EDF — `1_RM_vs_EDF.txt`**

**Purpose:**  
RM fails due to utilization > RM bound (≈83%), EDF succeeds (can handle 100%).

```text
# RM vs EDF Comparison
# Total Utilization: 0.5 + 0.375 = 87.5%
# RM bound for n=2 is ~83%, so RM may fail.
# EDF succeeds.

P 0 25 50 50
P 0 30 80 80
```

---

## **2️⃣ Poller vs Deferrable Server — `2_Server_Mechanisms.txt`**

**Purpose:**  
Show that Poller burns budget at t=0, while Deferrable Server preserves it.

```text
# Server Mechanisms Test
# Aperiodic task arrives at t=20.
# Poller will miss it.
# Deferrable Server will serve it immediately.

S 10 50
P 0 20 100 100
A 20 5
```

---

## **3️⃣ Multicore Stress — `3_Multicore_Stress.txt`**

**Purpose:**  
1 core overloaded (~240%).  
4 cores handle tasks with ease.

```text
# Multicore Load Balancing Test
# Total Load: ~240%
# 1 Core: OVERLOAD
# 4 Cores: SAFE

P 0 40 50 50
P 0 30 50 50
P 0 60 100 100
P 0 50 100 100
P 0 20 40 40
```

---

## **4️⃣ Sporadic Server Replenishment — `4_Sporadic_Server_Complex.txt`**

**Purpose:**  
Frequent aperiodic bursts; test dynamic replenishment.

```text
# Sporadic Server Complex Replenishment
# High priority server with frequent aperiodic arrivals

S 5 20
P 0 10 40 40
A 2 2
A 8 2
A 25 3
```

---

## **5️⃣ Deadline Monotonic Advantage — `5_Deadline_Monotonic.txt`**

**Purpose:**  
RM fails because priorities depend on period only.  
DM succeeds by using deadlines.

```text
# Deadline Monotonic Test
# T1: Long period (100), short deadline (20)
# T2: Shorter period (50), longer deadline (50)

D 10 100 20
D 20 50 50
```

---

## 🧩 Closing Notes

These test cases demonstrate the simulator’s capability across:

- Fixed vs dynamic priority scheduling  
- Server mechanisms  
- Aperiodic handling  
- Multi-core load balancing  
- Deadline-based priority assignment
