import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, scrolledtext
import matplotlib
matplotlib.use('TkAgg') # KRİTİK: Executable içinde grafik çizimi için şart
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
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

def parse_content(content):
    tasks = []
    task_counter = 1
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'): continue
        parts = line.split()
        if not parts: continue
        
        char_code = parts[0].upper()
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

def parse_file(filepath):
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        return parse_content(content)
    except Exception as e:
        messagebox.showerror("Error", f"File Error: {e}")
        return []

def generate_smart_random_tasks(total_tasks, num_aperiodic, target_util, include_server):
    tasks = []
    current_util_budget = target_util
    server_task = None
    
    if include_server:
        server_util = min(0.2, current_util_budget * 0.25)
        current_util_budget -= server_util
        s_period = random.choice([20, 40, 50])
        s_cap = max(1, int(s_period * server_util))
        server_task = Task('S', [s_cap, s_period], 'S')
        server_task.color = '#a6e3a1'
    
    num_periodic = total_tasks - num_aperiodic
    if include_server: num_periodic -= 1 
    if num_periodic < 0: num_periodic = 0 

    if num_periodic > 0 and current_util_budget > 0:
        points = [0.0] + sorted([random.uniform(0, current_util_budget) for _ in range(num_periodic - 1)]) + [current_util_budget]
        utilizations = [points[i+1] - points[i] for i in range(num_periodic)]
        periods_pool = [20, 40, 50, 60, 80, 100, 200]
        for i in range(num_periodic):
            p = random.choice(periods_pool)
            u = utilizations[i]
            c = max(1, int(p * u))
            if c >= p: c = p - 1
            t = Task('P', [0, c, p, p], 'P')
            t.color = '#89b4fa'
            tasks.append(t)
            
    if server_task: tasks.insert(0, server_task) 

    for i in range(num_aperiodic):
        arrival = random.randint(0, 100)
        exec_time = random.randint(1, 5)
        t = Task('A', [arrival, exec_time], 'A')
        t.color = '#fab387'
        tasks.append(t)
        
    for i, t in enumerate(tasks): t.id = i + 1
    return tasks

def run_simulation(tasks, algorithm, num_cores):
    periodic_tasks = [t for t in tasks if t.task_type == 'P']
    server_task = next((t for t in tasks if t.task_type == 'S'), None)
    aperiodic_tasks = [t for t in tasks if t.task_type == 'A']
    
    if algorithm in ["Poller", "Deferrable Server", "Sporadic Server"] and not server_task:
        messagebox.showwarning("Config Error", f"{algorithm} requires a Server (S) task!\nPlease generate or load a set with a Server.")
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
                    else: ready_queue.append(new_job)
                else: ready_queue.append(new_job)

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

        while ap_index < len(aperiodic_tasks) and aperiodic_tasks[ap_index].arrival_time == t:
            aperiodic_queue.append({'task': aperiodic_tasks[ap_index], 'remaining': aperiodic_tasks[ap_index].burst_time, 'abs_deadline': 99999})
            ap_index += 1

        if algorithm == "Poller" and server_task:
             for job in ready_queue:
                 if job['task'] == server_task:
                     if not aperiodic_queue: job['remaining'] = 0 
                     break

        ready_queue = [j for j in ready_queue if j['remaining'] > 0]
        if algorithm == "Earliest Deadline First (EDF)": ready_queue.sort(key=lambda x: (x['abs_deadline'], x['task'].id))
        elif algorithm == "Deadline Monotonic (DM)": ready_queue.sort(key=lambda x: (x['task'].relative_deadline, x['task'].id))
        else: ready_queue.sort(key=lambda x: (x['task'].period if x['task'].period > 0 else 9999, x['task'].id))

        cores_available = num_cores
        job_index = 0
        while cores_available > 0 and job_index < len(ready_queue):
            current_job = ready_queue[job_index]
            if current_job['task'] == server_task and not aperiodic_queue and algorithm in ["Deferrable Server", "Sporadic Server"]:
                job_index += 1; continue

            core_id = num_cores - cores_available + 1 
            label = f"T{current_job['task'].id}"; status = 'OK'
            
            if current_job['task'] == server_task and aperiodic_queue and algorithm != "RM Baseline":
                ap_job = aperiodic_queue[0]
                label = f"T{ap_job['task'].id}" 
                ap_job['remaining'] -= 1
                if ap_job['remaining'] == 0: aperiodic_queue.pop(0); stats['aperiodic_done'] += 1
            elif current_job['task'] == server_task and algorithm != "RM Baseline": label = "" 

            if t >= current_job['abs_deadline']: status = 'MISS'; stats['missed_deadlines'] += 1

            schedule_log.append({'core': core_id, 'time': t, 'duration': 1, 'label': label, 'status': status, 'task_id': current_job['task'].id})
            current_job['remaining'] -= 1
            
            if algorithm == "Sporadic Server" and current_job['task'] == server_task:
                server_task.current_budget -= 1; sporadic_replenishments.append((t + server_task.period, 1))
            
            if current_job['remaining'] == 0: ready_queue.pop(job_index)
            else: job_index += 1
            cores_available -= 1

        while cores_available > 0 and algorithm == "Background" and aperiodic_queue:
            core_id = num_cores - cores_available + 1
            ap_job = aperiodic_queue[0]
            schedule_log.append({'core': core_id, 'time': t, 'duration': 1, 'label': f"T{ap_job['task'].id}", 'status': 'OK', 'task_id': ap_job['task'].id})
            ap_job['remaining'] -= 1
            if ap_job['remaining'] == 0: aperiodic_queue.pop(0); stats['aperiodic_done'] += 1
            cores_available -= 1

    return schedule_log, lcm, stats

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
    algo_short = get_algo_short_name(algorithm)
    clean_filename = input_filename.replace(".txt", "")
    timestamp = datetime.now().strftime("%H%M")
    initial_name = f"{clean_filename}_{algo_short}_{num_cores}Core_{timestamp}"
    
    file_path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=initial_name, filetypes=[("Text Report", "*.txt")], title="Save Analysis Results")
    if not file_path: return 
    
    txt_path = file_path
    png_path = file_path.replace(".txt", ".png")
    figure.savefig(png_path, dpi=150, bbox_inches='tight')
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
        f.write(f"Deadline Misses: {stats['missed_deadlines']}\n")
        f.write("-" * 40 + "\n")
        for t in tasks:
            f.write(f"T{t.id}: Type={t.task_type}, C={t.burst_time}, P={t.period}, D={t.deadline}\n")
            
    messagebox.showinfo("Export Successful", f"Saved:\n{os.path.basename(txt_path)}")

def draw_gantt(raw_schedule, tasks, simulation_time, num_cores, algorithm):
    merged_schedule = []
    raw_schedule.sort(key=lambda x: (x['core'], x['time']))
    for item in raw_schedule:
        if not merged_schedule: merged_schedule.append(item); continue
        last = merged_schedule[-1]
        if (last['core'] == item['core'] and last['task_id'] == item['task_id'] and last['status'] == item['status'] and last['label'] == item['label'] and last['time'] + last['duration'] == item['time']):
            last['duration'] += 1 
        else: merged_schedule.append(item) 

    is_single_core = (num_cores == 1)
    fig_height = len(tasks) * 0.8 + 2 if is_single_core else num_cores * 1.5 + 2
    y_label = "Tasks" if is_single_core else "Processors (Cores)"
    y_limit = 10 * (len(tasks) + 1) if is_single_core else 10 * (num_cores + 1)

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
            plt.text(job['time'] + job['duration']/2, y_pos, job['label'], ha='center', va='center', color='white', fontsize=8, fontweight='bold')

    patches = [mpatches.Patch(color='#89b4fa', label='Periodic Task'), mpatches.Patch(color='#a6e3a1', label='Server Task'), mpatches.Patch(color='#fab387', label='Aperiodic Job'), mpatches.Patch(color='#f38ba8', label='Deadline Miss')]
    plt.legend(handles=patches, loc='upper right', frameon=True, fancybox=True, shadow=True)
    plt.title(f"{algorithm} - {('Task View' if is_single_core else 'Core View')}", fontsize=14, fontweight='bold')
    
    annot = gnt.annotate("", xy=(0,0), xytext=(20,20),textcoords="offset points", bbox=dict(boxstyle="round", fc="#313244", ec="black", alpha=0.9), arrowprops=dict(arrowstyle="->", color="black"))
    annot.set_visible(False); annot.set_color("white")

    def hover(event):
        vis = annot.get_visible()
        if event.inaxes == gnt:
            found = False
            for bbox, text in bar_patches:
                if bbox[0] <= event.xdata <= bbox[2] and bbox[1] <= event.ydata <= bbox[3]:
                    annot.xy = (event.xdata, event.ydata); annot.set_text(text); annot.set_visible(True); fig.canvas.draw_idle(); found = True; break
            if not found and vis: annot.set_visible(False); fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", hover)
    plt.tight_layout()
    return fig

# --- NEW: RESULT WINDOW TO REPLACE PLT.SHOW (EMBEDDED) ---
def show_result_window(fig, algorithm):
    result_win = tk.Toplevel()
    result_win.title(f"Simulation Result: {algorithm}")
    result_win.geometry("1000x700")
    
    # Embedding the Plot
    canvas = FigureCanvasTkAgg(fig, master=result_win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)
    
    # Adding Toolbar
    toolbar = NavigationToolbar2Tk(canvas, result_win)
    toolbar.update()
    canvas.get_tk_widget().pack(fill="both", expand=True)

# =============================================================================
# 5. UI (MODERN FLAT V4)
# =============================================================================

def main_app():
    root = tk.Tk()
    root.title("RTSS Simulator - ITU Platinum")
    root.geometry("700x820")
    
    BG_COLOR = "#1e1e2e"; CARD_BG = "#313244"; TEXT_COLOR = "#cdd6f4"
    ACCENT_BLUE = "#89b4fa"; ACCENT_GREEN = "#a6e3a1"; ACCENT_RED = "#f38ba8"; ACCENT_ORANGE = "#fab387"  
    
    root.configure(bg=BG_COLOR)
    style = ttk.Style(); style.theme_use('clam')
    style.configure("TFrame", background=BG_COLOR); style.configure("Card.TFrame", background=CARD_BG, relief="flat", borderwidth=0)
    style.configure("TLabel", background=CARD_BG, foreground=TEXT_COLOR, font=("Helvetica Neue", 11))
    style.configure("Header.TLabel", background=BG_COLOR, foreground=ACCENT_BLUE, font=("Helvetica Neue", 22, "bold"))
    style.configure("Action.TButton", background=ACCENT_BLUE, foreground="#11111b", font=("Helvetica Neue", 11, "bold"), borderwidth=0)
    style.map("Action.TButton", background=[('active', "#b4befe"), ('disabled', '#45475a')], foreground=[('disabled', '#a6adc8')])
    style.configure("TCombobox", fieldbackground="#45475a", background=ACCENT_BLUE, foreground="white", arrowcolor="#11111b", borderwidth=0)
    style.map('TCombobox', fieldbackground=[('readonly', '#45475a')], selectbackground=[('readonly', '#45475a')], selectforeground=[('readonly', 'white')])
    style.configure("TSpinbox", fieldbackground="#45475a", background=ACCENT_BLUE, foreground="white", arrowcolor="#11111b")
    style.configure("Treeview", background="#313244", foreground="white", fieldbackground="#313244", borderwidth=0)
    style.map("Treeview", background=[('selected', ACCENT_BLUE)], foreground=[('selected', 'black')])
    style.configure("Treeview.Heading", background="#45475a", foreground="white", font=('Helvetica', 10, 'bold'))

    main_frame = ttk.Frame(root, padding="30"); main_frame.pack(expand=True, fill="both")
    ttk.Label(main_frame, text="Real-Time Scheduling Simulator", style="Header.TLabel").pack(pady=(0, 25))
    data_store = {"tasks": [], "last_schedule": None, "last_fig": None, "last_algo": "", "filename": "Unknown"}

    card_input = ttk.Frame(main_frame, style="Card.TFrame", padding="20"); card_input.pack(fill="x", pady=(0, 20))
    ttk.Label(card_input, text="1. System Input", font=("Helvetica Neue", 12, "bold"), foreground=ACCENT_ORANGE).pack(anchor="w", pady=(0, 15))
    
    # Layout Fix: Buttons separate from label
    btn_frame = ttk.Frame(card_input, style="Card.TFrame"); btn_frame.pack(fill="x", pady=(0, 10))
    lbl_frame = ttk.Frame(card_input, style="Card.TFrame"); lbl_frame.pack(fill="x")
    
    file_status_lbl = ttk.Label(lbl_frame, text="No file loaded", foreground="#6c7086", font=("Helvetica Neue", 10, "italic"))
    file_status_lbl.pack(side="left", fill="x", expand=True)
    
    def reset_app():
        data_store["tasks"] = []
        data_store["last_schedule"] = None
        file_status_lbl.config(text="No file loaded", foreground="#6c7086")
        btn_export.config(state="disabled"); btn_view.config(state="disabled")
        update_status_bar()

    def update_status_bar():
        if not data_store["tasks"]: util_bar.config(text="System Load: 0.0% (Waiting)", background="#45475a"); return
        num_cores = int(core_spin.get()); raw_u = calculate_utilization(data_store["tasks"])
        load_pct = raw_u * 100; capacity_pct = num_cores * 100.0
        is_overload = raw_u > num_cores
        status_text = f"System Load: {load_pct:.1f}% (Capacity: {capacity_pct:.0f}%)"
        if is_overload: util_bar.config(text=f"⚠️ {status_text} - OVERLOAD", background=ACCENT_RED, foreground="#11111b")
        else: util_bar.config(text=f"✅ {status_text} - SAFE", background=ACCENT_GREEN, foreground="#11111b")

    def view_tasks():
        if not data_store["tasks"]: return
        win = tk.Toplevel(root); win.title("Task List Inspector"); win.geometry("600x400"); win.configure(bg=BG_COLOR)
        cols = ("ID", "Type", "Arrival", "Exec", "Period", "Deadline")
        tree = ttk.Treeview(win, columns=cols, show='headings')
        for col in cols: tree.heading(col, text=col); tree.column(col, width=80, anchor="center")
        for t in data_store["tasks"]:
            t_type = "Periodic" if t.task_type == 'P' else "Server" if t.task_type == 'S' else "Aperiodic"
            vals = (f"T{t.id}", t_type, t.arrival_time, t.burst_time, t.period if t.period > 0 else "-", t.deadline)
            tree.insert("", "end", values=vals, tags=(t.task_type,))
        tree.tag_configure('P', foreground='#89b4fa'); tree.tag_configure('S', foreground='#a6e3a1'); tree.tag_configure('A', foreground='#fab387')
        tree.pack(expand=True, fill='both', padx=10, pady=10)

    def load_file():
        fp = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if fp:
            tasks = parse_file(fp)
            if tasks:
                data_store["tasks"] = tasks; data_store["filename"] = fp.split('/')[-1]
                file_status_lbl.config(text=f"Loaded: {data_store['filename']} ({len(tasks)} tasks)", foreground=ACCENT_GREEN)
                update_status_bar(); btn_export.config(state="disabled"); btn_view.config(state="normal")
            else: messagebox.showerror("Error", "Invalid file!")

    def open_creator():
        creator_win = tk.Toplevel(root); creator_win.title("Task Set Creator"); creator_win.geometry("600x550"); creator_win.configure(bg=BG_COLOR)
        tab_control = ttk.Notebook(creator_win)
        
        tab_manual = ttk.Frame(tab_control); tab_control.add(tab_manual, text='Manual Editor')
        txt_edit = scrolledtext.ScrolledText(tab_manual, width=70, height=25, bg="#11111b", fg=TEXT_COLOR, insertbackground="white", font=("Consolas", 10))
        txt_edit.pack(padx=10, pady=10, fill="both", expand=True)
        # UPDATED TEMPLATE WITH ALL FORMATS
        template = """# SUPPORTED FORMATS GUIDE:
# ---------------------------------------------------------
# PERIODIC TASKS (P):
# P r e p d   -> Release(r), Exec(e), Period(p), Deadline(d)
# P r e p     -> Implicit Deadline (d=p)
# P e p       -> Synchronous (r=0), Implicit Deadline (d=p)

# DEADLINE DRIVEN (D) - (Alternative Periodic):
# D e p d     -> Exec(e), Period(p), Deadline(d) [r=0]
# D r e p d   -> Full definition

# SERVER (S):
# S e p       -> Capacity(e), Replenishment Period(p)

# APERIODIC (A):
# A r e       -> Arrival(r), Execution(e)
# ---------------------------------------------------------

# EXAMPLE SET:
P 0 10 50 50
D 5 40 30
S 5 50
A 12 2
"""
        txt_edit.insert(tk.INSERT, template)
        
        def save_manual():
            content = txt_edit.get("1.0", tk.END); tasks = parse_content(content)
            if tasks:
                f = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="manual_task_set", title="Save Task File")
                if f:
                    with open(f, "w") as file: file.write(content)
                    data_store["tasks"] = tasks; data_store["filename"] = f.split('/')[-1]
                    file_status_lbl.config(text=f"Created: {data_store['filename']} ({len(tasks)} tasks)", foreground=ACCENT_GREEN)
                    update_status_bar(); btn_export.config(state="disabled"); btn_view.config(state="normal"); creator_win.destroy()
            else: messagebox.showerror("Error", "No valid tasks found.")
        ttk.Button(tab_manual, text="Save & Load", command=save_manual).pack(pady=10)
        
        tab_random = ttk.Frame(tab_control); tab_control.add(tab_random, text='Random Generator')
        f_rand = ttk.Frame(tab_random, style="TFrame"); f_rand.pack(pady=20)
        def add_field(parent, label, r):
            tk.Label(parent, text=label, bg=BG_COLOR, fg="white").grid(row=r, column=0, pady=10, sticky="e")
            w = tk.Spinbox(parent, from_=1, to=50); w.grid(row=r, column=1, pady=10, padx=10)
            return w
        e_num = add_field(f_rand, "Total Tasks:", 0); e_ap = add_field(f_rand, "Aperiodic Count:", 1); e_ap.config(from_=0)
        tk.Label(f_rand, text="Target Util:", bg=BG_COLOR, fg="white").grid(row=2, column=0, sticky="e")
        e_util = tk.Entry(f_rand); e_util.insert(0, "0.8"); e_util.grid(row=2, column=1)
        server_var = tk.BooleanVar(value=True)
        tk.Checkbutton(f_rand, text="Add Server Task?", variable=server_var, bg=BG_COLOR, fg="white", selectcolor="#45475a").grid(row=3, columnspan=2, pady=10)
        
        def run_gen():
            try:
                n = int(e_num.get()); a = int(e_ap.get()); u = float(e_util.get())
                if a >= n: messagebox.showerror("Error", "Aperiodic < Total"); return
                tasks = generate_smart_random_tasks(n, a, u, server_var.get())
                data_store["tasks"] = tasks; data_store["filename"] = "Random_Generated"
                file_status_lbl.config(text=f"Generated: Random ({len(tasks)} Tasks)", foreground=ACCENT_BLUE)
                update_status_bar(); btn_export.config(state="disabled"); btn_view.config(state="normal"); creator_win.destroy()
            except Exception as e: messagebox.showerror("Error", str(e))
        ttk.Button(tab_random, text="Generate & Load", command=run_gen).pack()
        tab_control.pack(expand=1, fill="both")

    def create_tooltip(widget, text):
        tip = tk.Toplevel(widget); tip.wm_overrideredirect(True); tip.wm_geometry("+0+0"); tip.withdraw()
        label = tk.Label(tip, text=text, background="#313244", foreground="white", relief="solid", borderwidth=1, font=("tahoma", "9", "normal"))
        label.pack(ipadx=5, ipady=3)
        def enter(event): x = widget.winfo_rootx() + 20; y = widget.winfo_rooty() + 40; tip.wm_geometry(f"+{x}+{y}"); tip.deiconify()
        def leave(event): tip.withdraw()
        widget.bind("<Enter>", enter); widget.bind("<Leave>", leave)

    btn_load = ttk.Button(btn_frame, text="📂 Load", style="Action.TButton", command=load_file); btn_load.pack(side="left", padx=5)
    create_tooltip(btn_load, "Load a .txt file from disk")
    btn_create = ttk.Button(btn_frame, text="✨ Create", style="Action.TButton", command=open_creator); btn_create.pack(side="left", padx=5)
    create_tooltip(btn_create, "Create new task set (Manual or Random)")
    btn_view = ttk.Button(btn_frame, text="📋 List", style="Action.TButton", command=view_tasks, state="disabled"); btn_view.pack(side="left", padx=5)
    create_tooltip(btn_view, "View detailed table of current tasks")
    btn_reset = ttk.Button(btn_frame, text="❌ Reset", style="Action.TButton", command=reset_app); btn_reset.pack(side="left", padx=5)
    create_tooltip(btn_reset, "Clear all data and reset system")

    card_config = ttk.Frame(main_frame, style="Card.TFrame", padding="20"); card_config.pack(fill="x", pady=(0, 20))
    ttk.Label(card_config, text="2. Configuration", font=("Helvetica Neue", 12, "bold"), foreground=ACCENT_ORANGE).pack(anchor="w", pady=(0, 15))
    grid_frame = ttk.Frame(card_config, style="Card.TFrame"); grid_frame.pack(fill="x")
    ttk.Label(grid_frame, text="CPU Cores:").grid(row=0, column=0, sticky="w", pady=5)
    def on_core_change(): update_status_bar()
    core_var = tk.StringVar(value="1")
    core_spin = tk.Spinbox(grid_frame, from_=1, to=4, width=5, font=("Helvetica Neue", 11), textvariable=core_var, command=on_core_change, state="readonly")
    core_spin.grid(row=0, column=1, sticky="w", padx=(10, 30))
    ttk.Label(grid_frame, text="Algorithm:").grid(row=0, column=2, sticky="w", pady=5)
    algos = ["Rate Monotonic (RM)", "Deadline Monotonic (DM)", "Earliest Deadline First (EDF)", "Background", "Poller", "Deferrable Server", "Sporadic Server", "RM Baseline"]
    algo_combo = ttk.Combobox(grid_frame, values=algos, state="readonly", font=("Helvetica Neue", 11), width=25)
    algo_combo.current(0); algo_combo.grid(row=0, column=3, sticky="w", padx=10)

    status_frame = ttk.Frame(main_frame, style="TFrame", padding=(0, 10)); status_frame.pack(fill="x")
    util_bar = ttk.Label(status_frame, text="System Load: 0.0% (Waiting)", font=("Consolas", 11), background="#45475a", foreground=TEXT_COLOR, padding=10); util_bar.pack(fill="x")

    action_frame = ttk.Frame(main_frame, style="TFrame"); action_frame.pack(fill="x", pady=10)
    
    def run_sim():
        if not data_store["tasks"]: messagebox.showwarning("Wait", "Please load tasks first."); return
        sim_tasks = copy.deepcopy(data_store["tasks"])
        selected_algo = algo_combo.get(); num_cores = int(core_spin.get())
        schedule, duration, stats = run_simulation(sim_tasks, selected_algo, num_cores)
        if duration > 0:
            fig = draw_gantt(schedule, sim_tasks, duration, num_cores, selected_algo)
            data_store["last_schedule"] = schedule; data_store["last_stats"] = stats; data_store["last_fig"] = fig; data_store["last_algo"] = selected_algo
            btn_export.config(state="normal")
            show_result_window(fig, selected_algo)

    def export_data():
        if not data_store["last_schedule"]: return
        num_cores = int(core_spin.get())
        export_results(data_store["last_fig"], data_store["last_schedule"], data_store["last_stats"], data_store["last_algo"], data_store["tasks"], num_cores, data_store["filename"])

    btn_run = ttk.Button(action_frame, text="▶ START SIMULATION", style="Action.TButton", command=run_sim); btn_run.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 10))
    btn_export = ttk.Button(action_frame, text="💾 Export Report", style="Action.TButton", command=export_data, state="disabled"); btn_export.pack(side="right", fill="x", expand=True, ipady=10, padx=(10, 0))
    create_tooltip(btn_export, "Saves Chart (.png) and Report (.txt)")

    legend_frame = ttk.Frame(main_frame, style="TFrame"); legend_frame.pack(side="bottom", fill="x", pady=20)
    def add_legend_item(parent, color, text):
        f = ttk.Frame(parent, style="TFrame"); f.pack(side="left", padx=10)
        tk.Label(f, bg=color, width=2, height=1).pack(side="left", padx=(0, 5))
        ttk.Label(f, text=text, font=("Helvetica Neue", 9), background=BG_COLOR).pack(side="left")
    add_legend_item(legend_frame, ACCENT_BLUE, "Periodic"); add_legend_item(legend_frame, ACCENT_GREEN, "Server"); add_legend_item(legend_frame, ACCENT_ORANGE, "Aperiodic"); add_legend_item(legend_frame, ACCENT_RED, "Deadline Miss")

    root.mainloop()

if __name__ == "__main__":
    main_app()