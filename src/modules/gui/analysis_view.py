# src/modules/gui/analysis_view.py

import customtkinter as ctk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ..logic.statistic_calculator import StatisticCalculator 

class AnalysisView(ctk.CTkFrame):
    """
    Ansicht zur Darstellung und Visualisierung der Volleyball-Statistiken.
    """
    def __init__(self, master, app_controller, **kwargs):
        super().__init__(master, **kwargs)
        
        self.app_controller = app_controller
        self.stats_calculator: StatisticCalculator = self.app_controller.get_stats_calculator()
        self.db_manager = self.app_controller.get_db_manager() # Zugriff auf DB Manager
        
        self.current_game_id: Optional[int] = None 
        self.game_options: Dict[str, int] = {} # Speichert "Name: ID"
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Steuerung und Titel (Row 0)
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=0, column=0, padx=10, pady=(20, 10), sticky="ew")
        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(1, weight=3)
        
        ctk.CTkLabel(control_frame, text="📊 Spiel-Analyse", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # NEU: Spiel-Auswahl Dropdown
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
        self.display_analysis(self.current_game_id) # Anzeige beim Start

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
                first_game_id = game_id # Wähle das neueste Spiel beim Start

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
            
        # Wenn Sie die Analyse-Methoden aufrufen, stellen Sie sicher, dass sie die Game ID verwenden
        self.show_attack_efficiency(game_id)
        self.show_setting_distribution(game_id, start_row=4) # Startreihe anpassen

    def show_attack_efficiency(self, game_id: int):
        """Berechnet und zeigt die Angriffseffizienz des gesamten Teams an."""
        
        efficiency_data = self.stats_calculator.calculate_attack_efficiency(game_id) # <--- Game ID übergeben
        # ... (Rest des Codes bleibt gleich) ...
        
        # Beispiel-Implementierung der Anzeige
        ctk.CTkLabel(self.analysis_frame, text="--- Angriffseffizienz (Team) ---", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        text = (f"Effizienz: {efficiency_data['efficiency'] * 100:.1f}%\n"
                f"Kills: {efficiency_data['kills']}\n"
                f"Fehler: {efficiency_data['errors']}\n"
                f"Gesamtangriffe: {efficiency_data['total_attacks']}")
                
        ctk.CTkLabel(self.analysis_frame, text=text, justify="left").grid(row=1, column=0, padx=10, pady=5, sticky="w")

    def show_setting_distribution(self, game_id: int, start_row: int):
        """Berechnet und zeigt die Zuspielverteilung an (mit Game ID)."""
        
        distribution_df: pd.DataFrame = self.stats_calculator.calculate_setting_distribution(game_id) # <--- Game ID übergeben
        # ... (Rest des Codes bleibt gleich) ...
        
        ctk.CTkLabel(self.analysis_frame, text="--- Zuspiel-Verteilung ---", font=ctk.CTkFont(weight="bold")).grid(row=start_row, column=0, padx=10, pady=(20, 10), sticky="w")
        
        if distribution_df.empty:
            ctk.CTkLabel(self.analysis_frame, text="Keine Zuspiel-Daten vorhanden.").grid(row=start_row + 1, column=0, padx=10, sticky="w")
            return

        # Matplotlib-Diagramm zur Darstellung der Verteilung
        # ... (Matplotlib-Code zur Anzeige der Verteilung) ...
        pass # Platzhalter für die Darstellung