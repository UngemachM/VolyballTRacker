# src/modules/gui/analysis_view.py

import customtkinter as ctk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from typing import Optional, Dict
from ..logic.statistic_calculator import StatisticCalculator 

class AnalysisView(ctk.CTkFrame):
    """
    Ansicht zur Darstellung und Visualisierung der Volleyball-Statistiken.
    """
    # Zwei Blöcke nebeneinander in einer Gruppe (Card-Layout)
    PANELS_PER_ROW = 2 

    def __init__(self, master, app_controller, **kwargs):
        super().__init__(master, **kwargs)
        
        self.app_controller = app_controller
        self.stats_calculator: StatisticCalculator = self.app_controller.get_stats_calculator()
        self.db_manager = self.app_controller.get_db_manager() 
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.current_game_id: Optional[int] = None 
        self.game_options: Dict[str, int] = {} 
        
        # 1. Steuerung und Titel (Row 0)
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=0, column=0, padx=10, pady=(20, 10), sticky="ew")
        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(1, weight=0) 
        
        ctk.CTkLabel(control_frame, text="📊 Spiel-Analyse", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # Spiel-Auswahl Dropdown
        self.game_selection_var = ctk.StringVar(value="--- Spiel wählen ---")
        self.game_selection_menu = ctk.CTkOptionMenu(control_frame, 
                                                     values=["--- Spiel wählen ---"], 
                                                     variable=self.game_selection_var,
                                                     command=self.load_selected_game)
        self.game_selection_menu.grid(row=0, column=1, padx=10, pady=5, sticky="e")
        
        # 2. Haupt-Inhaltsbereich (Row 1) - Verwendung von Tabview
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Tabs erstellen
        self.tab_view.add("Team-Statistik")
        self.tab_view.add("Spieler-Zusammenfassung")
        self.tab_view.add("Zuspiel-Verteilung")

        # Frames für die Tabs
        
        # --- Team-Statistik Tab ---
        team_tab_frame = self.tab_view.tab("Team-Statistik")
        team_tab_frame.grid_columnconfigure(0, weight=1) # FIX: Macht die Spalte im Tab responsiv
        team_tab_frame.grid_rowconfigure(0, weight=1)   # FIX: Macht die Reihe im Tab responsiv
        self.team_frame = ctk.CTkScrollableFrame(team_tab_frame, label_text="Team-Effizienz")
        self.team_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.team_frame.grid_columnconfigure(0, weight=1)
        
        # --- Spieler-Zusammenfassung Tab ---
        player_tab_frame = self.tab_view.tab("Spieler-Zusammenfassung")
        player_tab_frame.grid_columnconfigure(0, weight=1) # FIX: Macht die Spalte im Tab responsiv
        player_tab_frame.grid_rowconfigure(0, weight=1)    # FIX: Macht die Reihe im Tab responsiv
        self.player_summary_frame = ctk.CTkScrollableFrame(player_tab_frame, label_text="Detaillierte Spielerleistung")
        self.player_summary_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # --- Zuspiel-Verteilung Tab ---
        setting_tab_frame = self.tab_view.tab("Zuspiel-Verteilung")
        setting_tab_frame.grid_columnconfigure(0, weight=1) # FIX: Macht die Spalte im Tab responsiv
        setting_tab_frame.grid_rowconfigure(0, weight=1)    # FIX: Macht die Reihe im Tab responsiv
        self.setting_frame = ctk.CTkScrollableFrame(setting_tab_frame, label_text="Zuspiel-Analyse")
        self.setting_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.load_game_options()
        self.display_analysis(self.current_game_id)


    def load_game_options(self):
        """Lädt alle Spiele aus der DB und füllt das Dropdown."""
        all_games = self.db_manager.get_all_games()
        
        if not all_games:
            self.game_selection_menu.configure(values=["Keine Spiele gefunden"])
            return

        options = []
        first_game_id: Optional[int] = None

        for game_id, date_time, home_name, guest_name in all_games:
            display_name = f"[{date_time[:10]}] {home_name} vs. {guest_name}"
            options.append(display_name)
            self.game_options[display_name] = game_id
            
            if first_game_id is None:
                first_game_id = game_id 

        self.game_selection_menu.configure(values=options)
        
        if options:
            self.game_selection_var.set(options[0])
            self.current_game_id = first_game_id
        else:
            self.game_selection_var.set("Keine Spiele gefunden")


    def load_selected_game(self, selection):
        """Wird aufgerufen, wenn im Dropdown ein Spiel ausgewählt wird."""
        game_id = self.game_options.get(selection)
        
        if game_id:
            self.current_game_id = game_id
            self.display_analysis(game_id)


    def clear_frame(self, frame):
        """Löscht alle Widgets in einem gegebenen Frame."""
        for widget in frame.winfo_children():
            widget.destroy()


    def display_analysis(self, game_id: Optional[int]):
        """Zentrale Funktion zur Anzeige aller Statistiken in den Tabs."""
        self.clear_frame(self.team_frame)
        self.clear_frame(self.player_summary_frame)
        self.clear_frame(self.setting_frame)
        
        if not game_id:
            ctk.CTkLabel(self.team_frame, text="Bitte ein Spiel zur Analyse auswählen.").grid(row=0, column=0, padx=20, pady=20)
            return
            
        # TEAM-STATISTIKEN
        self.show_attack_efficiency(game_id, frame=self.team_frame, start_row=0)
        
        # SPIELER-ZUSAMMENFASSUNG (Nutzt nun das neue Card-Flow-Layout)
        self.show_player_performance_summary(game_id)
        
        # ZUSPIEL-VERTEILUNG (Nutzt nun das neue Card-Flow-Layout)
        self.show_setting_distribution(game_id, frame=self.setting_frame, start_row=0)


    def show_attack_efficiency(self, game_id: int, frame, start_row: int):
        """Berechnet und zeigt die Angriffseffizienz des gesamten Teams an."""
        
        efficiency_data = self.stats_calculator.calculate_attack_efficiency(game_id)
        
        ctk.CTkLabel(frame, text="Angriffseffizienz (Team):", font=ctk.CTkFont(weight="bold")).grid(row=start_row, column=0, padx=10, pady=10, sticky="w")
        
        text = (f"Effizienz: {efficiency_data['efficiency'] * 100:.1f}%\n"
                f"Kills: {efficiency_data['kills']}\n"
                f"Fehler: {efficiency_data['errors']}\n"
                f"Gesamtangriffe: {efficiency_data['total_attacks']}")
                
        ctk.CTkLabel(frame, text=text, justify="left").grid(row=start_row + 1, column=0, padx=10, pady=5, sticky="w")


    def show_setting_distribution(self, game_id: int, frame, start_row: int):
        """Berechnet und zeigt die Zuspielverteilung an, verwendet jetzt Card-Flow-Layout."""
        
        distribution_df: pd.DataFrame = self.stats_calculator.calculate_setting_distribution(game_id)
        
        # Dieses Label nimmt nun die volle Breite ein (sticky="ew")
        ctk.CTkLabel(frame, text="Zuspiel-Verteilung:", font=ctk.CTkFont(weight="bold")).grid(row=start_row, column=0, padx=10, pady=(20, 10), sticky="ew") 
        
        if distribution_df.empty:
            ctk.CTkLabel(frame, text="Keine Zuspiel-Daten vorhanden.").grid(row=start_row + 1, column=0, padx=10, sticky="w")
            return

        # Anzeigen als Cards im Flow
        self._display_cards_in_flow(distribution_df, frame, start_row + 1)
        
        
    def show_player_performance_summary(self, game_id: int):
        """Berechnet und zeigt die Spieler-Zusammenfassungsstatistik an, verwendet jetzt Card-Flow-Layout."""
        
        summary_df: pd.DataFrame = self.stats_calculator.calculate_player_performance_summary(game_id)
        
        frame = self.player_summary_frame
        
        if summary_df.empty:
            ctk.CTkLabel(frame, text="Keine Aktionen für Spieler im Spiel erfasst.").grid(row=0, column=0, padx=10, pady=5, sticky="w")
            return

        # Anzeigen als Cards im Flow
        self._display_cards_in_flow(summary_df, frame, start_row=0)
        
        
    def _format_value(self, col_name, value):
        """Hilfsfunktion zur Formatierung von Werten (Zahl oder Prozent)."""
        if pd.isna(value):
            return "N/A"
            
        if "%" in col_name:
            return f"{value:.1f}%"
        elif isinstance(value, (int, float)):
            return str(int(value)) if value == int(value) else f"{value:.1f}"
        return str(value)

        
    def _display_cards_in_flow(self, df: pd.DataFrame, parent_frame, start_row):
        """
        Zeigt jede Zeile des DataFrames als eine "Card" an, angeordnet in einem Grid-Flow (2 nebeneinander).
        """
        
        # Sicherstellen, dass die Spaltenkonfiguration des parent_frame die Cards aufnimmt
        for col_idx in range(self.PANELS_PER_ROW):
            parent_frame.grid_columnconfigure(col_idx, weight=1)
        
        current_row = start_row
        current_col = 0

        for i, row in df.iterrows():
            # 1. Äußere Card (erhöhter Rand und Farbe für Kontrast)
            player_card = ctk.CTkFrame(parent_frame, 
                                       fg_color=("gray95", "gray15"), # Hellerer Hintergrund als der ScrollFrame
                                       corner_radius=10)
            
            # Position der Card im äußeren Grid (Flow-Layout)
            player_card.grid(row=current_row, column=current_col, padx=10, pady=10, sticky="nsew")
            
            # 2. Innere Konfiguration (Details des Blocks)
            
            # --- Spieler-Titel (Fett) ---
            player_name_label = ctk.CTkLabel(player_card, 
                                             text=row[df.columns[0]], # Erster Wert ist immer der Name
                                             font=ctk.CTkFont(weight="bold", size=15),
                                             anchor="w")
            # pack() für vertikale Stapelung innerhalb der Card
            player_name_label.pack(fill="x", padx=15, pady=(10, 5)) 
            
            # --- Detail-Grid-Frame (Enthält Metrik:Wert) ---
            detail_frame = ctk.CTkFrame(player_card, fg_color="transparent")
            detail_frame.pack(fill="both", expand=True, padx=10, pady=5) 
            
            # Konfiguration des inneren, dreispaltigen Key-Value-Grids (Links, Spacer, Rechts)
            detail_frame.grid_columnconfigure(0, weight=0) # Name (Auto)
            detail_frame.grid_columnconfigure(1, weight=1) # Spacer (Gewicht 1)
            detail_frame.grid_columnconfigure(2, weight=0) # Wert (Auto)

            # --- Details als Grid-Einträge ---
            detail_row = 0
            # Beginnt bei Spalte 1, da Spalte 0 der Name/Titel ist
            for j in range(1, len(df.columns)):
                col_name = df.columns[j]
                value = row[j]
                formatted_value = self._format_value(col_name, value)
                
                # Spalte 0: Metrik-Name (linksbündig)
                name_label = ctk.CTkLabel(detail_frame, text=f"{col_name}:", anchor="w")
                name_label.grid(row=detail_row, column=0, sticky="w", padx=(5, 2), pady=1)

                # Spalte 2: Wert (rechtsbündig)
                value_label = ctk.CTkLabel(detail_frame, text=formatted_value, anchor="e")
                value_label.grid(row=detail_row, column=2, sticky="e", padx=(2, 5), pady=1)
                
                detail_row += 1
            
            # 3. Rasterposition für den nächsten Block aktualisieren
            current_col += 1
            if current_col >= self.PANELS_PER_ROW:
                current_col = 0
                current_row += 1