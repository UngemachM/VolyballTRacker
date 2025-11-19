# src/modules/gui/input_view.py

import customtkinter as ctk
from typing import List, Dict, Optional, Any, Tuple
from ..logic.game_controller import GameController 
from .action_dialog import ActionDialog 
from .confirmation_dialog import ConfirmationDialog
# Annahme: Import für den neuen Dialog zur Bearbeitung
from .action_edit_dialog import ActionEditDialog 

class InputView(ctk.CTkFrame):
    """
    Die Hauptansicht zur Live-Erfassung der Volleyball-Statistiken, 
    mit farblich abwechselnden Spieler-Spalten und einer separaten 
    Spalte für die Aktionshistorie.
    """
    # Farben für Zebra-Striping 
    COLOR_LIGHT = ("#dbdbdb", "#2b2b2b")
    COLOR_DARK = ("#c3c3c3", "#212121")

    def __init__(self, master, app_controller, **kwargs):
        super().__init__(master, **kwargs)
        
        self.app_controller = app_controller
        self.game_controller: GameController = self.app_controller.get_game_controller() 
        self.db_manager = self.app_controller.get_db_manager() 
        
        self.players: Dict[int, str] = {}
        self.player_ids: List[int] = []
        self.game_options: Dict[str, int] = {}
        
        # --- GUI-Setup ---
        
        # 1. Haupt-Grid Konfiguration (Row 0: Titel/Score, Row 1: Game Selection, Row 2: Content/History)
        self.grid_columnconfigure(0, weight=1) 
        self.grid_rowconfigure(2, weight=1) # Row 2 (der Content-Frame) bekommt das Gewicht
        
        # Titel (Row 0)
        title_frame = ctk.CTkFrame(self)
        title_frame.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="ew")
        title_frame.grid_columnconfigure(0, weight=1)
        title_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(title_frame, text="🏐 Live Statistik Eingabe", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w")
        
        self.score_label = ctk.CTkLabel(title_frame, text="Set: -", font=ctk.CTkFont(size=20))
        self.score_label.grid(row=0, column=1, sticky="e")
        
        # Spiel-Auswahl Dropdown (Row 1)
        self.game_selection_var = ctk.StringVar(value="--- Spiel wählen ---")
        self.game_selection_menu = ctk.CTkOptionMenu(
            self, 
            values=["--- Spiel wählen ---"], 
            variable=self.game_selection_var,
            command=self.load_selected_game_manual
        )
        self.game_selection_menu.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        # --- HAUPT-CONTENT-FRAME (Row 2) ---
        self.main_content_frame = ctk.CTkFrame(self)
        self.main_content_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # 2. Grid Konfiguration für CONTENT (Eingabe links, Historie rechts)
        self.main_content_frame.grid_columnconfigure(0, weight=3) # Eingabefeld ist breiter
        self.main_content_frame.grid_columnconfigure(1, weight=1) # Historie
        self.main_content_frame.grid_rowconfigure(0, weight=1)
        
        # AKTIONS- UND HEADER-FRAME (Linke Seite)
        self._action_input_frame = ctk.CTkScrollableFrame(self.main_content_frame, label_text="Aktionen") 
        self._action_input_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0) 

        # HISTORIE-FRAME (Rechte Seite)
        self._history_frame = ctk.CTkScrollableFrame(self.main_content_frame, label_text="Aktionshistorie (Letzte 20)")
        self._history_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        self._history_frame.grid_columnconfigure(0, weight=1) # Für die Einträge
        
        # Buttons außerhalb des Frames (Row 3, 4)
        self._setup_fixed_buttons()

        # Initialer Ladevorgang
        self.load_game_options()
        self.load_game_data()
        
    def _setup_fixed_buttons(self):
        """Erstellt die Buttons außerhalb des scrollbaren Bereichs. ACHTUNG: Rows 3 und 4 genutzt."""
        # Spezialfall 'Unser Punkt' (Row 3)
        ctk.CTkButton(
            self, text="Unser Punkt (z.B. Gegner Fehler)", 
            command=lambda: self.handle_action(executor_id=0, action_name="Unser Punkt")
        ).grid(row=3, column=0, sticky="ew", padx=10, pady=10)

        # Spiel beenden (Row 4)
        ctk.CTkButton(
            self, 
            text="🛑 SPIEL BEENDEN", 
            command=self.end_game_confirmation,
            fg_color="red", 
            hover_color="darkred"
        ).grid(row=4, column=0, sticky="ew", padx=10, pady=(5, 20))


    def load_game_options(self):
        # ... (Methode bleibt gleich) ...
        all_games = self.db_manager.get_all_games()
        
        options = ["--- Spiel wählen ---"]
        self.game_options = {}

        if not all_games:
            self.game_selection_menu.configure(values=options)
            return

        for game_id, date_time, home_name, guest_name in all_games:
            display_name = f"[{date_time[:10]}] {home_name} vs. {guest_name}"
            options.append(display_name)
            self.game_options[display_name] = game_id

        self.game_selection_menu.configure(values=options)
        
        current_game_id = self.game_controller._current_game_id
        if current_game_id:
            current_name = next((name for name, id in self.game_options.items() if id == current_game_id), options[0])
            self.game_selection_var.set(current_name)
            

    def load_selected_game_manual(self, selection: str):
        # ... (Methode bleibt gleich) ...
        game_id = self.game_options.get(selection)
        
        if game_id:
            self.game_controller.load_game_context(game_id)
            self.load_game_data() 
        elif selection == "--- Spiel wählen ---":
             self.game_controller._current_game_id = None
             self.game_controller._current_set = None
             self.load_game_data()


    def load_game_data(self):
        """Lädt Spielerdaten und erstellt das GUI neu, falls Spieler fehlen."""
        
        if not self.game_controller._current_game_id:
            self._clear_dynamic_widgets()
            self._clear_history_widgets() 
            self._create_header_and_actions(empty=True) 
            self.update_score_display()
            return
            
        new_players = self.game_controller.get_all_players()
        
        if self.players != new_players:
            self.players = new_players
            self.player_ids = list(self.players.keys())
            
            self._clear_dynamic_widgets()
            
            # Aufbau des gesamten Grids
            self._create_header_and_actions() 
        
        self.update_score_display()
        self.load_action_history() # NEU: Historie laden/aktualisieren


    def _clear_dynamic_widgets(self):
        """Löscht die Widgets im Aktions-ScrollableFrame."""
        for widget in self._action_input_frame.winfo_children():
            widget.destroy()

    def _clear_history_widgets(self):
        """Löscht die Widgets im Historie-ScrollableFrame."""
        for widget in self._history_frame.winfo_children():
            widget.destroy()
            
            
    # src/modules/gui/input_view.py (Ausschnitt der Methode _create_header_and_actions)
    def _create_header_and_actions(self, empty: bool = False):
        """Erstellt Header und Aktionen im SELBEN Grid."""
        input_frame = self._action_input_frame
        
        # 1. Initiale Konfiguration des Grids (Bleibt gleich)
        input_frame.grid_columnconfigure(0, weight=0, minsize=100) 
        
        for i in range(len(self.player_ids)):
            input_frame.grid_columnconfigure(i + 1, weight=1)

        if not self.players or empty:
            # ... (Fehlerbehandlung bleibt gleich) ...
            return
        
        # --- 2. HEADER-ZEILE (Row 0) ---
        action_header_label = ctk.CTkLabel(input_frame, text="Aktion", font=("Arial", 12, "bold"), fg_color=self.COLOR_DARK, anchor="center")
        action_header_label.grid(row=0, column=0, padx=0, pady=(5, 0), sticky="ew") 
        
        for i, player_id in enumerate(self.player_ids):
            col = i + 1
            bg_color = self.COLOR_LIGHT if i % 2 == 0 else self.COLOR_DARK 
            player_name = self.players[player_id]
            label = ctk.CTkLabel(input_frame, text=player_name, font=("Arial", 12, "bold"), fg_color=bg_color, anchor="center") 
            label.grid(row=0, column=col, padx=0, pady=(5, 0), sticky="ew") 


        # --- 3. AKTIONEN-ZEILEN (Ab Row 1) ---
        
        action_names = ["Zuspiel", "Angriff", "Kill", "Aufschlag", "Block"]
        
        for row_idx, action_name in enumerate(action_names):
            current_row = row_idx + 1
            
            # AKTIONENNAME in Spalte 0
            ctk.CTkLabel(input_frame, text=action_name, width=100, anchor="w", fg_color=self.COLOR_DARK).grid(row=current_row, column=0, padx=0, pady=(1, 1), sticky="ew")
            
            # SPIELER-BUTTONS ab Spalte 1
            for col_idx, player_id in enumerate(self.player_ids):
                
                bg_color = self.COLOR_LIGHT if col_idx % 2 == 0 else self.COLOR_DARK
                
                # Hintergrund-Frame
                bg_frame = ctk.CTkFrame(input_frame, fg_color=bg_color, corner_radius=0)
                bg_frame.grid(row=current_row, column=col_idx + 1, padx=0, pady=(0, 0), sticky="nsew") 
                
                # Führe ein internes Grid-Layout im bg_frame ein
                bg_frame.grid_columnconfigure(0, weight=1) 
                bg_frame.grid_rowconfigure(0, weight=1)
                
                button = ctk.CTkButton(
                    bg_frame, 
                    text="+", 
                    width=40, height=20,
                    command=lambda p_id=player_id, a_name=action_name: self.handle_action(p_id, a_name)
                )
                button.grid(row=0, column=0, padx=4, pady=2)

    def load_action_history(self):
        """Lädt die letzten Aktionen aus dem GameController und zeigt sie an."""
        self._clear_history_widgets()
        
        if not self.game_controller._current_game_id:
            ctk.CTkLabel(self._history_frame, text="Kein Spiel aktiv.").grid(row=0, column=0, padx=10, pady=10, sticky="w")
            return

        # Annahme: Der GameController hat eine Methode get_latest_actions()
        # Tupel-Struktur: (action_id, set_number, time, executor_name, action_type, result_type, point_for)
        latest_actions = self.game_controller.get_latest_actions(limit=20) 

        if not latest_actions:
            ctk.CTkLabel(self._history_frame, text="Keine Aktionen erfasst.").grid(row=0, column=0, padx=10, pady=10, sticky="w")
            return
            
        # Header für die Historie (Row 0)
        ctk.CTkLabel(self._history_frame, text="ID | Zeit | Aktion | Punkt", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5, pady=(5, 0), sticky="ew")
        
        for idx, action in enumerate(latest_actions):
            action_id, set_num, time, executor_name, action_type, result_type, point_for = action
            
            # Formatierung des Punkt-Feldes
            point_display = "-> UNS" if point_for == 'OWN' else ("-> OPP" if point_for == 'OPP' else "")
            
            # Zusammenfassung der Aktion
            action_summary = f"[{set_num}] {action_type} ({result_type or ''}) durch {executor_name}"
            
            # Frame für den Eintrag (enthält Label und Button)
            entry_frame = ctk.CTkFrame(self._history_frame, fg_color="transparent")
            entry_frame.grid(row=idx + 1, column=0, sticky="ew", pady=2, padx=5)
            entry_frame.grid_columnconfigure(0, weight=1) # Label bekommt den Platz
            entry_frame.grid_columnconfigure(1, weight=0) # Button ist fix
            
            # Label mit Zeit und Zusammenfassung
            label_text = f"[{time[-8:]}] {action_summary} {point_display}"
            ctk.CTkLabel(entry_frame, text=label_text, anchor="w", justify="left").grid(row=0, column=0, sticky="ew")

            # Bearbeiten Button
            ctk.CTkButton(
                entry_frame, 
                text="✎", 
                width=30, height=20,
                command=lambda a_id=action_id: self.show_edit_dialog(a_id)
            ).grid(row=0, column=1, sticky="e", padx=(5, 0))

    # src/modules/gui/input_view.py (Ausschnitt der Methode show_edit_dialog)

    def show_edit_dialog(self, action_id: int):
        """Öffnet den Bearbeitungsdialog für die ausgewählte Aktion."""
        
        action_details = self.game_controller.get_action_details(action_id)
        
        if not action_details:
            print(f"Fehler: Details für Aktion ID {action_id} nicht gefunden.")
            return

        # VORHER: Der Dialog musste den Controller über master.master selbst finden.
        # NEU: Wir übergeben den Controller direkt.
        ActionEditDialog(
            master=self.master.master, 
            app_controller=self.app_controller,  # <--- HIER IST DIE WICHTIGE ÄNDERUNG
            action_id=action_id,
            details=action_details, 
            players=self.players, 
            callback=self.process_edit_action
        )
    def process_edit_action(self, success: bool):
        """Callback nach Bearbeitung oder Löschung einer Aktion."""
        if success:
            print("Aktion erfolgreich bearbeitet/gelöscht. Daten neu laden.")
            # Lädt Daten, Historie und Punktestand neu
            self.load_game_data() 

    def end_game_confirmation(self):
        """Zeigt einen Bestätigungsdialog vor dem Beenden des Spiels."""
        from .confirmation_dialog import ConfirmationDialog

        ConfirmationDialog(
            master=self.master.master, 
            message="Möchten Sie das aktuelle Spiel wirklich beenden? Die Daten werden gespeichert.",
            callback=self.end_game_action
        )

    def end_game_action(self, confirmed: bool):
        """Beendet das Spiel im Controller und wechselt zur Analyse."""
        if confirmed:
            self.game_controller.end_active_game()
            
            self.app_controller.get_main_window().show_analysis_view()
        else:
            print("Spielende abgebrochen.")

    def handle_action(self, executor_id: int, action_name: str):
        """
        Sendet Aktionen entweder direkt oder über einen Dialog an den GameController.
        """
        if action_name == "Kill":
            self.process_final_action(executor_id=executor_id, action_type="Angriff", result_type="Kill")
            return
        elif action_name == "Unser Punkt":
            self.process_final_action(executor_id=0, action_type="Unser Punkt", result_type=None)
            return
        elif action_name == "Block":
            self.process_final_action(executor_id=executor_id, action_type="Block", result_type="Punkt")
            return
        
        if action_name in ["Angriff", "Aufschlag", "Zuspiel"]:
            self.show_result_dialog(executor_id, action_name)
            return

    def show_result_dialog(self, executor_id: int, action_name: str):
        """Öffnet einen Dialog, um das Ergebnis einer Aktion abzufragen."""
        from .action_dialog import ActionDialog 
        
        ActionDialog(
            master=self.master.master, 
            executor_id=executor_id,
            action_name=action_name,
            players=self.players,
            callback=self.process_final_action
        )

    def process_final_action(self, 
        executor_id: Any, 
        action_type: Optional[str] = None, 
        result_type: Optional[str] = None, 
        target_id: Optional[int] = None
    ):
        """
        Empfängt die vollständigen Aktionsdaten, speichert sie und 
        prüft, ob ein Folge-Dialog (Angriff) geöffnet werden muss (verzögert).
        """
        
        # 1. Daten aus dem Dialog-Dictionary extrahieren (falls vorhanden)
        if isinstance(executor_id, dict):
            data = executor_id
            executor_id = data.get('executor_id')
            action_type = data.get('action_type')
            result_type = data.get('result_type')
            target_id = data.get('target_id')
        
        # 2. Aktion speichern
        success = self.game_controller.process_action(
            executor_id=executor_id, 
            action_type=action_type, 
            result_type=result_type,
            target_id=target_id 
        )
        
        if success:
            self.update_score_display()
            self.load_action_history() # Historie nach jeder Aktion aktualisieren
            
            # 3. PRÜFUNG AUF FOLGE-AKTION (Angriff nach Zuspiel)
            if action_type == "Zuspiel" and target_id is not None:
                
                # FIX: Verwende self.after(ms, func) zur Verzögerung, um TclError zu vermeiden
                self.after(10, lambda: self.show_result_dialog(executor_id=target_id, action_name="Angriff"))

    def update_score_display(self):
        """
        Aktualisiert die Anzeige des aktuellen Spielstands im score_label. 
        """
        score_own = self.game_controller.get_current_score_own()
        score_opp = self.game_controller.get_current_score_opponent()
        set_num = self.game_controller.get_set_number()
        
        self.score_label.configure(text=f"Set {set_num}: {score_own} - {score_opp}")