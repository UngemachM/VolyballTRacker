# src/modules/gui/analysis_view.py

import customtkinter as ctk
from typing import Optional, Dict
from ..logic.statistic_calculator import StatisticCalculator 

class AnalysisView(ctk.CTkFrame):
    def __init__(self, master, app_controller, **kwargs):
        super().__init__(master, **kwargs)
        self.app_controller = app_controller
        self.stats_calculator: StatisticCalculator = self.app_controller.get_stats_calculator()
        self.db_manager = self.app_controller.get_db_manager() 
        
        self.current_game_id: Optional[int] = None 
        self.game_options: Dict[str, int] = {} 
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        ctk.CTkLabel(self.header, text="📊 Performance Dashboard", 
                     font=ctk.CTkFont(size=26, weight="bold")).pack(side="left")

        self.export_btn = ctk.CTkButton(self.header, text="📄 PDF Export", 
                                        fg_color="#27ae60", hover_color="#219150",
                                        command=self.export_report)
        self.export_btn.pack(side="right", padx=10)

        self.game_selection_var = ctk.StringVar(value="Spiel wählen...")
        self.game_menu = ctk.CTkOptionMenu(self.header, variable=self.game_selection_var,
                                           command=self.load_selected_game, width=200)
        self.game_menu.pack(side="right")

        # Tabs
        self.tabview = ctk.CTkTabview(self, segmented_button_selected_color="#3498db")
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.tab_players = self.tabview.add("👤 Spieler")
        self.tab_combinations = self.tabview.add("🏐 Kombinationen")
        self.tab_settings = self.tabview.add("📈 Zuspiel-Verteilung")

        self.load_game_options()

    def load_game_options(self):
        all_games = self.db_manager.get_all_games()
        if not all_games: return
        options = []
        for g_id, date_time, home, guest in all_games:
            name = f"[{date_time[:10]}] {home} vs. {guest}"
            options.append(name)
            self.game_options[name] = g_id
        self.game_menu.configure(values=options)
        if options:
            self.game_selection_var.set(options[0])
            self.load_selected_game(options[0])

    def load_selected_game(self, selection):
        self.current_game_id = self.game_options.get(selection)
        self.display_analysis(self.current_game_id)

    def display_analysis(self, game_id: int):
        for tab in [self.tab_players, self.tab_combinations, self.tab_settings]:
            for child in tab.winfo_children(): child.destroy()
        self.render_player_cards(game_id)
        self.render_combination_analysis(game_id)
        self.render_setting_distribution(game_id)

    def render_player_cards(self, game_id: int):
        df = self.stats_calculator.calculate_player_general_stats(game_id)
        if df.empty: return

        df = df.sort_values(by="Gesamtpunkte", ascending=False)
        scroll = ctk.CTkScrollableFrame(self.tab_players, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)
        scroll.grid_columnconfigure((0, 1), weight=1)

        for i, (_, row) in enumerate(df.iterrows()):
            p_id = int(row['executor_player_id'])
            name = self.db_manager.get_player_name_by_id(p_id)
            
            card = ctk.CTkFrame(scroll, border_width=2, border_color="#3d3d3d", corner_radius=15)
            card.grid(row=i//2, column=i%2, padx=12, pady=12, sticky="nsew")
            
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=15, pady=(15, 5))
            ctk.CTkLabel(header, text=name, font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
            
            eff = row['Gesamtquote'] * 100
            color = "#2ecc71" if eff > 20 else "#e67e22" if eff > 0 else "#e74c3c"
            badge = ctk.CTkFrame(header, fg_color=color, corner_radius=8)
            badge.pack(side="right")
            ctk.CTkLabel(badge, text=f"{eff:.1f}% Total", text_color="white", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=8, pady=2)

            ctk.CTkFrame(card, height=2, fg_color="#3d3d3d").pack(fill="x", padx=15, pady=5)
            stats_container = ctk.CTkFrame(card, fg_color="transparent")
            stats_container.pack(fill="x", padx=10, pady=5)

            # 📊 TOTAL
            group_total = self._create_stat_group(stats_container, "📊 TOTAL")
            self._add_stat_item(group_total, "Punkte", f"{row['Gesamtpunkte']:.1f}", "#3498db")
            self._add_stat_item(group_total, "Fehler", int(row['Gesamtfehler']), "#e74c3c")
            self._add_stat_item(group_total, "Versuche", int(row['Gesamtversuche']))
            self._add_stat_item(group_total, "Blocks", int(row['Blocks']), "#27ae60")
            # ⚔️ ANGRIFF
            group_atk = self._create_stat_group(stats_container, "⚔️ ANGRIFF")
            self._add_stat_item(group_atk, "Kills", int(row['Kills']), "#2ecc71")
            self._add_stat_item(group_atk, "Fehler", int(row['Angriffsfehler']), "#e74c3c")
            self._add_stat_item(group_atk, "A-Quote %", f"{row['Angriffsquote']*100:.1f}%")
            self._add_stat_item(group_atk, "Versuche", int(row['Angriffe_Gesamt']))

            # 🚀 AUFSCHLAG
            group_srv = self._create_stat_group(stats_container, "🚀 AUFSCHLAG")
            self._add_stat_item(group_srv, "S-Punkte", f"{row['Aufschlag_Punkte']:.1f}", "#f1c40f")
            self._add_stat_item(group_srv, "S-Fehler", int(row['Aufschlagfehler']), "#e74c3c")
            self._add_stat_item(group_srv, "In-Feld %", f"{row['Ins_Feld_Quote']*100:.1f}%")
            self._add_stat_item(group_srv, "S-Effekt %", f"{row['Aufschlagsquote']*100:.1f}%")
            self._add_stat_item(group_srv, "Versuche", int(row['Aufschläge_Gesamt']))

    def _create_stat_group(self, parent, title):
        group_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
        group_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(group_frame, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="gray").pack()
        inner_stats = ctk.CTkFrame(group_frame, fg_color="transparent")
        inner_stats.pack(fill="x", pady=5)
        return inner_stats

    def _add_stat_item(self, parent, label, value, color="white"):
        item = ctk.CTkFrame(parent, fg_color="transparent")
        item.pack(side="left", expand=True)
        ctk.CTkLabel(item, text=str(value), font=ctk.CTkFont(size=15, weight="bold"), text_color=color).pack()
        ctk.CTkLabel(item, text=label, font=ctk.CTkFont(size=9), text_color="gray").pack()

    def export_report(self):
        if not self.current_game_id: return
        path = ctk.filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if path:
            if self.stats_calculator.export_to_pdf(self.current_game_id, path):
                print(f"Exportiert nach {path}")

    # (render_combination_analysis und render_setting_distribution bleiben gleich)
    def render_combination_analysis(self, game_id: int):
        df = self.stats_calculator.calculate_setter_attacker_efficiency(game_id)
        if df.empty: return
        scroll = ctk.CTkScrollableFrame(self.tab_combinations, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        for _, row in df.sort_values("Efficiency", ascending=False).iterrows():
            frame = ctk.CTkFrame(scroll)
            frame.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(frame, text=f"{row['Zuspieler']} ➔ {row['Angreifer']}", width=250, anchor="w").pack(side="left", padx=10)
            bar = ctk.CTkProgressBar(frame, width=150)
            bar.pack(side="left", padx=10)
            bar.set(max(0, min(1, row['Efficiency'] / 100)))
            ctk.CTkLabel(frame, text=f"{row['Efficiency']}% Eff. ({int(row['Total'])}x)").pack(side="right", padx=10)

    def render_setting_distribution(self, game_id: int):
        df = self.stats_calculator.calculate_setting_distribution(game_id)
        if df.empty: return
        scroll = ctk.CTkScrollableFrame(self.tab_settings, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        for setter in df['Zuspieler'].unique():
            f = ctk.CTkFrame(scroll)
            f.pack(fill="x", padx=20, pady=10)
            ctk.CTkLabel(f, text=f"Setter: {setter}", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10)
            for _, r in df[df['Zuspieler'] == setter].iterrows():
                ctk.CTkLabel(f, text=f"  ➔ {r['Angreifer']}: {r['Prozent']}% ({int(r['Total'])}x)").pack(anchor="w", padx=20)
