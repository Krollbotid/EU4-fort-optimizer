import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox, simpledialog
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Patch
import json
import os
from itertools import combinations

try:
    import pulp
    PULP_AVAILABLE = True
except ImportError:
    PULP_AVAILABLE = False
    pulp = None

from localization import i18n

class GraphApp:
    def __init__(self, root):
        self.root = root
        self.root.title(i18n.get('app_title'))
        self.root.geometry("1400x900")
        
        self.dragging_node = None
        self.current_G = None
        self.current_pos = {}
        self.node_artist = None
        self.edge_artist = None
        self.label_artists = {}
        
        self.debounce_timer = None
        self.update_delay = tk.IntVar(value=3000)
        
        self.forts = set()
        self.mandatory = set()
        self.preferred = set()
        self.purple = set()
        self.covered = set()
        self.group_constraints = []
        self.neighbor_constraint_mode = tk.IntVar(value=2)
        
        # Основной горизонтальный контейнер
        self.main_pane = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashrelief="raised", sashwidth=8)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Левая панель (вертикальный разделитель)
        left_outer = tk.Frame(self.main_pane)
        self.main_pane.add(left_outer, width=550)
        left_pane = tk.PanedWindow(left_outer, orient=tk.VERTICAL, sashrelief="raised", sashwidth=6)
        left_pane.pack(fill=tk.BOTH, expand=True)
        
        # ---- Конфигурация графа ----
        self.graph_frame = tk.LabelFrame(left_pane, text=i18n.get('graph_config'), font=("Arial", 10, "bold"))
        left_pane.add(self.graph_frame, height=140)
        self.text_area = scrolledtext.ScrolledText(self.graph_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.text_area.pack(fill=tk.BOTH, expand=True)
        
        # ---- Словарь имён ----
        self.names_frame = tk.LabelFrame(left_pane, text=i18n.get('names_dict'), font=("Arial", 10, "bold"))
        left_pane.add(self.names_frame, height=80)
        self.names_area = scrolledtext.ScrolledText(self.names_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.names_area.pack(fill=tk.BOTH, expand=True)
        
        # ---- Панель управления ----
        control_frame = tk.Frame(left_pane)
        left_pane.add(control_frame, height=45)
        self.apply_btn = tk.Button(control_frame, text=i18n.get('apply_btn'), command=self.apply_configuration,
                                   font=("Arial", 10, "bold"), bg="#e0e0e0")
        self.apply_btn.pack(side=tk.LEFT, padx=(0, 10))
        timer_frame = tk.Frame(control_frame)
        timer_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.timer_label = tk.Label(timer_frame, text=i18n.get('timer_label'), font=("Arial", 9))
        self.timer_label.pack(side=tk.LEFT, padx=(0, 5))
        self.timer_spinbox = ttk.Spinbox(timer_frame, from_=500, to=10000, increment=500,
                                         textvariable=self.update_delay, width=8, font=("Arial", 9))
        self.timer_spinbox.pack(side=tk.LEFT)
        self.timer_hint_label = tk.Label(timer_frame, text=i18n.get('timer_hint'), font=("Arial", 8, "italic"), fg="gray")
        self.timer_hint_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # ---- Обязательные ----
        self.mandatory_frame = tk.LabelFrame(left_pane, text=i18n.get('mandatory'), font=("Arial", 10, "bold"))
        left_pane.add(self.mandatory_frame, height=70)
        self.mandatory_text = scrolledtext.ScrolledText(self.mandatory_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.mandatory_text.pack(fill=tk.BOTH, expand=True)
        
        # ---- Желательные ----
        self.preferred_frame = tk.LabelFrame(left_pane, text=i18n.get('preferred'), font=("Arial", 10, "bold"))
        left_pane.add(self.preferred_frame, height=70)
        self.preferred_text = scrolledtext.ScrolledText(self.preferred_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.preferred_text.pack(fill=tk.BOTH, expand=True)
        
        # ---- Исключительные ----
        self.purple_frame = tk.LabelFrame(left_pane, text=i18n.get('purple'), font=("Arial", 10, "bold"))
        left_pane.add(self.purple_frame, height=70)
        self.purple_text = scrolledtext.ScrolledText(self.purple_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.purple_text.pack(fill=tk.BOTH, expand=True)
        
        # ---- Групповые ограничения ----
        self.group_frame = tk.LabelFrame(left_pane, text=i18n.get('group_constraints'), font=("Arial", 10, "bold"))
        left_pane.add(self.group_frame, height=90)
        self.group_text = scrolledtext.ScrolledText(self.group_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.group_text.pack(fill=tk.BOTH, expand=True)
        self.group_text.insert(tk.END, "# Пример:\n# Falsemire: 762,761,759 : 1\n")
        
        # ---- Ограничения соседних крепостей ----
        self.constraint_frame = tk.LabelFrame(left_pane, text=i18n.get('neighbor_constraints'), font=("Arial", 10, "bold"))
        left_pane.add(self.constraint_frame, height=85)
        self.radio_none = tk.Radiobutton(self.constraint_frame, text=i18n.get('neighbor_none'),
                                         variable=self.neighbor_constraint_mode, value=0, font=("Arial", 9))
        self.radio_none.pack(anchor=tk.W)
        self.radio_pref = tk.Radiobutton(self.constraint_frame, text=i18n.get('neighbor_pref'),
                                         variable=self.neighbor_constraint_mode, value=1, font=("Arial", 9))
        self.radio_pref.pack(anchor=tk.W)
        self.radio_all = tk.Radiobutton(self.constraint_frame, text=i18n.get('neighbor_all'),
                                        variable=self.neighbor_constraint_mode, value=2, font=("Arial", 9))
        self.radio_all.pack(anchor=tk.W)
        
        # ---- Кнопки действий ----
        btn_frame = tk.Frame(left_pane)
        left_pane.add(btn_frame, height=70)   # достаточно для двух кнопок
        self.optimize_btn = tk.Button(btn_frame, text=i18n.get('optimize_btn'), command=self.optimize_coverage,
                                      font=("Arial", 10, "bold"), bg="#90EE90")
        self.optimize_btn.pack(fill=tk.X)
        self.manual_btn = tk.Button(btn_frame, text=i18n.get('check_coverage_btn'), command=self.manual_check_coverage,
                                    font=("Arial", 10, "bold"), bg="#FFD700")
        self.manual_btn.pack(fill=tk.X, pady=(2,0))
        
        # ---- Кнопки сохранения/загрузки/сброса/языка ----
        save_load_frame = tk.Frame(left_pane)
        left_pane.add(save_load_frame, height=35)
        self.save_btn = tk.Button(save_load_frame, text=i18n.get('save_btn'), command=self.save_config,
                                  font=("Arial", 9), bg="#D3D3D3")
        self.save_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        self.load_btn = tk.Button(save_load_frame, text=i18n.get('load_btn'), command=self.load_config,
                                  font=("Arial", 9), bg="#D3D3D3")
        self.load_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        self.reset_btn = tk.Button(save_load_frame, text=i18n.get('reset_btn'), command=self.reset_colors,
                                   font=("Arial", 9), bg="#FFB6C1")
        self.reset_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        self.lang_btn = tk.Button(save_load_frame, text=i18n.get('switch_lang'), command=self.toggle_language,
                                  font=("Arial", 9), bg="#ADD8E6")
        self.lang_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        # ---- Результат ----
        self.result_frame = tk.LabelFrame(left_pane, text=i18n.get('result_title'), font=("Arial", 10, "bold"))
        left_pane.add(self.result_frame, height=130)
        self.result_text = scrolledtext.ScrolledText(self.result_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # ---- Правая панель (граф) с панелью инструментов ----
        right_frame = tk.Frame(self.main_pane)
        self.main_pane.add(right_frame, width=700)
        self.fig, self.ax = plt.subplots(figsize=(8, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.toolbar = NavigationToolbar2Tk(self.canvas, right_frame)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Привязка событий для всех текстовых полей (горячие клавиши)
        for widget in (self.text_area, self.names_area, self.mandatory_text, 
                       self.preferred_text, self.purple_text, self.group_text, self.result_text):
            widget.bind("<Control-KeyPress>", self.keypress)
        
        # Привязка автообновления
        self.text_area.bind("<KeyRelease>", self.on_key_release)
        
        # Кастомное перетаскивание узлов
        self.canvas.mpl_connect('pick_event', self.on_pick)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        
        self._load_defaults()
        self.apply_configuration()
        self.update_ui_language()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def keypress(self, e):
        # Обработчик комбинаций клавиш для вставки, копирования и вырезания
        if e.keycode == 86 and e.keysym != 'v':
            self.paste_text(e)
        elif e.keycode == 67 and e.keysym != 'c':
            self.copy_text(e)
        elif e.keycode == 65 and e.keysym != 'a':
            self.select_all(e)
        elif e.keycode == 88 and e.keysym != 'x':
            self.cut_text(e)
    
    # ------------------ Методы локализации ------------------
    def update_ui_language(self):
        self.root.title(i18n.get('app_title'))
        self.graph_frame.config(text=i18n.get('graph_config'))
        self.names_frame.config(text=i18n.get('names_dict'))
        self.mandatory_frame.config(text=i18n.get('mandatory'))
        self.preferred_frame.config(text=i18n.get('preferred'))
        self.purple_frame.config(text=i18n.get('purple'))
        self.group_frame.config(text=i18n.get('group_constraints'))
        self.constraint_frame.config(text=i18n.get('neighbor_constraints'))
        self.result_frame.config(text=i18n.get('result_title'))
        self.apply_btn.config(text=i18n.get('apply_btn'))
        self.optimize_btn.config(text=i18n.get('optimize_btn'))
        self.manual_btn.config(text=i18n.get('check_coverage_btn'))
        self.save_btn.config(text=i18n.get('save_btn'))
        self.load_btn.config(text=i18n.get('load_btn'))
        self.reset_btn.config(text=i18n.get('reset_btn'))
        self.lang_btn.config(text=i18n.get('switch_lang'))
        self.timer_label.config(text=i18n.get('timer_label'))
        self.timer_hint_label.config(text=i18n.get('timer_hint'))
        self.radio_none.config(text=i18n.get('neighbor_none'))
        self.radio_pref.config(text=i18n.get('neighbor_pref'))
        self.radio_all.config(text=i18n.get('neighbor_all'))
        if hasattr(self, 'ax') and self.ax:
            self.ax.set_title(i18n.get('graph_title'))
            self.update_legend()
            self.canvas.draw()
    
    def update_legend(self):
        if hasattr(self, 'ax') and self.ax:
            if self.ax.legend_ is not None:
                self.ax.legend_.remove()
            legend_elements = [Patch(facecolor='red', label=i18n.get('legend_mandatory')),
                               Patch(facecolor='gold', label=i18n.get('legend_fort_normal')),
                               Patch(facecolor='hotpink', label=i18n.get('legend_fort_group')),
                               Patch(facecolor='orange', label=i18n.get('legend_preferred')),
                               Patch(facecolor='purple', label=i18n.get('legend_purple')),
                               Patch(facecolor='lightgreen', label=i18n.get('legend_covered')),
                               Patch(facecolor='lightblue', label=i18n.get('legend_uncovered'))]
            self.ax.legend(handles=legend_elements, loc='upper left', fontsize=8)
    
    def toggle_language(self):
        new_lang = 'en' if i18n._lang == 'ru' else 'ru'
        i18n.set_language(new_lang)
        self.update_ui_language()
        if self.current_G is not None:
            adj = {node: set(self.current_G.neighbors(node)) for node in self.current_G.nodes()}
            self.draw_graph(adj)
    
    # ------------------ Вспомогательные методы ------------------
    def _load_defaults(self):
        default_config = """# Forlorn Vale
779 : 777, 778, 780
778 : 358, 775, 777, 779
777 : 775, 776, 778, 779, 780
775 : 776, 777, 778, 358, 257, 770
358 : 778, 775, 257, 355
257 : 358, 775, 770, 355
355 : 358, 257, 770, 248
248 : 355, 770, 768, 762, 231"""
        self.text_area.insert(tk.END, default_config)
        default_names = "779 : Whistlevale Center\n778 : Northern Outpost"
        self.names_area.insert(tk.END, default_names)
        self.mandatory_text.insert(tk.END, "775\n779")
        self.preferred_text.insert(tk.END, "358\n248")
        self.purple_text.insert(tk.END, "770\n358")
        self.group_text.insert(tk.END, "Falsemire: 762,761,759 : 1\n")
    
    # --- Горячие клавиши (исправлено) ---
    def select_all(self, event):
        event.widget.tag_add('sel', '1.0', 'end')
        return 'break'
    
    def copy_text(self, event):
        try:
            selected = event.widget.get('sel.first', 'sel.last')
            event.widget.clipboard_clear()
            event.widget.clipboard_append(selected)
        except tk.TclError:
            pass
        return 'break'
    
    def paste_text(self, event):
        try:
            text = event.widget.clipboard_get()
            event.widget.insert(tk.INSERT, text)
        except:
            pass
        return 'break'
    
    def cut_text(self, event):
        try:
            selected = event.widget.get('sel.first', 'sel.last')
            event.widget.clipboard_clear()
            event.widget.clipboard_append(selected)
            event.widget.delete('sel.first', 'sel.last')
        except tk.TclError:
            pass
        return 'break'
    
    def on_closing(self):
        if self.debounce_timer:
            self.root.after_cancel(self.debounce_timer)
        plt.close(self.fig)
        self.root.destroy()
    
    def on_key_release(self, event):
        if self.debounce_timer:
            self.root.after_cancel(self.debounce_timer)
        delay = max(100, self.update_delay.get())
        self.debounce_timer = self.root.after(delay, self.apply_configuration)
    
    def sort_key(self, x):
        try:
            return (0, int(x))
        except ValueError:
            return (1, x)
    
    def parse_names(self, text):
        names = {}
        for line in text.split('\n'):
            if ':' in line and not line.strip().startswith('#'):
                parts = line.split(':', 1)
                node = parts[0].strip()
                name = parts[1].strip()
                if node and name:
                    names[node] = name
        return names
    
    def parse_and_symmetrize(self, text):
        lines = text.split('\n')
        adj = {}
        node_lines = {}
        for i, line in enumerate(lines):
            stripped = line.strip()
            if ':' in stripped and not stripped.startswith('#'):
                parts = stripped.split(':', 1)
                node = parts[0].strip()
                node_lines[node] = i
                if node not in adj:
                    adj[node] = set()
                neighbors = [n.strip() for n in parts[1].split(',') if n.strip()]
                for n in neighbors:
                    adj[node].add(n)
                    if n not in adj:
                        adj[n] = set()
                    adj[n].add(node)
        new_nodes = set(adj.keys()) - set(node_lines.keys())
        new_lines = list(lines)
        for node, neighbors in adj.items():
            if node in node_lines:
                idx = node_lines[node]
                indent = lines[idx][:len(lines[idx]) - len(lines[idx].lstrip())]
                neighbors_str = ", ".join(sorted(neighbors, key=self.sort_key))
                new_lines[idx] = f"{indent}{node} : {neighbors_str}"
        if new_nodes:
            sorted_new = sorted(new_nodes, key=self.sort_key)
            new_node_lines = [f"{node} : {', '.join(sorted(adj[node], key=self.sort_key))}" for node in sorted_new]
            unattended_idx = -1
            for i, line in enumerate(new_lines):
                if line.strip() == "# Unattended":
                    unattended_idx = i
                    break
            if unattended_idx != -1:
                end = len(new_lines)
                for i in range(unattended_idx+1, len(new_lines)):
                    if new_lines[i].strip().startswith('#'):
                        end = i
                        break
                for i, nl in enumerate(new_node_lines):
                    new_lines.insert(end + i, nl)
            else:
                if new_lines and new_lines[-1].strip() != "":
                    new_lines.append("")
                new_lines.append("# Unattended")
                new_lines.extend(new_node_lines)
        return "\n".join(new_lines), adj
    
    def apply_configuration(self):
        text_yview = self.text_area.yview()
        names_yview = self.names_area.yview()
        text = self.text_area.get("1.0", tk.END).strip()
        new_text, adj = self.parse_and_symmetrize(text)
        if new_text != self.text_area.get("1.0", tk.END).strip():
            cursor = self.text_area.index(tk.INSERT)
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert(tk.END, new_text)
            try:
                self.text_area.mark_set(tk.INSERT, cursor)
            except:
                pass
            self.text_area.yview_moveto(text_yview[0])
            self.names_area.yview_moveto(names_yview[0])
        self.draw_graph(adj)
    
    def is_in_any_group(self, vertex):
        for _, vertices, _ in self.group_constraints:
            if vertex in vertices:
                return True
        return False
    
    def draw_graph(self, adj):
        self.ax.clear()
        G = nx.Graph()
        for node, neigh in adj.items():
            G.add_node(node)
            for n in neigh:
                G.add_edge(node, n)
        if not G.nodes:
            self.canvas.draw()
            return
        
        self.current_G = G
        names_dict = self.parse_names(self.names_area.get("1.0", tk.END))
        labels = {node: f"{node}\n({names_dict.get(str(node), '')})" if names_dict.get(str(node)) else str(node) for node in G.nodes()}
        self.current_pos = nx.kamada_kawai_layout(G)
        
        node_colors = []
        for node in G.nodes():
            node_str = str(node)
            if node_str in self.mandatory:
                node_colors.append('red')
            elif node_str in self.preferred and node_str in self.forts:
                node_colors.append('orange')
            elif node_str in self.purple and node_str in self.forts:
                node_colors.append('purple')
            elif node_str in self.forts:
                if self.is_in_any_group(node_str):
                    node_colors.append('hotpink')
                else:
                    node_colors.append('gold')
            elif node_str in self.covered:
                node_colors.append('lightgreen')
            else:
                node_colors.append('lightblue')
        
        self.node_artist = nx.draw_networkx_nodes(G, self.current_pos, ax=self.ax, node_color=node_colors, node_size=900)
        if self.node_artist:
            self.node_artist.set_picker(5)
        self.edge_artist = nx.draw_networkx_edges(G, self.current_pos, ax=self.ax, edge_color='gray', width=1.5)
        self.label_artists = nx.draw_networkx_labels(G, self.current_pos, ax=self.ax, labels=labels, font_size=8, font_weight='bold')
        self.update_legend()
        
        all_x = [p[0] for p in self.current_pos.values()]
        all_y = [p[1] for p in self.current_pos.values()]
        if all_x:
            margin = 0.05
            x_range = max(all_x)-min(all_x)
            y_range = max(all_y)-min(all_y)
            self.ax.set_xlim(min(all_x)-margin*x_range, max(all_x)+margin*x_range)
            self.ax.set_ylim(min(all_y)-margin*y_range, max(all_y)+margin*y_range)
        self.ax.set_title(i18n.get('graph_title'))
        
        self.canvas.draw()
    
    # ------------------ Перетаскивание узлов ------------------
    def on_pick(self, event):
        if event.mouseevent.button == 1 and event.artist == self.node_artist and len(event.ind) > 0:
            node_list = list(self.current_G.nodes())
            self.dragging_node = node_list[event.ind[0]]
    
    def on_release(self, event):
        self.dragging_node = None
    
    def on_motion(self, event):
        if self.dragging_node is not None and event.inaxes == self.ax:
            new_x, new_y = event.xdata, event.ydata
            self.current_pos[self.dragging_node] = (new_x, new_y)
            idx = list(self.current_G.nodes()).index(self.dragging_node)
            offsets = self.node_artist.get_offsets()
            offsets[idx] = (new_x, new_y)
            self.node_artist.set_offsets(offsets)
            new_segments = [[self.current_pos[u], self.current_pos[v]] for u, v in self.current_G.edges()]
            self.edge_artist.set_segments(new_segments)
            if self.dragging_node in self.label_artists:
                self.label_artists[self.dragging_node].set_position((new_x, new_y))
            self.canvas.draw_idle()
    
    # ------------------ Сохранение и загрузка ------------------
    def save_config(self):
        config_data = {
            "graph_config": self.text_area.get("1.0", tk.END).strip(),
            "names_config": self.names_area.get("1.0", tk.END).strip(),
            "mandatory_list": self.mandatory_text.get("1.0", tk.END).strip(),
            "preferred_list": self.preferred_text.get("1.0", tk.END).strip(),
            "purple_list": self.purple_text.get("1.0", tk.END).strip(),
            "group_list": self.group_text.get("1.0", tk.END).strip(),
            "update_delay_ms": self.update_delay.get(),
            "neighbor_constraint_mode": self.neighbor_constraint_mode.get()
        }
        try:
            with open("graph_config.json", "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            messagebox.showinfo(i18n.get('save_success'), i18n.get('save_success'))
        except Exception as e:
            messagebox.showerror(i18n.get('save_error'), i18n.get('save_error', error=str(e)))
    
    def load_config(self):
        if not os.path.exists("graph_config.json"):
            messagebox.showwarning(i18n.get('load_not_found'), i18n.get('load_not_found'))
            return
        try:
            with open("graph_config.json", "r", encoding="utf-8") as f:
                config_data = json.load(f)
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert(tk.END, config_data.get("graph_config", ""))
            self.names_area.delete("1.0", tk.END)
            self.names_area.insert(tk.END, config_data.get("names_config", ""))
            self.mandatory_text.delete("1.0", tk.END)
            self.mandatory_text.insert(tk.END, config_data.get("mandatory_list", ""))
            self.preferred_text.delete("1.0", tk.END)
            self.preferred_text.insert(tk.END, config_data.get("preferred_list", ""))
            self.purple_text.delete("1.0", tk.END)
            self.purple_text.insert(tk.END, config_data.get("purple_list", ""))
            self.group_text.delete("1.0", tk.END)
            self.group_text.insert(tk.END, config_data.get("group_list", ""))
            delay = config_data.get("update_delay_ms", 3000)
            self.update_delay.set(delay)
            mode = config_data.get("neighbor_constraint_mode", 2)
            self.neighbor_constraint_mode.set(mode)
            self.apply_configuration()
            messagebox.showinfo(i18n.get('load_success'), i18n.get('load_success'))
        except Exception as e:
            messagebox.showerror(i18n.get('load_error'), i18n.get('load_error', error=str(e)))
    
    def reset_colors(self):
        self.forts = set()
        self.mandatory = set()
        self.preferred = set()
        self.purple = set()
        self.covered = set()
        self.group_constraints = []
        self.result_text.delete("1.0", tk.END)
        if self.current_G is not None:
            adj = {node: set(self.current_G.neighbors(node)) for node in self.current_G.nodes()}
            self.draw_graph(adj)
        messagebox.showinfo(i18n.get('reset_done'), i18n.get('reset_done'))
    
    # ------------------ Оптимизация покрытия ------------------
    def parse_vertex_list_flexible(self, text):
        """Разбирает текст, удаляя комментарии (# ...) и извлекая вершины."""
        # Удаляем всё, что идёт после # в каждой строке
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Находим позицию первого #
            pos = line.find('#')
            if pos != -1:
                line = line[:pos]
            cleaned_lines.append(line)
        text = ' '.join(cleaned_lines)
        # Заменяем запятые на пробелы и разбиваем
        text = text.replace(',', ' ')
        tokens = text.split()
        vertices = set()
        for t in tokens:
            t = t.strip()
            if t and not t.startswith('#'):
                vertices.add(t)
        return vertices
    
    def parse_group_constraints(self, text):
        groups = []
        for line in text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(':')
            if len(parts) < 3:
                continue
            group_name = parts[0].strip()
            vertices_part = parts[1].strip()
            min_count_part = parts[2].strip()
            vertices = set()
            for v in vertices_part.split(','):
                v = v.strip()
                if v:
                    vertices.add(v)
            if not vertices:
                continue
            try:
                min_count = int(min_count_part)
            except ValueError:
                continue
            groups.append((group_name, vertices, min_count))
        return groups
    
    def solve_with_pulp(self, vertices, edges, mandatory, preferred, purple, group_constraints, neighbor_mode):
        prob = pulp.LpProblem("Fortress_Coverage", pulp.LpMinimize)
        x = {v: pulp.LpVariable(f"x_{v}", cat='Binary') for v in vertices}
        prob += pulp.lpSum(x.values())
        
        neighbors = {v: set() for v in vertices}
        for u, v in edges:
            neighbors[u].add(v)
            neighbors[v].add(u)
        
        for u in vertices:
            prob += x[u] + pulp.lpSum(x[v] for v in neighbors[u]) >= 1
        
        for v in mandatory:
            prob += x[v] == 1
        
        for group_name, group_vertices, min_cnt in group_constraints:
            prob += pulp.lpSum(x[v] for v in group_vertices) >= min_cnt
        
        if neighbor_mode == 0:
            for u, v in edges:
                prob += x[u] + x[v] <= 1
        elif neighbor_mode == 1:
            for u, v in edges:
                if u not in purple and v not in purple:
                    prob += x[u] + x[v] <= 1
        
        solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=300)
        prob.solve(solver)
        if prob.status != pulp.LpStatusOptimal:
            return None, False
        
        best_size = int(pulp.value(prob.objective))
        prob += pulp.lpSum(x.values()) == best_size
        prob.objective = pulp.lpSum(-x[v] for v in preferred if v in vertices)
        prob.solve(solver)
        
        forts = {v for v in vertices if x[v].value() > 0.5}
        return forts, True
    
    def optimize_coverage(self):
        if not PULP_AVAILABLE:
            messagebox.showerror(i18n.get('error_title'), i18n.get('pulp_not_installed'))
            return
        
        if self.current_G is None:
            messagebox.showwarning(i18n.get('no_graph'), i18n.get('no_graph_msg'))
            return
        
        mandatory_raw = self.parse_vertex_list_flexible(self.mandatory_text.get("1.0", tk.END))
        preferred_raw = self.parse_vertex_list_flexible(self.preferred_text.get("1.0", tk.END))
        purple_raw = self.parse_vertex_list_flexible(self.purple_text.get("1.0", tk.END))
        group_text = self.group_text.get("1.0", tk.END)
        group_constraints = self.parse_group_constraints(group_text)
        
        all_vertices = set(str(v) for v in self.current_G.nodes())
        mandatory = {v for v in mandatory_raw if v in all_vertices}
        preferred = {v for v in preferred_raw if v in all_vertices}
        purple = {v for v in purple_raw if v in all_vertices}
        
        missing_mandatory = mandatory_raw - all_vertices
        if missing_mandatory:
            messagebox.showerror(i18n.get('missing_mandatory', missing=", ".join(missing_mandatory)),
                                 i18n.get('missing_mandatory', missing=", ".join(missing_mandatory)))
            return
        
        missing_purple = purple_raw - all_vertices
        if missing_purple:
            messagebox.showwarning(i18n.get('warning_title'), i18n.get('warning_purple_not_found', vertices=", ".join(missing_purple)))
            purple = {v for v in purple_raw if v in all_vertices}
        
        all_group_vertices = set()
        for _, verts, _ in group_constraints:
            all_group_vertices.update(verts)
        missing_group = all_group_vertices - all_vertices
        if missing_group:
            messagebox.showerror(i18n.get('missing_group', missing=", ".join(missing_group)),
                                 i18n.get('missing_group', missing=", ".join(missing_group)))
            return
        
        self.group_constraints = group_constraints
        self.purple = purple
        
        vertices = list(all_vertices)
        edges = []
        for u in self.current_G.nodes():
            u_str = str(u)
            for v in self.current_G.neighbors(u):
                v_str = str(v)
                if (u_str, v_str) not in edges and (v_str, u_str) not in edges:
                    edges.append((u_str, v_str))
        
        try:
            forts, _ = self.solve_with_pulp(vertices, edges, mandatory, preferred, purple,
                                            group_constraints, self.neighbor_constraint_mode.get())
        except Exception as e:
            messagebox.showerror(i18n.get('error_title'), i18n.get('error_solving_ilp', error=str(e)))
            return
        
        if forts is None:
            messagebox.showerror(i18n.get('exact_fail'), i18n.get('exact_fail'))
            return
        
        neighbors = {v: set(str(n) for n in self.current_G.neighbors(v)) for v in vertices}
        covered_vertices = set()
        for f in forts:
            covered_vertices.add(f)
            covered_vertices |= neighbors.get(f, set())
        
        self.update_coverage_result(forts, mandatory, preferred, purple, covered_vertices, group_constraints)
        messagebox.showinfo(i18n.get('info_title'), i18n.get('solution_found', count=len(forts)))
    
    # ------------------ Ручная проверка покрытия ------------------
    def manual_check_coverage(self):
        if self.current_G is None:
            messagebox.showwarning(i18n.get('no_graph'), i18n.get('no_graph_msg'))
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(i18n.get('manual_coverage'))
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        label = tk.Label(dialog, text=i18n.get('manual_coverage_enter'), font=("Arial", 10))
        label.pack(pady=10)

        text_area = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, font=("Consolas", 10), height=15)
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)

        def check():
            user_input = text_area.get("1.0", tk.END).strip()
            if not user_input:
                messagebox.showwarning("", i18n.get('manual_coverage_empty'))
                return
            forts = self.parse_vertex_list_flexible(user_input)
            errors = self.check_coverage(forts)
            if errors:
                messagebox.showerror(i18n.get('coverage_check_error'), "\n".join(errors))
            else:
                messagebox.showinfo(i18n.get('coverage_check_ok'), i18n.get('coverage_check_ok'))
            dialog.destroy()

        tk.Button(btn_frame, text=i18n.get('check_btn'), command=check, bg="#90EE90").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text=i18n.get('cancel_btn'), command=dialog.destroy, bg="#FFB6C1").pack(side=tk.LEFT, padx=5)
    
    def check_coverage(self, forts):
        errors = []
        all_vertices = set(str(v) for v in self.current_G.nodes())
        neighbors = {v: set(str(n) for n in self.current_G.neighbors(v)) for v in all_vertices}

        missing = forts - all_vertices
        if missing:
            errors.append(i18n.get('error_missing_vertices', vertices=", ".join(sorted(missing))))

        covered = set()
        for f in forts:
            if f in all_vertices:
                covered.add(f)
                covered.update(neighbors.get(f, set()))
        uncovered = all_vertices - covered
        if uncovered:
            errors.append(i18n.get('error_not_covered', vertices=", ".join(sorted(uncovered))))

        mandatory = self.parse_vertex_list_flexible(self.mandatory_text.get("1.0", tk.END))
        missing_mandatory = mandatory - forts
        if missing_mandatory:
            errors.append(i18n.get('missing_mandatory_forts', vertices=", ".join(sorted(missing_mandatory))))

        group_constraints = self.parse_group_constraints(self.group_text.get("1.0", tk.END))
        for name, vertices, min_cnt in group_constraints:
            selected = forts.intersection(vertices)
            if len(selected) < min_cnt:
                needed = vertices - forts
                errors.append(i18n.get('error_group_not_satisfied', name=name, required=min_cnt, selected=len(selected), needed_vertices=", ".join(sorted(needed))))

        mode = self.neighbor_constraint_mode.get()
        if mode != 2:
            purple = self.parse_vertex_list_flexible(self.purple_text.get("1.0", tk.END))
            for f in forts:
                for u in neighbors.get(f, set()):
                    if u in forts:
                        if mode == 0:
                            errors.append(i18n.get('error_neighbor_violation', v=f, u=u))
                        elif mode == 1:
                            if f not in purple and u not in purple:
                                errors.append(i18n.get('error_neighbor_violation', v=f, u=u))
        return errors
    
    def update_coverage_result(self, forts, mandatory_set, preferred_set, purple_set, covered_vertices, group_constraints):
        self.forts = forts
        self.mandatory = mandatory_set
        self.preferred = preferred_set
        self.purple = purple_set
        self.covered = covered_vertices
        self.group_constraints = group_constraints
        
        names_dict = self.parse_names(self.names_area.get("1.0", tk.END))
        
        result_text = i18n.get('forts_selected') + "\n"
        for f in sorted(forts, key=self.sort_key):
            name = names_dict.get(str(f), "")
            if name:
                result_text += f"{f} ({name}) "
            else:
                result_text += f"{f} "
            if f in mandatory_set:
                result_text += i18n.get('mandatory_tag')
            elif f in preferred_set:
                result_text += i18n.get('preferred_tag')
            elif f in purple_set:
                result_text += i18n.get('purple_tag')
            elif self.is_in_any_group(f):
                result_text += i18n.get('group_tag')
            result_text += "\n"
        result_text += "\n" + i18n.get('total_forts', count=len(forts)) + "\n\n"
        
        if group_constraints:
            result_text += i18n.get('group_header') + "\n"
            for name, vertices, min_cnt in group_constraints:
                selected_in_group = forts.intersection(vertices)
                result_text += i18n.get('group_line',
                                        name=name,
                                        selected=len(selected_in_group),
                                        required=min_cnt,
                                        vertices=", ".join(sorted(selected_in_group))) + "\n"
        
        mode = self.neighbor_constraint_mode.get()
        if mode == 0:
            result_text += "\n" + i18n.get('neighbor_mode_0') + "\n"
        elif mode == 1:
            result_text += "\n" + i18n.get('neighbor_mode_1') + "\n"
        else:
            result_text += "\n" + i18n.get('neighbor_mode_2') + "\n"
        
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, result_text)
        
        adj = {node: set(self.current_G.neighbors(node)) for node in self.current_G.nodes()}
        self.draw_graph(adj)

if __name__ == "__main__":
    root = tk.Tk()
    app = GraphApp(root)
    root.mainloop()