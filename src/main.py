# src/main.py (Updated mit CustomTkinter)

import sys
import os
import customtkinter as ctk # Importiere CustomTkinter
from modules.data.db_manager import DBManager
from modules.gui.main_window import MainWindow 
from modules.logic.game_controller import GameController 
from modules.config import DB_PATH


ctk.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue") # Themes: "blue" (default), "green", "dark-blue"


from modules.logic.statistic_calculator import StatisticCalculator 


class VolleyballApp(ctk.CTk):
    """Hauptklasse der Anwendung, die das Hauptfenster und die Navigation verwaltet."""
    def __init__(self):
        super().__init__()
        self.title("Volleyball Statistik Erfassung")
        self.geometry("1024x768")
        
        # 1. DATEN & LOGIK INITIALISIERUNG
        self.db_manager = DBManager(db_path=DB_PATH)
        self.initialize_database()
        
        # HINZUGEFÜGT: Game Controller und Stats Calculator
        self.game_controller = GameController(db_manager=self.db_manager) 
        self.stats_calculator = StatisticCalculator(db_manager=self.db_manager) # Für später

        
        # Konfiguriere das Grid für das Hauptfenster
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # 2. GUI INITIALISIERUNG (Ruft get_game_controller() auf, was jetzt funktioniert)
        self.main_window = MainWindow(master=self, app_controller=self)
        self.main_window.grid(row=0, column=0, sticky="nsew") 

    def initialize_database(self):
        # ... (Bleibt gleich) ...
        # WICHTIG: Hier muss auch der Test-Code zum Laden von Spielern sein (siehe vorherige Schritte)
        print(f"Prüfe Datenbank unter: {DB_PATH}")
        db_dir = os.path.dirname(DB_PATH)
        os.makedirs(db_dir, exist_ok=True)
        self.db_manager.setup_database()
        
    # Eine zentrale Methode, um auf den DB-Manager von überall zuzugreifen
    def get_db_manager(self):
        return self.db_manager
        
    # HINZUGEFÜGT: get_game_controller (war vorher außerhalb der Klasse)
    def get_game_controller(self):
        return self.game_controller

    # HINZUGEFÜGT: get_stats_calculator
    def get_stats_calculator(self):
        return self.stats_calculator
    
    def get_main_window(self):
        return self.main_window

def main():
    """Der Hauptprozess, der die App startet."""
    try:
        app = VolleyballApp()
        app.mainloop()
    except Exception as e:
        print(f"Ein kritischer Fehler ist aufgetreten: {e}")
        # Hier könnte man eine GUI-Fehlermeldung anzeigen
        sys.exit(1)

if __name__ == "__main__":
    main()

