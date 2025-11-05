# src/modules/gui/main_window.py

import customtkinter as ctk
from .input_view import InputView
from .analysis_view import AnalysisView
from .admin_view import AdminView

class MainWindow(ctk.CTkFrame):
    """
    Das Haupt-Container-Frame für die gesamte Anwendung. 
    Hier wird die Navigation (Sidebar) und der Inhaltsbereich implementiert.
    """
    def __init__(self, master, app_controller, **kwargs):
        super().__init__(master, **kwargs)
        
        self.app_controller = app_controller # Referenz zur Haupt-App-Klasse
        
        # Konfiguriere Grid-Layout (1 Spalte für Sidebar, 1 für Inhalt)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # --- 1. Navigation Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1) # Platzhalter für Spacer

        self.start_game_button = ctk.CTkButton(self.sidebar_frame, 
                                           text="🚀 Spiel starten", 
                                           command=self.show_start_game_dialog,
                                           fg_color="green", hover_color="darkgreen")
        self.start_game_button.grid(row=1, column=0, padx=20, pady=(20, 10))
        
        ctk.CTkLabel(self.sidebar_frame, text="Statistik", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Navigations-Buttons
        self.input_button = ctk.CTkButton(self.sidebar_frame, text="Eingabe", command=self.show_input_view)
        self.input_button.grid(row=2, column=0, padx=20, pady=10)
        
        self.analysis_button = ctk.CTkButton(self.sidebar_frame, text="Analyse", command=self.show_analysis_view)
        self.analysis_button.grid(row=3, column=0, padx=20, pady=10)
        
        self.admin_button = ctk.CTkButton(self.sidebar_frame, text="Verwaltung", command=self.show_admin_view)
        self.admin_button.grid(row=4, column=0, padx=20, pady=10)

        # --- 2. Inhaltsbereich ---
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # Initialisiere die Ansichten (Platzhalter)
        self.input_view = None  # Wird bei Bedarf initialisiert
        self.analysis_view = None
        self.admin_view = None
        
        self.current_view = None
        self.show_input_view() # Starte mit der Eingabeansicht

    def show_start_game_dialog(self):
        """Öffnet den Dialog zur Spielvorbereitung."""
        from .start_dialog import StartGameDialog # Importiere den neuen Dialog
        
        # Stelle die aktuelle Team-ID (1) und alle Spieler bereit
        all_teams = self.app_controller.get_db_manager().get_all_teams() # Methode muss erstellt werden
        all_players = self.app_controller.get_game_controller().get_all_players_details() # Methode muss erstellt werden

        StartGameDialog(
            master=self.master, 
            app_controller=self.app_controller,
            teams=all_teams,
            players=all_players,
            callback=self.handle_game_started
        )

    def handle_game_started(self, game_id: int):
        """Callback-Funktion nach erfolgreichem Spielstart."""
        # 1. Spiel-ID setzen (wird in der aktuellen Architektur nicht direkt genutzt, aber gut für Kontext)
        self.app_controller.current_game_id = game_id 
        
        # 2. Zur Eingabeansicht wechseln
        self.show_input_view() 
        
        # 3. WICHTIG: Die InputView muss jetzt die neuen Spieler laden und anzeigen
        if self.input_view:
            self.input_view.load_game_data()

    def switch_view(self, new_view):
        """Wechselt die aktuell angezeigte Ansicht im Inhaltsbereich."""
        if self.current_view:
            self.current_view.grid_forget()
            
        self.current_view = new_view
        self.current_view.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

    def show_input_view(self):
        """Initialisiert und zeigt die Eingabeansicht an."""
        
        if self.input_view is None:
            self.input_view = InputView(
                master=self.content_frame, 
                app_controller=self.app_controller 
            )
        
        self.switch_view(self.input_view)

    # ... in der Klasse MainWindow ...

    def show_analysis_view(self):
        """Initialisiert und zeigt die Analyseansicht an."""

        if self.analysis_view is None:
            self.analysis_view = AnalysisView(
                master=self.content_frame, 
                app_controller=self.app_controller
            )
        self.switch_view(self.analysis_view)


    def show_admin_view(self):
        """Initialisiert und zeigt die Verwaltungsansicht an."""

        if self.admin_view is None:
            self.admin_view = AdminView(
                master=self.content_frame, 
                app_controller=self.app_controller
            )
        self.switch_view(self.admin_view)
