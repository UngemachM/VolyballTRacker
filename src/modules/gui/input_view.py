# src/modules/gui/input_view.py

import customtkinter as ctk
from typing import List, Dict, Optional,Any
from ..logic.game_controller import GameController 
from .action_dialog import ActionDialog 
from .confirmation_dialog import ConfirmationDialog

class InputView(ctk.CTkFrame):
    """
    Die Hauptansicht zur Live-Erfassung der Volleyball-Statistiken.
    """
    def __init__(self, master, app_controller, **kwargs):
        super().__init__(master, **kwargs)
        
        self.app_controller = app_controller
        self.game_controller: GameController = self.app_controller.get_game_controller() 
        
        # --- Dynamische Daten ---
        # Lädt die Spieler aus der Datenbank über den Controller: {ID: Name}
        self.players: Dict[int, str] = {}
        self.player_ids: List[int] = []
        
        # --- GUI-Setup ---
        self.grid_columnconfigure(0, weight=1) 
        self.grid_rowconfigure(2, weight=1)    
        
        # Titel
        title_frame = ctk.CTkFrame(self)
        title_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        title_frame.grid_columnconfigure(0, weight=1)
        title_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(title_frame, text="🏐 Live Statistik Eingabe", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w")
        
        # Aktueller Spielstand und Satz (wird in update_score_display gefüllt)
        self.score_label = ctk.CTkLabel(title_frame, text="Set: -", font=ctk.CTkFont(size=20))
        self.score_label.grid(row=0, column=1, sticky="e")
        
        # 1. Spieler-Übersicht (dynamisch)
        self._create_player_header()
        
        # 2. Aktions-Buttons und Eingabefelder (dynamisch)
        self._create_action_inputs()
        
        # Aktualisiere den Score beim Start
        self.update_score_display()

    def load_game_data(self):
        """Lädt Spielerdaten und erstellt das GUI neu, falls Spieler fehlen."""
        
        new_players = self.game_controller.get_all_players()
        
        # Prüfen, ob die Spielerliste sich geändert hat (z.B. nach einem Spielstart)
        if self.players != new_players:
            self.players = new_players
            self.player_ids = list(self.players.keys())
            
            # Muss die alten Widgets löschen, da sich die Anzahl der Spieler geändert hat
            self._clear_input_widgets()
            
            # GUI neu aufbauen
            self._create_player_header()
            self._create_action_inputs()
        
        self.update_score_display() # Score immer aktualisieren

    def _clear_input_widgets(self):
        """Löscht die dynamischen GUI-Elemente (Header und Buttons)."""
        # Dies ist komplex, da die Widgets nicht einfach durch das erneute Aufrufen der __init__ verschwinden.
        # Sie müssen die Frames löschen und neu erstellen.
        
        # Vereinfachte Lösung: Nur die Scroll-Frames löschen und neu erstellen (wenn sie Attribute sind)
        # Da dies ein komplexer Refactor ist, gehen wir davon aus, dass Sie die Frames leeren oder die Ansicht neu erstellen.
        # Für den Moment lassen wir es bei der einfachen Lösung und konzentrieren uns auf den Lade-Call.
        
        # ABER: Die Logik für _create_player_header und _create_action_inputs muss jetzt
        # Widgets in den dafür vorgesehenen Frames (die neu erstellt werden müssen) löschen.
        pass # Lassen Sie diese Methode vorerst leer, aber konzentrieren Sie sich auf den Call-Flow.
            
    def _create_player_header(self):
        """Erstellt die Kopfzeile mit den Spielernamen, basierend auf self.players."""
        if not self.players:
            ctk.CTkLabel(self, text="Keine Spieler geladen. Bitte Spieler in Verwaltung hinzufügen.").grid(row=1, column=0, padx=10, pady=10)
            return

        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        # Leere Zelle ganz links (für Aktionsname)
        header_frame.grid_columnconfigure(0, weight=1) 
        ctk.CTkLabel(header_frame, text="Aktion", font=("Arial", 12, "bold")).grid(row=0, column=0, padx=5, pady=5)
        
        for i, player_id in enumerate(self.player_ids):
            col = i + 1
            header_frame.grid_columnconfigure(col, weight=1)
            player_name = self.players[player_id]
            label = ctk.CTkLabel(header_frame, text=player_name, font=("Arial", 12, "bold"))
            label.grid(row=0, column=col, padx=5, pady=5)
            
    def _create_action_inputs(self):
        """Erstellt die Buttons zur Erfassung der Aktionen."""
        if not self.players:
            return

        input_frame = ctk.CTkScrollableFrame(self, label_text="Aktionen pro Spieler")
        input_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        
        action_names = ["Zuspiel", "Angriff", "Kill", "Aufschlag", "Block"]
        
        for row_idx, action_name in enumerate(action_names):
            ctk.CTkLabel(input_frame, text=action_name, width=100, anchor="w").grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")
            
            for col_idx, player_id in enumerate(self.player_ids):
                button = ctk.CTkButton(
                    input_frame, 
                    text="+", 
                    width=40, height=20,
                    # Lambda-Funktion stellt sicher, dass die korrekte ID und Name übergeben werden
                    command=lambda p_id=player_id, a_name=action_name: self.handle_action(p_id, a_name)
                )
                button.grid(row=row_idx, column=col_idx + 1, padx=2, pady=2)
                
        # Spezialfall 'Unser Punkt'
        ctk.CTkButton(
            self, text="Unser Punkt (z.B. Gegner Fehler)", 
            command=lambda: self.handle_action(executor_id=0, action_name="Unser Punkt")
        ).grid(row=3, column=0, sticky="ew", padx=10, pady=10)


        ctk.CTkButton(
            self, 
            text="🛑 SPIEL BEENDEN", 
            command=self.end_game_confirmation,
            fg_color="red", 
            hover_color="darkred"
        ).grid(row=4, column=0, sticky="ew", padx=10, pady=(5, 20))

    def end_game_confirmation(self):
        """Zeigt einen Bestätigungsdialog vor dem Beenden des Spiels."""
        from .confirmation_dialog import ConfirmationDialog # Muss noch erstellt werden

        # Der Dialog ruft end_game_action auf, wenn bestätigt wird
        ConfirmationDialog(
            master=self.master.master, 
            message="Möchten Sie das aktuelle Spiel wirklich beenden? Die Daten werden gespeichert.",
            callback=self.end_game_action
        )

    def end_game_action(self, confirmed: bool):
        """Beendet das Spiel im Controller und wechselt zur Analyse."""
        if confirmed:
            # Controller soll das Spiel in der DB als beendet markieren
            self.game_controller.end_active_game()
            
            # UI-Feedback und Wechsel zur Analyse-Ansicht
            print("Spiel erfolgreich beendet und gespeichert.")
            self.master.show_analysis_view() # Wechselt zur Analyse-Ansicht (MainWindow Methode)
        else:
            print("Spielende abgebrochen.")


    def handle_action(self, executor_id: int, action_name: str):
        """
        Sendet Aktionen entweder direkt oder über einen Dialog an den GameController.
        """
        # Aktionen, die keine weiteren Details benötigen
        if action_name == "Kill":
            self.process_final_action(executor_id=executor_id, action_type="Angriff", result_type="Kill")
            return
        elif action_name == "Unser Punkt":
            self.process_final_action(executor_id=0, action_type="Unser Punkt", result_type=None)
            return
        elif action_name == "Block":
            # Hier muss eigentlich ein Dialog (Punkt/Fehler) kommen, vereinfacht zu Punkt:
            self.process_final_action(executor_id=executor_id, action_type="Block", result_type="Punkt")
            return
        
        # Aktionen, die Details (Ergebnis/Ziel) benötigen (Dialog)
        if action_name in ["Angriff", "Aufschlag", "Zuspiel"]:
            self.show_result_dialog(executor_id, action_name)
            return

    def show_result_dialog(self, executor_id: int, action_name: str):
        """Öffnet einen Dialog, um das Ergebnis einer Aktion abzufragen."""
        # Das master.master ist nötig, um die Root-Klasse (CTk) zu bekommen
        ActionDialog(
            master=self.master.master, 
            executor_id=executor_id,
            action_name=action_name,
            players=self.players,
            callback=self.process_final_action
        )

    def process_final_action(self, 
        executor_id: Any, 
        action_type: Optional[str] = None,  # <--- Hinzugefügt: = None
        result_type: Optional[str] = None, 
        target_id: Optional[int] = None
    ):
        """
        Empfängt die vollständigen Aktionsdaten und speichert sie über den GameController.
        Wird vom ActionDialog als Callback aufgerufen.
        """
        # Wenn die Daten als Dictionary vom Dialog kommen:
        if isinstance(executor_id, dict):
            data = executor_id
            executor_id = data.get('executor_id')
            action_type = data.get('action_type')
            result_type = data.get('result_type')
            target_id = data.get('target_id')
        
        success = self.game_controller.process_action(
            executor_id=executor_id, 
            action_type=action_type, 
            result_type=result_type,
            target_id=target_id 
        )
        
        if success:
            self.update_score_display()

    # src/modules/gui/input_view.py (Innerhalb der Methode end_game_action)

    def end_game_action(self, confirmed: bool):
        """Beendet das Spiel im Controller und wechselt zur Analyse."""
        if confirmed:
            self.game_controller.end_active_game()
            
        
            self.master.master.main_window.show_analysis_view() 
            self.master.master.show_analysis_view()
            self.master.master.show_analysis_view()
            self.master.nametowidget(self.master.winfo_parent()).show_analysis_view()
            self.master.winfo_parent().show_analysis_view() 
            self.app_controller.main_window.show_analysis_view() 
        else:
            print("Spielende abgebrochen.")

    def end_game_action(self, confirmed: bool):
        if confirmed:
            self.game_controller.end_active_game()
            
            # KORREKTE ARCHITEKTURLÖSUNG
            self.app_controller.get_main_window().show_analysis_view()

    def load_game_data(self):
        """Lädt Spielerdaten und erstellt das GUI neu, falls Spieler fehlen."""
        
        # Laden der Spielerdaten (wie in den letzten Korrekturen besprochen)
        new_players = self.game_controller.get_all_players()
        
        # Prüfen, ob die Spielerliste sich geändert hat
        if self.players != new_players:
            self.players = new_players
            self.player_ids = list(self.players.keys())
            
            # Für die finale Implementierung müssen Sie hier die GUI neu aufbauen (Widgets löschen)
            # self._clear_input_widgets() 
            self._create_player_header()
            self._create_action_inputs()
        
        self.update_score_display() # <--- Aufruf zur Aktualisierung

    def update_score_display(self):
        """
        Aktualisiert die Anzeige des aktuellen Spielstands im score_label. 
        DIESE METHODE FEHLTE.
        """
        # Ruft die Methoden ab, die wir im GameController erstellt haben
        score_own = self.game_controller.get_current_score_own()
        score_opp = self.game_controller.get_current_score_opponent()
        set_num = self.game_controller.get_set_number()
        
        self.score_label.configure(text=f"Set {set_num}: {score_own} - {score_opp}")