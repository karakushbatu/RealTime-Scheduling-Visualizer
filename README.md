# ⏱️ Real-Time Scheduling Simulator (ITU RTSS Project)

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Completed-success.svg)
![University](https://img.shields.io/badge/University-ITU-red.svg)

A comprehensive simulation tool developed for the **Real-Time Systems Software** course at **Istanbul Technical University (İTÜ)**. This application visualizes various real-time scheduling algorithms on both **Single-core** and **Multi-core** architectures with a modern, dark-themed GUI.

## 🚀 Features

* **Multi-Core Support:** Simulates global scheduling logic on 1 to 4 processor cores.
* **Advanced Scheduling Algorithms:**
    * **Static Priority:** Rate Monotonic (RM), Deadline Monotonic (DM).
    * **Dynamic Priority:** Earliest Deadline First (EDF).
    * **Server Mechanisms:** Poller, Deferrable Server, Sporadic Server.
    * **Analysis Mode:** RM Baseline (Capacity Check).
* **Interactive Visualization:**
    * **Smart Gantt Chart:** Automatically switches between Task-Centric (Single-core) and Core-Centric (Multi-core) views.
    * **Tooltips:** Hover over blocks to see detailed job information (Start, End, Status).
    * **Clean UI:** Modern "Flat Design" interface with a dark theme.
* **Real-Time Analytics:**
    * **Dynamic Utilization ($U$):** Real-time system load calculation based on core count.
    * **Fault Detection:** Visualizes Deadline Misses in **RED** and warns about system overload.
* **Reporting:**
    * **One-Click Export:** Saves high-resolution **PNG** charts and detailed **TXT** analysis reports.
* **Tools:**
    * **Random Task Generator:** Built-in tool to generate random task sets for stress testing.

## 📂 Input File Format

The simulator accepts `.txt` files defining the task set. The format is space-separated. Lines starting with `#` are ignored as comments.

| Code | Type | Format | Description |
| :---: | :--- | :--- | :--- |
| **P** | Periodic | `P r e p d` | **r**: Release, **e**: Execution, **p**: Period, **d**: Deadline |
| **D** | Deadline | `D e p d` | Periodic task where `r=0` is implicit. |
| **S** | Server | `S e p` | **e**: Capacity (Budget), **p**: Replenishment Period |
| **A** | Aperiodic | `A r e` | **r**: Arrival Time, **e**: Execution Time |

> **Note:** If `d` is omitted for Periodic tasks, it defaults to `d=p` (Implicit Deadline).

### Example `input.txt`
```text
# High Priority Periodic Task (r=0, e=10, p=50, d=50)
P 0 10 50 50

# Server Task (Capacity=5, Period=50)
S 5 50

# Aperiodic Job (Arrives at t=12, Exec=2)
A 12 2
```
##🛠️ Installation & Usage

### Method 1: Running from Source (Recommended)

Ensure you have Python 3.x installed.

#### 1.Clone the repository:
```
git clone [https://github.com/YOUR_USERNAME/ITU-RTSS-Scheduler-Sim.git](https://github.com/YOUR_USERNAME/ITU-RTSS-Scheduler-Sim.git)
cd ITU-RTSS-Scheduler-Sim
```
#### 2.Install dependencies:  
```
pip install matplotlib
```
(Note: tkinter usually comes pre-installed with Python. If not, install python-tk)

#### 3.Run the application:
```
python main.py
```
### Method 2: Running Executables

(Optional: If you create releases)

Download RTSS_Simulator.exe (Windows) or RTSS_Simulator.app (macOS) from the Releases page.

##📝 Reporting Module

After a simulation runs, the "💾 Export Report" button becomes active. It generates:

  1.Report_X.txt: Contains simulation logs, miss counts, utilization stats, and input summary.

  2.Report_X.png: A high-quality Gantt chart image.

##👨‍💻 Author

Batuhan Computer Engineering Student @ Istanbul Technical University (İTÜ)
