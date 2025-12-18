# src/modules/gui/analysis_view.py

import customtkinter as ctk
import pandas as pd
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

        # --- HEADER ---
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

        # --- TABS ---
        self.tabview = ctk.CTkTabview(self, segmented_button_selected_color="#3498db")
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
        self.tab_players = self.tabview.add("👤 Spieler")
        self.tab_combinations = self.tabview.add("🏐 Kombinationen")
        self.tab_settings = self.tabview.add("📈 Zuspiel-Verteilung")

        self.load_game_options()
        if self.current_game_id:
            self.display_analysis(self.current_game_id)

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
            self.current_game_id = self.game_options[options[0]]

    def load_selected_game(self, selection):
        self.current_game_id = self.game_options.get(selection)
        self.display_analysis(self.current_game_id)

    def display_analysis(self, game_id: int):
        # Clearen
        for tab in [self.tab_players, self.tab_combinations, self.tab_settings]:
            for child in tab.winfo_children(): child.destroy()

        self.render_player_cards(game_id)
        self.render_combination_analysis(game_id)
        self.render_setting_distribution(game_id)

    def render_player_cards(self, game_id: int):
        """Dashboard mit sortierten Karten. Blocks sind nun in 'Defensive'."""
        df = self.stats_calculator.calculate_player_general_stats(game_id)
        if df.empty: return

        # Ranking nach Gesamtpunkten
        df = df.sort_values(by="Gesamtpunkte", ascending=False)
        scroll = ctk.CTkScrollableFrame(self.tab_players, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)
        scroll.grid_columnconfigure((0, 1), weight=1)

        for i, (_, row) in enumerate(df.iterrows()):
            p_id = int(row['executor_player_id'])
            name = self.db_manager.get_player_name_by_id(p_id)
            
            card = ctk.CTkFrame(scroll, border_width=2, border_color="#3d3d3d", corner_radius=15)
            card.grid(row=i//2, column=i%2, padx=12, pady=12, sticky="nsew")
            
            # --- Header: Name & Effizienz ---
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=15, pady=(15, 5))
            ctk.CTkLabel(header, text=name, font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
            
            # Effizienz-Badge
            eff = row['Angriffseffizienz'] * 100
            color = "#2ecc71" if eff > 25 else "#e67e22" if eff > 0 else "#e74c3c"
            badge = ctk.CTkFrame(header, fg_color=color, corner_radius=8)
            badge.pack(side="right")
            ctk.CTkLabel(badge, text=f"{eff:.1f}% Eff.", text_color="white", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=8, pady=2)

            # Trennlinie
            ctk.CTkFrame(card, height=2, fg_color="#3d3d3d").pack(fill="x", padx=15, pady=5)

            # --- Statistik-Bereich ---
            stats_container = ctk.CTkFrame(card, fg_color="transparent")
            stats_container.pack(fill="x", padx=10, pady=5)

            # Kategorie 1: Übersicht (Punkte & NEU: Gesamtfehler)
            group_summary = self._create_stat_group(stats_container, "📊 ÜBERSICHT")
            self._add_stat_item(group_summary, "Punkte", int(row['Gesamtpunkte']), "#3498db")
            self._add_stat_item(group_summary, "Gesamtfehler", int(row['Gesamtfehler']), "#e74c3c")

            # Kategorie 2: Offensive (Kills, Angriffsfehler, Versuche)
            group_offense = self._create_stat_group(stats_container, "⚔️ OFFENSIVE")
            self._add_stat_item(group_offense, "Kills", int(row['Kills']))
            self._add_stat_item(group_offense, "A-Fehler", int(row['Angriffsfehler']))
            self._add_stat_item(group_offense, "Angriffe", int(row['Angriffe_Gesamt']))

            # Kategorie 3: Defensive & Aufschläge
            group_bottom = self._create_stat_group(stats_container, "🛡️ DEF & 🚀 SERVICE")
            self._add_stat_item(group_bottom, "Blocks", int(row['Blockpunkte']), "#27ae60")
            self._add_stat_item(group_bottom, "Asse", int(row['Asse']), "#f1c40f")
            self._add_stat_item(group_bottom, "S-Quote %", f"{row['Service_Error_Rate']*100:.0f}%")

    def _create_stat_group(self, parent, title):
        group_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
        group_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(group_frame, text=title, font=ctk.CTkFont(size=10, weight="bold"), 
                     text_color="gray").pack(pady=(5, 0))
        inner_stats = ctk.CTkFrame(group_frame, fg_color="transparent")
        inner_stats.pack(fill="x", pady=5)
        return inner_stats

    def _add_stat_item(self, parent, label, value, color="white"):
        item = ctk.CTkFrame(parent, fg_color="transparent")
        item.pack(side="left", expand=True)
        ctk.CTkLabel(item, text=str(value), font=ctk.CTkFont(size=15, weight="bold"), 
                     text_color=color).pack()
        ctk.CTkLabel(item, text=label, font=ctk.CTkFont(size=9), text_color="gray").pack()
            
    def render_combination_analysis(self, game_id: int):
        """Zeigt, wie effektiv Zuspieler-Angreifer-Paare sind."""
        df = self.stats_calculator.calculate_setter_attacker_efficiency(game_id)
        if df.empty:
            ctk.CTkLabel(self.tab_combinations, text="Keine Kombinations-Daten").pack(pady=20)
            return

        ctk.CTkLabel(self.tab_combinations, text="Beste Duos (Zuspieler ➔ Angreifer)", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        for _, row in df.sort_values("Efficiency", ascending=False).iterrows():
            frame = ctk.CTkFrame(self.tab_combinations)
            frame.pack(fill="x", padx=20, pady=5)
            
            txt = f"{row['Zuspieler']} ➔ {row['Angreifer']}"
            ctk.CTkLabel(frame, text=txt, width=250, anchor="w").pack(side="left", padx=10)
            
            # Fortschrittsbalken für Effizienz
            bar = ctk.CTkProgressBar(frame, width=150)
            bar.pack(side="left", padx=10)
            bar.set(max(0, min(1, row['Efficiency'] / 100)))
            
            ctk.CTkLabel(frame, text=f"{row['Efficiency']}% Effizienz ({row['Total']} Vers.)").pack(side="right", padx=10)

    def render_setting_distribution(self, game_id: int):
        """Die klassische Zuspielverteilung."""
        df = self.stats_calculator.calculate_setting_distribution(game_id)
        if df.empty: return
        
        for setter in df['Zuspieler'].unique():
            f = ctk.CTkFrame(self.tab_settings)
            f.pack(fill="x", padx=20, pady=10)
            ctk.CTkLabel(f, text=f"Setter: {setter}", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10)
            
            for _, r in df[df['Zuspieler'] == setter].iterrows():
                lbl = f"  ➔ {r['Angreifer']}: {r['Prozent']}% ({r['Total']}x)"
                ctk.CTkLabel(f, text=lbl).pack(anchor="w", padx=20)

    def _add_stat(self, parent, label, value):
        f = ctk.CTkFrame(parent, fg_color="#808080", corner_radius=5)
        f.pack(side="left", expand=True, fill="both", padx=2)
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10)).pack()
        ctk.CTkLabel(f, text=str(value), font=ctk.CTkFont(size=14, weight="bold")).pack()

    def export_report(self):
        if not self.current_game_id: return
        path = ctk.filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if path:
            if self.stats_calculator.export_to_pdf(self.current_game_id, path):
                print(f"Exportiert nach {path}")