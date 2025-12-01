import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import random
import math
import copy
import io
import time

st.set_page_config(
    page_title="RTSS Simulator - ITU",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded"
)


import matplotlib
matplotlib.use('Agg')

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
        return [], 0, {'error': f"Error: {algorithm} requires a Server (S) task definition."}

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
        # 1. Arrivals
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

        # 2. Sporadic Replenishment
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

        # 3. Aperiodic Arrivals
        while ap_index < len(aperiodic_tasks) and aperiodic_tasks[ap_index].arrival_time == t:
            aperiodic_queue.append({'task': aperiodic_tasks[ap_index], 'remaining': aperiodic_tasks[ap_index].burst_time, 'abs_deadline': 99999})
            ap_index += 1

        # 4. Poller Check
        if algorithm == "Poller" and server_task:
             for job in ready_queue:
                 if job['task'] == server_task:
                     if not aperiodic_queue: job['remaining'] = 0 
                     break

        # 5. SORTING (PRIORITY ASSIGNMENT)
        ready_queue = [j for j in ready_queue if j['remaining'] > 0]
        
        if algorithm == "Least Laxity First (LLF)":
            # LAXITY = (Absolute Deadline - Current Time) - Remaining Execution
            # Lower Laxity = Higher Priority
            ready_queue.sort(key=lambda x: ((x['abs_deadline'] - t - x['remaining']), x['task'].id))
            
        elif algorithm == "Earliest Deadline First (EDF)": 
            ready_queue.sort(key=lambda x: (x['abs_deadline'], x['task'].id))
            
        elif algorithm == "Deadline Monotonic (DM)": 
            ready_queue.sort(key=lambda x: (x['task'].relative_deadline, x['task'].id))
            
        else: # Rate Monotonic (Default)
            ready_queue.sort(key=lambda x: (x['task'].period if x['task'].period > 0 else 9999, x['task'].id))

        # 6. Dispatching
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


def draw_gantt(raw_schedule, tasks, simulation_time, num_cores, algorithm):
    merged_schedule = []
    raw_schedule.sort(key=lambda x: (x['core'], x['time']))
    for item in raw_schedule:
        if not merged_schedule: merged_schedule.append(item); continue
        last = merged_schedule[-1]
        if (last['core'] == item['core'] and last['task_id'] == item['task_id'] and 
            last['status'] == item['status'] and last['label'] == item['label'] and 
            last['time'] + last['duration'] == item['time']):
            last['duration'] += 1 
        else: merged_schedule.append(item) 

    is_single_core = (num_cores == 1)
    fig_height = len(tasks) * 0.5 + 1 if is_single_core else num_cores * 1.0 + 1
    y_label = "Tasks" if is_single_core else "Processors (Cores)"
    y_limit = 10 * (len(tasks) + 1) if is_single_core else 10 * (num_cores + 1)

    fig, gnt = plt.subplots(figsize=(12, fig_height))
    gnt.set_ylim(0, y_limit)
    gnt.set_xlim(0, simulation_time)
    gnt.set_xlabel('Time (ms)')
    gnt.set_ylabel(y_label)
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
    gnt.set_yticklabels(yticklabels)

    for job in merged_schedule:
        task = next((t for t in tasks if t.id == job['task_id']), None)
        color = task.color if task else 'gray'
        if job['status'] == 'MISS': color = '#f38ba8' 
        y_pos = 10 * (next((i for i, t in enumerate(tasks) if t.id == job['task_id']), 0) + 1) if is_single_core else 10 * job['core']
        gnt.broken_barh([(job['time'], job['duration'])], (y_pos - 4, 8), facecolors=color, edgecolors='black', linewidth=0.5)
        
        if job['label'] and job['duration'] > 1:
            gnt.text(job['time'] + job['duration']/2, y_pos, job['label'], ha='center', va='center', color='white', fontsize=8, fontweight='bold')

    patches = [mpatches.Patch(color='#89b4fa', label='Periodic Task'), mpatches.Patch(color='#a6e3a1', label='Server Task'), mpatches.Patch(color='#fab387', label='Aperiodic Job'), mpatches.Patch(color='#f38ba8', label='Deadline Miss')]
    gnt.legend(handles=patches, loc='upper right', frameon=True)
    gnt.set_title(f"{algorithm} - {('Task View' if is_single_core else 'Core View')}")
    
    return fig

def main():
    st.markdown("## ⏱️ RTSS Simulator - ITU Gold (Web Edition)")
    st.markdown("""
    A web-based simulator for **BLG 456E**. Supports Multicore, Sporadic Server, EDF, and **Least Laxity First**.
    *Developed by Batuhan.*
    """)

    # --- SIDEBAR CONFIG ---
    with st.sidebar:
        st.header("⚙️ Configuration")
        num_cores = st.number_input("CPU Cores", min_value=1, max_value=4, value=1)
        algorithm = st.selectbox("Scheduling Algorithm", [
            "Rate Monotonic (RM)", "Deadline Monotonic (DM)", 
            "Earliest Deadline First (EDF)", "Least Laxity First (LLF)",
            "Background", "Poller", "Deferrable Server", "Sporadic Server", "RM Baseline"
        ])
        
        st.divider()
        st.markdown("### ℹ️ Info")
        st.info("Upload a .txt file or Generate random tasks to begin.")

    # --- SESSION STATE ---
    if 'tasks' not in st.session_state: st.session_state.tasks = []
    
    # --- TABS FOR INPUT ---
    tab1, tab2, tab3 = st.tabs(["📂 Load File", "🎲 Random Generator", "✏️ Manual Input"])

    with tab1:
        uploaded_file = st.file_uploader("Upload Task File (.txt)", type="txt")
        if uploaded_file is not None:
            content = uploaded_file.getvalue().decode("utf-8")
            st.session_state.tasks = parse_content(content)
            st.success(f"Loaded: {uploaded_file.name} ({len(st.session_state.tasks)} tasks)")

    with tab2:
        col1, col2 = st.columns(2)
        rn = col1.number_input("Total Tasks", 1, 20, 5)
        ra = col2.number_input("Aperiodic Count", 0, 10, 1)
        ru = st.slider("Target Utilization", 0.1, 4.0, 0.8)
        rs = st.checkbox("Add Server?", value=True)
        
        if st.button("Generate Random Set", type="primary"):
            st.session_state.tasks = generate_smart_random_tasks(rn, ra, ru, rs)
            st.success(f"Generated {len(st.session_state.tasks)} random tasks.")

    with tab3:
        default_txt = "# P r e p d\n# S e p\n# A r e\nP 0 10 50 50\nS 5 50\nA 12 2"
        txt_input = st.text_area("Paste Task Data Here", value=default_txt, height=150)
        if st.button("Load Manual Data"):
            st.session_state.tasks = parse_content(txt_input)
            st.success("Loaded manual tasks.")

    # --- MAIN DISPLAY ---
    st.divider()
    
    if st.session_state.tasks:
        # Utilization Bar
        u = calculate_utilization(st.session_state.tasks)
        cap = num_cores * 1.0
        status_color = "red" if u > cap else "green"
        st.markdown(f"### System Load: :{status_color}[{u*100:.1f}%] (Capacity: {cap*100:.0f}%)")
        
        with st.expander("View Task List"):
            task_data = [{"ID": t.id, "Type": t.task_type, "C": t.burst_time, "P": t.period, "D": t.deadline} for t in st.session_state.tasks]
            st.table(task_data)

        # --- RUN SIMULATION ---
        if st.button("▶ START SIMULATION", type="primary", use_container_width=True):
            with st.spinner("Simulating..."):
                sim_tasks = copy.deepcopy(st.session_state.tasks)
                schedule, duration, stats = run_simulation(sim_tasks, algorithm, num_cores)
                
                if 'error' in stats:
                    st.error(stats['error'])
                else:
                    # Metrics
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Duration", f"{duration} ms")
                    m2.metric("Missed Deadlines", stats['missed_deadlines'], delta_color="inverse" if stats['missed_deadlines']>0 else "normal")
                    m3.metric("Total Jobs", stats['total_jobs'])
                    m4.metric("Aperiodic Done", stats['aperiodic_done'])
                    
                    # Chart
                    fig = draw_gantt(schedule, sim_tasks, duration, num_cores, algorithm)
                    st.pyplot(fig)
                    
                    # Export
                    report_text = f"Algorithm: {algorithm}\nCores: {num_cores}\nLoad: {u*100:.1f}%\nMisses: {stats['missed_deadlines']}\n"
                    st.download_button("💾 Download Report (.txt)", report_text, file_name=f"Report_{algorithm.split()[0]}.txt")
                    
                    img = io.BytesIO()
                    fig.savefig(img, format='png')
                    st.download_button("🖼️ Download Chart (.png)", img, file_name=f"Chart_{algorithm.split()[0]}.png", mime="image/png")

    else:
        st.warning("Waiting for tasks...")

if __name__ == "__main__":
    main()
