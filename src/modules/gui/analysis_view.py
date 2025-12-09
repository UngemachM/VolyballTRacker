# src/modules/gui/analysis_view.py

import customtkinter as ctk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from typing import Optional, Dict, Any, List, Tuple
from ..logic.statistic_calculator import StatisticCalculator 

class AnalysisView(ctk.CTkFrame):
    """
    Ansicht zur Darstellung und Visualisierung der Volleyball-Statistiken.
    """
    def __init__(self, master, app_controller, **kwargs):
        super().__init__(master, **kwargs)
        
        self.app_controller = app_controller
        self.stats_calculator: StatisticCalculator = self.app_controller.get_stats_calculator()
        self.db_manager = self.app_controller.get_db_manager() 
        
        self.current_game_id: Optional[int] = None 
        self.game_options: Dict[str, int] = {} 
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Steuerung und Titel (Row 0)
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=0, column=0, padx=10, pady=(20, 10), sticky="ew")
        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(1, weight=3)
        
        ctk.CTkLabel(control_frame, text="📊 Spiel-Analyse", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # Spiel-Auswahl Dropdown
        self.game_selection_var = ctk.StringVar(value="--- Spiel wählen ---")
        self.game_selection_menu = ctk.CTkOptionMenu(control_frame, 
                                                     values=["--- Spiel wählen ---"], 
                                                     variable=self.game_selection_var,
                                                     command=self.load_selected_game)
        self.game_selection_menu.grid(row=0, column=1, padx=10, pady=5, sticky="e")
        
        # 2. Haupt-Inhaltsbereich (Row 1)
        self.analysis_frame = ctk.CTkScrollableFrame(self)
        self.analysis_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.analysis_frame.grid_columnconfigure(0, weight=1)

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
            # Format: [Datum] Heimname vs. Gastname
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


    def clear_analysis_frame(self):
        """Löscht alle Widgets im Analyse-Frame."""
        for widget in self.analysis_frame.winfo_children():
            widget.destroy()


    def display_analysis(self, game_id: Optional[int]):
        """Zentrale Funktion zur Anzeige aller Statistiken."""
        self.clear_analysis_frame()
        
        if not game_id:
            ctk.CTkLabel(self.analysis_frame, text="Bitte ein Spiel zur Analyse auswählen.").grid(row=0, column=0, padx=20, pady=20)
            return
            
        row_counter = 0
        
        # 1. Spielerzusammenfassung (Anforderung 1 & 2)
        row_counter = self.show_player_summary(game_id, start_row=row_counter)
        
        # 2. Zuspielverteilung (Anforderung 3)
        self.show_setting_distribution(game_id, start_row=row_counter)


    # --- 1. SPIELERZUSAMMENFASSUNG & SERVICE RATE ---

    def show_player_summary(self, game_id: int, start_row: int):
        """
        Zeigt alle wichtigen Statistiken pro Spieler an und filtert 0-Werte heraus.
        """
        
        # 1. Daten aggregieren
        summary_df = self.stats_calculator.calculate_player_general_stats(game_id)
        
        if summary_df.empty:
            ctk.CTkLabel(self.analysis_frame, text="Keine Aktionen von Spielern erfasst.").grid(row=start_row, column=0, padx=10, pady=10, sticky="w")
            return current_row + 1

        # 2. Spieler-Namen für die Anzeige
        player_names = self.app_controller.get_game_controller().get_all_players() 
        
        # Sortiere das DataFrame nach Kills abwärts
        summary_df = summary_df.sort_values(by=['Kills'], ascending=False)
        
        current_row = start_row
        
        ctk.CTkLabel(self.analysis_frame, text="--- Spieler-Zusammenfassung ---", font=ctk.CTkFont(weight="bold")).grid(row=current_row, column=0, padx=10, pady=(10, 5), sticky="w")
        current_row += 1

        for _, row in summary_df.iterrows():
            player_id = int(row['executor_player_id'])
            name = player_names.get(player_id, f"ID {player_id} (Unbekannt)")
            
            # --- ZUSAMMENFASSUNG ERSTELLEN (FILTERING VON 0-WERTEN) ---
            
            stats_list = []
            
            # 1. Angriffseffizienz (nur anzeigen, wenn Angriffe vorhanden sind)
            if row['Angriffe Gesamt'] > 0:
                eff_display = f"Effizienz: {row['Angriffseffizienz'] * 100:.1f}% ({int(row['Kills'])}K - {int(row['Angriffsfehler'])}F)"
                stats_list.append(eff_display)
            
            # 2. Aufschlag Quote (nur anzeigen, wenn Aufschläge vorhanden sind)
            if row['Aufschläge Gesamt'] > 0:
                service_data = self.stats_calculator.calculate_service_rate(game_id, player_id)
                rate_display = (f"Aufschlagquote: {service_data['rate'] * 100:.1f}% "
                                f"({service_data['aces']}/{service_data['total_serves']} Asse/Gesamt)")
                stats_list.append(rate_display)
            
            # 3. Weitere Stats filtern (Werte ungleich 0 ausgeben)
            stat_mapping = {
                'Blockpunkte': 'Blockpunkte',
                'Aufschlagfehler': 'Aufschlagfehler',
            }
            
            for col, display_name in stat_mapping.items():
                if row[col] != 0:
                    stats_list.append(f"{display_name}: {int(row[col])}")
            
            
            # Zusammenfassen und anzeigen
            if stats_list:
                summary_text = "\n".join(stats_list)
                
                # Header für den Spieler
                ctk.CTkLabel(self.analysis_frame, 
                             text=f"*** {name} ***", 
                             font=ctk.CTkFont(weight="bold")).grid(row=current_row, column=0, padx=10, pady=(10, 0), sticky="w")
                current_row += 1
                
                # Details
                ctk.CTkLabel(self.analysis_frame, 
                             text=summary_text, 
                             justify="left").grid(row=current_row, column=0, padx=20, pady=(0, 5), sticky="w")
                current_row += 1

        return current_row # Gebe die nächste freie Reihe zurück


    # --- 2. ZUSPIELVERTEILUNG (KACHEL-ANSICHT) ---

    def show_setting_distribution(self, game_id: int, start_row: int):
        """
        Berechnet und zeigt die Zuspielverteilung pro Zuspieler in separaten Boxen an.
        """
        
        distribution_df: pd.DataFrame = self.stats_calculator.calculate_setting_distribution(game_id) 
        
        if distribution_df.empty:
            ctk.CTkLabel(self.analysis_frame, text="Keine Zuspiel-Daten vorhanden.").grid(row=start_row, column=0, padx=10, pady=(20, 10), sticky="w")
            return

        current_row = start_row
        ctk.CTkLabel(self.analysis_frame, text="--- Zuspiel-Verteilung Pro Spieler ---", font=ctk.CTkFont(weight="bold")).grid(row=current_row, column=0, padx=10, pady=(20, 10), sticky="w")
        current_row += 1

        # 1. Gruppiere nach Zuspieler
        setters = distribution_df['Zuspieler'].unique()
        
        # Erstelle ein Container-Frame für die Setter-Boxen (das Grid, in dem die Boxen liegen)
        setter_container = ctk.CTkFrame(self.analysis_frame, fg_color="transparent")
        setter_container.grid(row=current_row, column=0, sticky="ew", padx=10, pady=5)
        
        # Konfiguriere das interne Grid des Containers (3 Spalten)
        setter_container.grid_columnconfigure((0, 1, 2), weight=1) 
        
        frame_col = 0
        frame_row = 0 # Innere Reihe des Containers
        
        for idx, setter_name in enumerate(setters):
            setter_data = distribution_df[distribution_df['Zuspieler'] == setter_name].sort_values(by='Total', ascending=False)
            
            # Frame für den einzelnen Zuspieler (Die "Box")
            setter_frame = ctk.CTkFrame(setter_container)
            setter_frame.grid(row=frame_row, column=frame_col, sticky="nsew", padx=5, pady=5)
            setter_frame.grid_columnconfigure(0, weight=1) 
            
            # Titel
            total_attempts = setter_data['Total'].sum()
            ctk.CTkLabel(setter_frame, 
                         text=f"*** {setter_name} ({total_attempts} Vers.) ***", 
                         font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=(5, 2), sticky="w")

            # Details
            detail_row = 1
            for _, target_row in setter_data.iterrows():
                # Ausgabe der Verteilung
                text = (f"  -> {target_row['Angreifer']}: {target_row['Total']}x "
                        f"({target_row['Prozent']:.1f}%)")
                        
                ctk.CTkLabel(setter_frame, text=text, justify="left", anchor="w").grid(row=detail_row, column=0, padx=15, pady=(0, 2), sticky="w")
                detail_row += 1

            frame_col += 1
            if frame_col >= 3: # Neue Reihe nach 3 Spalten
                frame_col = 0
                frame_row += 1