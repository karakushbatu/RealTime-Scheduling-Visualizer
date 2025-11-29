import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import random
import os
import math
import copy
from datetime import datetime

# =============================================================================
# 1. DATA STRUCTURES (MODEL)
# =============================================================================

class Task:
    def __init__(self, task_type, args, original_char):
        self.task_type = task_type
        self.original_char = original_char 
        self.id = 0 
        self.color = "" 
        
        self.arrival_time = 0 
        self.burst_time = 0    
        self.period = 0        
        self.deadline = 0      
        self.relative_deadline = 0 
        
        self.server_capacity = 0
        self.current_budget = 0
        
        self.parse_args(args)

    def parse_args(self, args):
        n = len(args)
        if self.task_type == 'P':
            if self.original_char == 'P':
                if n == 4: self.arrival_time, self.burst_time, self.period, self.deadline = args
                elif n == 3: self.arrival_time, self.burst_time, self.period = args; self.deadline = self.period
                elif n == 2: self.arrival_time = 0; self.burst_time, self.period = args; self.deadline = self.period
            elif self.original_char == 'D':
                if n == 3: self.arrival_time = 0; self.burst_time, self.period, self.deadline = args
                elif n == 4: self.arrival_time, self.burst_time, self.period, self.deadline = args
            self.relative_deadline = self.deadline 

        elif self.task_type == 'S': 
            self.arrival_time = 0
            self.burst_time = args[0]
            self.period = args[1]
            self.deadline = args[1] 
            self.relative_deadline = self.period
            self.server_capacity = self.burst_time
            self.current_budget = self.burst_time 
            
        elif self.task_type == 'A': 
            if n >= 2: 
                self.arrival_time = args[0]
                self.burst_time = args[1]
                self.period = 0 
                self.deadline = 99999 
                self.relative_deadline = 99999

    def __repr__(self):
        return f"T{self.id}"

# =============================================================================
# 2. LOGIC & SIMULATION
# =============================================================================

def calculate_lcm(tasks):
    periods = [t.period for t in tasks if t.period > 0]
    if not periods: return 100
    lcm = periods[0]
    for p in periods[1:]:
        lcm = abs(lcm * p) // math.gcd(lcm, p)
    return min(lcm, 2000) 

def calculate_utilization(tasks):
    u = 0.0
    for t in tasks:
        if t.task_type in ['P', 'S'] and t.period > 0:
            u += t.burst_time / t.period
    return u

def parse_file(filepath):
    tasks = []
    task_counter = 1
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                parts = line.split()
                if not parts: continue
                
                char_code = parts[0]
                clean_args = []
                for p in parts[1:]:
                    if p.startswith('('): break 
                    try: clean_args.append(int(p))
                    except ValueError: continue
                
                if clean_args:
                    t_type = 'P'
                    if char_code == 'A': t_type = 'A'
                    elif char_code == 'S': t_type = 'S'
                    elif char_code == 'D': t_type = 'P'
                    
                    new_task = Task(t_type, clean_args, char_code)
                    new_task.id = task_counter
                    if t_type == 'S': new_task.color = '#a6e3a1' 
                    elif t_type == 'A': new_task.color = '#fab387' 
                    else: new_task.color = '#89b4fa' 
                    tasks.append(new_task)
                    task_counter += 1
        return tasks
    except Exception as e:
        messagebox.showerror("Error", f"File Error: {e}")
        return []

def generate_random_tasks(num_tasks, target_util):
    tasks = []
    utils = [target_util / num_tasks] * num_tasks
    
    for i, u in enumerate(utils):
        period = random.choice([20, 40, 50, 60, 80, 100])
        exec_time = max(1, int(period * u))
        if exec_time >= period: exec_time = period - 1
        
        if i == num_tasks - 1:
            t = Task('A', [random.randint(0, period), exec_time], 'A')
            t.color = '#fab387'
        else:
            t = Task('P', [0, exec_time, period], 'P')
            t.color = '#89b4fa'
        
        t.id = i + 1
        tasks.append(t)
    return tasks

def run_simulation(tasks, algorithm, num_cores):
    periodic_tasks = [t for t in tasks if t.task_type == 'P']
    server_task = next((t for t in tasks if t.task_type == 'S'), None)
    aperiodic_tasks = [t for t in tasks if t.task_type == 'A']
    
    if algorithm in ["Poller", "Deferrable Server", "Sporadic Server"] and not server_task:
        messagebox.showwarning("Config Error", f"{algorithm} requires a Server (S) task!")
        return [], 0, {}

    active_periodic = periodic_tasks[:]
    if server_task and algorithm != "Background":
        active_periodic.append(server_task)

    lcm = calculate_lcm(active_periodic) if active_periodic else 100
    
    schedule_log = [] 
    ready_queue = []    
    aperiodic_queue = [] 
    sporadic_replenishments = []
    
    aperiodic_tasks.sort(key=lambda x: x.arrival_time)
    ap_index = 0
    stats = {'total_jobs': 0, 'missed_deadlines': 0, 'aperiodic_done': 0}

    for t in range(lcm):
        # 1. ARRIVALS
        for task in active_periodic:
            if t >= task.arrival_time and (t - task.arrival_time) % task.period == 0:
                abs_deadline = t + task.deadline
                new_job = {'task': task, 'remaining': task.burst_time, 'abs_deadline': abs_deadline}
                stats['total_jobs'] += 1
                
                if task == server_task:
                    if algorithm == "Deferrable Server":
                        task.current_budget = task.server_capacity
                        ready_queue = [j for j in ready_queue if j['task'] != server_task]
                        new_job['remaining'] = task.current_budget
                        ready_queue.append(new_job)
                    elif algorithm == "Sporadic Server":
                        if task.current_budget > 0:
                            new_job['remaining'] = task.current_budget
                            ready_queue = [j for j in ready_queue if j['task'] != server_task]
                            ready_queue.append(new_job)
                    else:
                        ready_queue.append(new_job)
                else:
                    ready_queue.append(new_job)

        # 2. SPORADIC
        if algorithm == "Sporadic Server" and server_task:
            while sporadic_replenishments and sporadic_replenishments[0][0] <= t:
                rep_time, amount = sporadic_replenishments.pop(0)
                server_task.current_budget = min(server_task.server_capacity, server_task.current_budget + amount)
                server_in_queue = any(j['task'] == server_task for j in ready_queue)
                if not server_in_queue and server_task.current_budget > 0:
                    ready_queue.append({'task': server_task, 'remaining': server_task.current_budget, 'abs_deadline': t + server_task.period})
                elif server_in_queue:
                    for j in ready_queue:
                        if j['task'] == server_task: j['remaining'] = server_task.current_budget

        # 3. APERIODIC
        while ap_index < len(aperiodic_tasks) and aperiodic_tasks[ap_index].arrival_time == t:
            aperiodic_queue.append({'task': aperiodic_tasks[ap_index], 'remaining': aperiodic_tasks[ap_index].burst_time, 'abs_deadline': 99999})
            ap_index += 1

        # 4. POLLER
        if algorithm == "Poller" and server_task:
             for job in ready_queue:
                 if job['task'] == server_task:
                     if not aperiodic_queue: job['remaining'] = 0 
                     break

        # 5. SORTING
        ready_queue = [j for j in ready_queue if j['remaining'] > 0]
        if algorithm == "Earliest Deadline First (EDF)":
            ready_queue.sort(key=lambda x: (x['abs_deadline'], x['task'].id))
        elif algorithm == "Deadline Monotonic (DM)":
            ready_queue.sort(key=lambda x: (x['task'].relative_deadline, x['task'].id))
        else: 
            ready_queue.sort(key=lambda x: (x['task'].period if x['task'].period > 0 else 9999, x['task'].id))

        # 6. DISPATCHING
        cores_available = num_cores
        job_index = 0
        
        while cores_available > 0 and job_index < len(ready_queue):
            current_job = ready_queue[job_index]
            
            if current_job['task'] == server_task and not aperiodic_queue and algorithm in ["Deferrable Server", "Sporadic Server"]:
                job_index += 1
                continue

            core_id = num_cores - cores_available + 1 
            label = f"T{current_job['task'].id}"
            status = 'OK'
            
            if current_job['task'] == server_task and aperiodic_queue and algorithm != "RM Baseline":
                ap_job = aperiodic_queue[0]
                label = f"T{ap_job['task'].id}" 
                ap_job['remaining'] -= 1
                if ap_job['remaining'] == 0:
                    aperiodic_queue.pop(0)
                    stats['aperiodic_done'] += 1
            elif current_job['task'] == server_task and algorithm != "RM Baseline":
                 label = "" 

            if t >= current_job['abs_deadline']:
                status = 'MISS'
                stats['missed_deadlines'] += 1

            schedule_log.append({
                'core': core_id, 'time': t, 'duration': 1, 
                'label': label, 'status': status, 'task_id': current_job['task'].id
            })
            
            current_job['remaining'] -= 1
            
            if algorithm == "Sporadic Server" and current_job['task'] == server_task:
                server_task.current_budget -= 1
                sporadic_replenishments.append((t + server_task.period, 1))
            
            if current_job['remaining'] == 0:
                ready_queue.pop(job_index)
            else:
                job_index += 1
            cores_available -= 1

        while cores_available > 0 and algorithm == "Background" and aperiodic_queue:
            core_id = num_cores - cores_available + 1
            ap_job = aperiodic_queue[0]
            schedule_log.append({
                'core': core_id, 'time': t, 'duration': 1, 
                'label': f"T{ap_job['task'].id}", 'status': 'OK', 'task_id': ap_job['task'].id
            })
            ap_job['remaining'] -= 1
            if ap_job['remaining'] == 0:
                aperiodic_queue.pop(0)
                stats['aperiodic_done'] += 1
            cores_available -= 1

    return schedule_log, lcm, stats

# =============================================================================
# 3. ADVANCED EXPORT
# =============================================================================

def get_algo_short_name(algo_long):
    if "Rate Monotonic" in algo_long: return "RM"
    if "Deadline" in algo_long: return "DM"
    if "Earliest" in algo_long: return "EDF"
    if "Background" in algo_long: return "BG"
    if "Poller" in algo_long: return "Poll"
    if "Deferrable" in algo_long: return "DS"
    if "Sporadic" in algo_long: return "SS"
    return "Algo"

def export_results(figure, schedule, stats, algorithm, tasks, num_cores, input_filename):
    if not schedule: return
    
    # 1. Smart Default Filename Logic
    # Format: {InputFile}_{AlgoShort}_{Cores}C_{Time}
    algo_short = get_algo_short_name(algorithm)
    clean_filename = input_filename.replace(".txt", "")
    timestamp = datetime.now().strftime("%H%M")
    
    initial_name = f"{clean_filename}_{algo_short}_{num_cores}Core_{timestamp}"
    
    file_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        initialfile=initial_name,
        filetypes=[("Text Report", "*.txt")],
        title="Save Analysis Results"
    )
    
    if not file_path: return 
    
    txt_path = file_path
    png_path = file_path.replace(".txt", ".png")
    
    # 2. Save Image
    figure.savefig(png_path, dpi=150, bbox_inches='tight')
    
    # 3. Save Text Report
    u = calculate_utilization(tasks)
    
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("===================================================\n")
        f.write("       REAL-TIME SCHEDULING SIMULATION REPORT      \n")
        f.write("===================================================\n")
        f.write(f"Source File    : {input_filename}\n")
        f.write(f"Date Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Algorithm      : {algorithm}\n")
        f.write(f"Configuration  : {num_cores} Core(s)\n")
        f.write(f"System Load (U): {u*100:.1f}%\n")
        f.write("===================================================\n\n")
        
        f.write("-------------------- TASK SET ---------------------\n")
        f.write(f"{'ID':<6} {'Type':<10} {'Exec(C)':<10} {'Period(P)':<10} {'Deadline(D)':<10}\n")
        f.write("-" * 50 + "\n")
        for t in tasks:
            t_type_full = "Periodic" if t.task_type=='P' else "Server" if t.task_type=='S' else "Aperiodic"
            f.write(f"T{t.id:<5} {t_type_full:<10} {t.burst_time:<10} {t.period:<10} {t.deadline:<10}\n")
        f.write("-" * 50 + "\n\n")
        
        f.write("------------------- STATISTICS --------------------\n")
        f.write(f"Total Simulation Duration  : {len(schedule) // num_cores} ms (approx)\n") 
        f.write(f"Total Job Instances        : {stats['total_jobs']}\n")
        f.write(f"Aperiodic Jobs Completed   : {stats['aperiodic_done']}\n")
        f.write(f"Deadline Misses            : {stats['missed_deadlines']}\n")
        if stats['missed_deadlines'] > 0:
            f.write("STATUS                     : FAILURE (System Overloaded)\n")
        else:
            f.write("STATUS                     : SUCCESS\n")
        f.write("\n")
        
        f.write("----------------- EXECUTION LOG -------------------\n")
        f.write(f"{'Core':<6} | {'Start':<8} | {'End':<8} | {'Task':<8} | {'Status'}\n")
        f.write("-" * 55 + "\n")
        
        merged = []
        temp_sched = sorted(schedule, key=lambda x: (x['core'], x['time']))
        for item in temp_sched:
            if not merged: merged.append(item.copy()); continue
            last = merged[-1]
            if (last['core'] == item['core'] and last['task_id'] == item['task_id'] and 
                last['status'] == item['status'] and last['label'] == item['label'] and
                last['time'] + last['duration'] == item['time']):
                last['duration'] += 1
            else: merged.append(item.copy())
            
        for m in merged:
            start = m['time']
            end = start + m['duration']
            lbl = m['label'] if m['label'] else f"T{m['task_id']}"
            f.write(f"{m['core']:<6} | {start:<8} | {end:<8} | {lbl:<8} | {m['status']}\n")
            
    messagebox.showinfo("Export Successful", f"Report saved successfully!\n\n📄 Text: {os.path.basename(txt_path)}\n🖼️ Image: {os.path.basename(png_path)}")

def draw_gantt(raw_schedule, tasks, simulation_time, num_cores, algorithm):
    merged_schedule = []
    raw_schedule.sort(key=lambda x: (x['core'], x['time']))
    
    for item in raw_schedule:
        if not merged_schedule:
            merged_schedule.append(item)
            continue
        last = merged_schedule[-1]
        if (last['core'] == item['core'] and last['task_id'] == item['task_id'] and 
            last['status'] == item['status'] and last['label'] == item['label'] and
            last['time'] + last['duration'] == item['time']):
            last['duration'] += 1 
        else:
            merged_schedule.append(item) 

    is_single_core = (num_cores == 1)
    
    if is_single_core:
        fig_height = len(tasks) * 0.8 + 2
        y_label = "Tasks"
        y_limit = 10 * (len(tasks) + 1)
    else:
        fig_height = num_cores * 1.5 + 2
        y_label = "Processors (Cores)"
        y_limit = 10 * (num_cores + 1)

    fig, gnt = plt.subplots(figsize=(14, fig_height))
    gnt.set_ylim(0, y_limit)
    gnt.set_xlim(0, simulation_time)
    gnt.set_xlabel('Time (ms)', fontsize=12)
    gnt.set_ylabel(y_label, fontsize=12)
    gnt.grid(True, which='both', axis='x', linestyle='--', alpha=0.5)

    yticks = []
    yticklabels = []
    if is_single_core:
        tasks.sort(key=lambda x: x.id)
        for i, task in enumerate(tasks):
            y_pos = 10 * (i + 1)
            yticks.append(y_pos)
            info = f"P:{task.period}" if task.task_type=='P' else "S" if task.task_type=='S' else "A"
            yticklabels.append(f"T{task.id} ({info})")
    else:
        for i in range(1, num_cores + 1):
            y_pos = 10 * i
            yticks.append(y_pos)
            yticklabels.append(f"Core {i}")

    gnt.set_yticks(yticks)
    gnt.set_yticklabels(yticklabels, fontsize=10)

    bar_patches = [] 
    
    for job in merged_schedule:
        task = next((t for t in tasks if t.id == job['task_id']), None)
        color = task.color if task else 'gray'
        if job['status'] == 'MISS': color = '#f38ba8' 
        
        y_pos = 10 * (next((i for i, t in enumerate(tasks) if t.id == job['task_id']), 0) + 1) if is_single_core else 10 * job['core']

        gnt.broken_barh([(job['time'], job['duration'])], (y_pos - 4, 8), facecolors=color, edgecolors='black', linewidth=0.5)
        
        bbox = [job['time'], y_pos - 4, job['time'] + job['duration'], y_pos + 4] 
        info = f"Task: {job['label']}\nStart: {job['time']}\nDur: {job['duration']}\nStatus: {job['status']}"
        bar_patches.append((bbox, info))

        if job['label'] and job['duration'] > 1:
            plt.text(job['time'] + job['duration']/2, y_pos, job['label'], 
                     ha='center', va='center', color='white', fontsize=8, fontweight='bold')

    patches = [
        mpatches.Patch(color='#89b4fa', label='Periodic Task'),
        mpatches.Patch(color='#a6e3a1', label='Server Task'),
        mpatches.Patch(color='#fab387', label='Aperiodic Job'),
        mpatches.Patch(color='#f38ba8', label='Deadline Miss')
    ]
    plt.legend(handles=patches, loc='upper right', frameon=True, fancybox=True, shadow=True)
    plt.title(f"{algorithm} - {('Task View' if is_single_core else 'Core View')}", fontsize=14, fontweight='bold')
    
    annot = gnt.annotate("", xy=(0,0), xytext=(20,20),textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="#313244", ec="black", alpha=0.9),
                        arrowprops=dict(arrowstyle="->", color="black"))
    annot.set_visible(False)
    annot.set_color("white")

    def hover(event):
        vis = annot.get_visible()
        if event.inaxes == gnt:
            found = False
            for bbox, text in bar_patches:
                if bbox[0] <= event.xdata <= bbox[2] and bbox[1] <= event.ydata <= bbox[3]:
                    annot.xy = (event.xdata, event.ydata)
                    annot.set_text(text)
                    annot.set_visible(True)
                    fig.canvas.draw_idle()
                    found = True
                    break
            if not found and vis:
                annot.set_visible(False)
                fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", hover)
    plt.tight_layout()
    return fig

# =============================================================================
# 4. UI (MODERN FLAT DESIGN V2)
# =============================================================================

def main_app():
    root = tk.Tk()
    root.title("RTSS Simulator - ITU Gold")
    root.geometry("700x820")
    
    BG_COLOR = "#1e1e2e"       
    CARD_BG = "#313244"        
    TEXT_COLOR = "#cdd6f4"     
    ACCENT_BLUE = "#89b4fa"    
    ACCENT_GREEN = "#a6e3a1"   
    ACCENT_RED = "#f38ba8"     
    ACCENT_ORANGE = "#fab387"  
    
    root.configure(bg=BG_COLOR)
    
    style = ttk.Style()
    style.theme_use('clam')
    
    style.configure("TFrame", background=BG_COLOR)
    style.configure("Card.TFrame", background=CARD_BG, relief="flat", borderwidth=0)
    
    style.configure("TLabel", background=CARD_BG, foreground=TEXT_COLOR, font=("Helvetica Neue", 11))
    style.configure("Header.TLabel", background=BG_COLOR, foreground=ACCENT_BLUE, font=("Helvetica Neue", 22, "bold"))
    
    # Modern Button (Fixed Disabled Color)
    style.configure("Action.TButton", 
                    background=ACCENT_BLUE, 
                    foreground="#11111b", 
                    font=("Helvetica Neue", 11, "bold"), 
                    borderwidth=0)
    style.map("Action.TButton", 
              background=[('active', "#b4befe"), ('disabled', '#45475a')],
              foreground=[('disabled', '#a6adc8')])
    
    style.configure("TCombobox", fieldbackground="#45475a", background=ACCENT_BLUE, foreground="white", arrowcolor="#11111b", borderwidth=0)
    style.map('TCombobox', fieldbackground=[('readonly', '#45475a')], selectbackground=[('readonly', '#45475a')], selectforeground=[('readonly', 'white')])

    style.configure("TSpinbox", fieldbackground="#45475a", background=ACCENT_BLUE, foreground="white", arrowcolor="#11111b")

    main_frame = ttk.Frame(root, padding="30")
    main_frame.pack(expand=True, fill="both")
    
    ttk.Label(main_frame, text="Real-Time Scheduling Simulator", style="Header.TLabel").pack(pady=(0, 25))
    
    # Global Store
    data_store = {
        "tasks": [], 
        "last_run_stats": None, 
        "last_schedule": None, 
        "last_fig": None, 
        "last_algo": "",
        "filename": "Unknown" # <--- NEW: Stores filename
    }

    # ------------------ CARD 1: INPUT ------------------
    card_input = ttk.Frame(main_frame, style="Card.TFrame", padding="20")
    card_input.pack(fill="x", pady=(0, 20))
    
    ttk.Label(card_input, text="1. System Input", font=("Helvetica Neue", 12, "bold"), foreground=ACCENT_ORANGE).pack(anchor="w", pady=(0, 15))
    
    row1 = ttk.Frame(card_input, style="Card.TFrame")
    row1.pack(fill="x")
    
    file_status_lbl = ttk.Label(row1, text="No file loaded", foreground="#6c7086", font=("Helvetica Neue", 10, "italic"))
    file_status_lbl.pack(side="left", fill="x", expand=True)
    
    def update_status_bar():
        if not data_store["tasks"]: return
        num_cores = int(core_spin.get())
        raw_u = calculate_utilization(data_store["tasks"])
        total_capacity = num_cores * 1.0
        load_pct = raw_u * 100
        capacity_pct = total_capacity * 100
        
        is_overload = raw_u > total_capacity
        status_text = f"System Load: {load_pct:.1f}% (Capacity: {capacity_pct:.0f}%)"
        
        if is_overload:
            util_bar.config(text=f"⚠️ {status_text} - OVERLOAD", background=ACCENT_RED, foreground="#11111b")
        else:
            util_bar.config(text=f"✅ {status_text} - SAFE", background=ACCENT_GREEN, foreground="#11111b")

    def load_file():
        fp = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if fp:
            tasks = parse_file(fp)
            if tasks:
                data_store["tasks"] = tasks
                filename = fp.split('/')[-1]
                data_store["filename"] = filename
                file_status_lbl.config(text=f"Loaded: {filename} ({len(tasks)} tasks)", foreground=ACCENT_GREEN)
                update_status_bar()
                btn_export.config(state="disabled")
            else:
                messagebox.showerror("Error", "Invalid file!")

    def generate_random():
        num = simpledialog.askinteger("Random", "Number of Tasks:", initialvalue=5, minvalue=1, maxvalue=20)
        if not num: return
        util = simpledialog.askfloat("Random", "Target Utilization (0.1 - 4.0):", initialvalue=0.8, minvalue=0.1, maxvalue=4.0)
        if not util: return
        
        tasks = generate_random_tasks(num, util)
        data_store["tasks"] = tasks
        data_store["filename"] = "Random_Generated"
        file_status_lbl.config(text=f"Generated: Random Set ({len(tasks)} tasks)", foreground=ACCENT_BLUE)
        update_status_bar()
        btn_export.config(state="disabled")

    btn_load = ttk.Button(row1, text="📂 Load File", style="Action.TButton", command=load_file)
    btn_load.pack(side="right", padx=5)
    
    btn_rand = ttk.Button(row1, text="🎲 Random", style="Action.TButton", command=generate_random)
    btn_rand.pack(side="right", padx=5)

    # ------------------ CARD 2: CONFIGURATION ------------------
    card_config = ttk.Frame(main_frame, style="Card.TFrame", padding="20")
    card_config.pack(fill="x", pady=(0, 20))
    
    ttk.Label(card_config, text="2. Configuration", font=("Helvetica Neue", 12, "bold"), foreground=ACCENT_ORANGE).pack(anchor="w", pady=(0, 15))
    
    grid_frame = ttk.Frame(card_config, style="Card.TFrame")
    grid_frame.pack(fill="x")
    
    ttk.Label(grid_frame, text="CPU Cores:").grid(row=0, column=0, sticky="w", pady=5)
    
    def on_core_change():
        update_status_bar()

    core_var = tk.StringVar(value="1")
    core_spin = tk.Spinbox(grid_frame, from_=1, to=4, width=5, font=("Helvetica Neue", 11), 
                           textvariable=core_var, command=on_core_change, state="readonly")
    core_spin.grid(row=0, column=1, sticky="w", padx=(10, 30))
    
    ttk.Label(grid_frame, text="Algorithm:").grid(row=0, column=2, sticky="w", pady=5)
    algos = ["Rate Monotonic (RM)", "Deadline Monotonic (DM)", "Earliest Deadline First (EDF)", 
             "Background", "Poller", "Deferrable Server", "Sporadic Server", "RM Baseline"]
    algo_combo = ttk.Combobox(grid_frame, values=algos, state="readonly", font=("Helvetica Neue", 11), width=25)
    algo_combo.current(0)
    algo_combo.grid(row=0, column=3, sticky="w", padx=10)

    # ------------------ STATUS BAR ------------------
    status_frame = ttk.Frame(main_frame, style="TFrame", padding=(0, 10))
    status_frame.pack(fill="x")
    util_bar = ttk.Label(status_frame, text="System Load: 0.0% (Waiting)", font=("Consolas", 11), background="#45475a", foreground=TEXT_COLOR, padding=10)
    util_bar.pack(fill="x")

    # ------------------ ACTIONS ------------------
    action_frame = ttk.Frame(main_frame, style="TFrame")
    action_frame.pack(fill="x", pady=10)

    def run_sim():
        if not data_store["tasks"]:
            messagebox.showwarning("Wait", "Please load or generate tasks first.")
            return
        
        sim_tasks = copy.deepcopy(data_store["tasks"])
        selected_algo = algo_combo.get()
        num_cores = int(core_spin.get())
        
        schedule, duration, stats = run_simulation(sim_tasks, selected_algo, num_cores)
        
        if duration > 0:
            fig = draw_gantt(schedule, sim_tasks, duration, num_cores, selected_algo)
            
            data_store["last_schedule"] = schedule
            data_store["last_stats"] = stats
            data_store["last_fig"] = fig
            data_store["last_algo"] = selected_algo
            
            btn_export.config(state="normal") 
            plt.show()

    def export_data():
        if not data_store["last_schedule"]: return
        num_cores = int(core_spin.get())
        export_results(
            data_store["last_fig"], 
            data_store["last_schedule"], 
            data_store["last_stats"], 
            data_store["last_algo"], 
            data_store["tasks"], 
            num_cores,
            data_store["filename"]
        )

    # Modern Tooltip
    def create_tooltip(widget, text):
        tip = tk.Toplevel(widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry("+0+0")
        tip.withdraw()
        # Dark Theme Tooltip
        label = tk.Label(tip, text=text, background="#313244", foreground="#cdd6f4", 
                         relief="flat", borderwidth=0, font=("Helvetica Neue", 9))
        label.pack(ipadx=5, ipady=3)
        def enter(event):
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 40
            tip.wm_geometry(f"+{x}+{y}")
            tip.deiconify()
        def leave(event):
            tip.withdraw()
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    btn_run = ttk.Button(action_frame, text="▶ START SIMULATION", style="Action.TButton", command=run_sim)
    btn_run.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 10))
    
    btn_export = ttk.Button(action_frame, text="💾 Export Report", style="Action.TButton", command=export_data, state="disabled")
    btn_export.pack(side="right", fill="x", expand=True, ipady=10, padx=(10, 0))
    create_tooltip(btn_export, "Save Chart & Analysis as PNG/TXT")

    # ------------------ LEGEND ------------------
    legend_frame = ttk.Frame(main_frame, style="TFrame")
    legend_frame.pack(side="bottom", fill="x", pady=20)
    
    def add_legend_item(parent, color, text):
        f = ttk.Frame(parent, style="TFrame")
        f.pack(side="left", padx=10)
        lbl_color = tk.Label(f, bg=color, width=2, height=1)
        lbl_color.pack(side="left", padx=(0, 5))
        ttk.Label(f, text=text, font=("Helvetica Neue", 9), background=BG_COLOR).pack(side="left")

    add_legend_item(legend_frame, ACCENT_BLUE, "Periodic")
    add_legend_item(legend_frame, ACCENT_GREEN, "Server")
    add_legend_item(legend_frame, ACCENT_ORANGE, "Aperiodic")
    add_legend_item(legend_frame, ACCENT_RED, "Deadline Miss")

    root.mainloop()

if __name__ == "__main__":
    main_app()