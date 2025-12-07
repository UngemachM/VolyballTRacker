# src/modules/gui/input_view.py

import customtkinter as ctk
from typing import List, Dict, Optional, Any, Tuple
from ..logic.game_controller import GameController 
from .action_dialog import ActionDialog 
from .confirmation_dialog import ConfirmationDialog
from .action_edit_dialog import ActionEditDialog 
# NEUE IMPORTE FÜR PUNKTDETAILS (Annahme: diese existieren im Dateisystem)
from .point_detail_dialog import PointDetailDialog 
from ..config import POINT_DETAIL_OUTCOMES 


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
        
        # NEU: Variablen für die Satzfilterung
        self.set_options: Dict[str, int] = {} 
        self.current_selected_set_id: Optional[int] = None 
        
        # NEU: Zwischenspeicher für die Action-Daten, bevor die Point-Details erfasst werden
        self._pending_action_data: Optional[Dict[str, Any]] = None 
        
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

        # HISTORIE-RAHMEN (Rechte Seite)
        self._history_container = ctk.CTkFrame(self.main_content_frame)
        self._history_container.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        self._history_container.grid_columnconfigure(0, weight=1)
        self._history_container.grid_rowconfigure(2, weight=1) # Platz für den Scrollable Frame

        ctk.CTkLabel(self._history_container, text="Aktionshistorie", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        # Dropdown zur Satz-Auswahl
        self.set_filter_var = ctk.StringVar(value="Satz auswählen...")
        self.set_filter_var.trace_add("write", self._on_set_filter_change) 
        
        self.set_filter_menu = ctk.CTkOptionMenu(self._history_container, 
                                                 values=["Satz auswählen..."], 
                                                 variable=self.set_filter_var
                                                )
        self.set_filter_menu.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        # Scrollable Frame für die Aktionen
        self._history_frame = ctk.CTkScrollableFrame(self._history_container, label_text="Letzte 50 Aktionen")
        self._history_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self._history_frame.grid_columnconfigure(0, weight=1) 

        # Buttons außerhalb des Frames (Row 3, 4)
        self._setup_fixed_buttons()

        # Initialer Ladevorgang
        self.load_game_options()
        self.load_game_data()
        
    def on_action_details_received(self, result_data: Optional[Dict[str, Any]]):
        """
        Wird vom ActionDialog aufgerufen.
        Prüft, ob die Aktion einen Punkt zur Folge hat und öffnet ggf. den Detail-Dialog.
        """
        if not result_data:
            return

        action_type = result_data.get('action_type')
        result_type = result_data.get('result_type')
        
        # Logik, die bestimmt, ob es sich um eine punktbringende Aktion handelt:
        # Hier ist eine Annahme: Alle 'Kill', 'Ass', 'Punkt' (Block) führen zu Punkt-Details.
        point_resulting_results = ['Kill', 'Ass', 'Punkt'] 

        is_point_action = result_type in point_resulting_results 
        
        if is_point_action:
            # Speichere die Kerndaten zwischen
            self._pending_action_data = result_data
            
            # Öffne den neuen Detail-Dialog
            PointDetailDialog(
                # master muss die Top-Level-App sein, um Modalität zu gewährleisten
                master=self.master.master, 
                action_type=action_type,
                callback=self.on_point_details_received
            )
        else:
            # Keine Punkt-Details erforderlich, Aktion direkt verarbeiten
            # Muss process_final_action aufrufen, da handle_action diese Methode erwartet
            self.process_final_action(result_data)
            
    def on_point_details_received(self, point_detail_code: str):
        """
        Wird vom PointDetailDialog aufgerufen und führt die Speicherung der Aktion durch.
        """
        if not self._pending_action_data:
            return

        # Füge die Detailinformationen zu den zwischengespeicherten Daten hinzu
        self._pending_action_data['point_detail_type'] = point_detail_code
        
        # Verarbeite die vollständige Aktion
        self.process_final_action(self._pending_action_data)
        
        # Speicher zurücksetzen
        self._pending_action_data = None
            
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
        """Lädt alle Spiele aus der DB und füllt das Dropdown."""
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
        """Wird aufgerufen, wenn ein Spiel im Dropdown ausgewählt wird. Lädt den Spielkontext."""
        game_id = self.game_options.get(selection)
        
        if game_id:
            self.game_controller.load_game_context(game_id)
            self.load_game_data() 
        elif selection == "--- Spiel wählen ---":
             self.game_controller._current_game_id = None
             self.game_controller._current_set = None
             self.load_game_data()


    def load_game_data(self):
        """Lädt alle relevanten Daten für das ausgewählte Spiel (Spieler, Sets, Score) und aktualisiert die UI."""
        
        # 1. Prüfen, ob ein Spiel aktiv ist
        game_id = self.game_controller.get_current_game_id()
        if game_id is None:
            self._clear_dynamic_widgets()
            self._clear_history_widgets() 
            self._create_header_and_actions(empty=True) 
            self.update_score_display()
            
            # Set-Filter zurücksetzen, wenn kein Spiel aktiv
            self.set_options = {}
            if hasattr(self, 'set_filter_menu'):
                self.set_filter_menu.configure(values=["Satz auswählen..."])
                self.set_filter_var.set("Satz auswählen...")
            self.current_selected_set_id = None
            return
            
        # 2. Spielerdaten laden
        new_players = self.game_controller.get_all_players()
        
        if self.players != new_players:
            self.players = new_players
            self.player_ids = list(self.players.keys())
            
            self._clear_dynamic_widgets()
            self._create_header_and_actions() 
            
        
        # 3. Satzdaten laden und Filter setzen
        self.set_options = self.game_controller.get_all_sets_for_current_game()
        set_names = list(self.set_options.keys())
        
        # Setze den Filter auf den aktuellen Satz, wenn vorhanden, oder auf "Alle Sätze"
        current_set_number = self.game_controller.get_set_number()
        default_set_name = f"Satz {current_set_number}" if f"Satz {current_set_number}" in set_names else "Alle Sätze"
        
        # Sicherstellen, dass die Werte im Dropdown aktuell sind
        if hasattr(self, 'set_filter_menu'):
            self.set_filter_menu.configure(values=set_names)
        
        # Setze das Dropdown. Dies löst den Callback _on_set_filter_change aus.
        self.set_filter_var.set(default_set_name) 

        # 4. Score laden
        self.update_score_display()


    def _clear_dynamic_widgets(self):
        """Löscht die Widgets im Aktions-ScrollableFrame."""
        for widget in self._action_input_frame.winfo_children():
            widget.destroy()

    def _clear_history_widgets(self):
        """Löscht die Widgets im Historie-ScrollableFrame."""
        if hasattr(self, '_history_frame'):
            for widget in self._history_frame.winfo_children():
                widget.destroy()
            
            
    def _create_header_and_actions(self, empty: bool = False):
        """Erstellt Header und Aktionen im SELBEN Grid."""
        input_frame = self._action_input_frame
        
        # 1. Initiale Konfiguration des Grids (Bleibt gleich)
        input_frame.grid_columnconfigure(0, weight=0, minsize=100) 
        
        for i in range(len(self.player_ids)):
            input_frame.grid_columnconfigure(i + 1, weight=1)

        if not self.players or empty:
            # Platzhalter oder Fehlermeldung
            ctk.CTkLabel(input_frame, text="Kein Spiel aktiv oder keine Spieler geladen.", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=10)
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

    def _on_set_filter_change(self, *args):
        """Wird aufgerufen, wenn die Auswahl im Satzfilter geändert wird. Aktualisiert die Historie."""
        selected_set_name = self.set_filter_var.get()
        set_id = self.set_options.get(selected_set_name)
        
        # Aktualisiere die interne Set-ID. Kann None, -1 (Alle Sätze) oder eine gültige ID sein.
        self.current_selected_set_id = set_id
        
        # Lade die Aktionshistorie neu mit dem gewählten Filter
        self.load_action_history()


    def load_action_history(self):
        """Läd die letzten Aktionen aus der Datenbank und zeigt sie an."""
        
        # Ermittle die Set-ID basierend auf der Auswahl im Dropdown
        set_id_to_filter = self.current_selected_set_id if self.current_selected_set_id not in [None, -1] else None
        
        # Übergabe des Filters
        actions = self.game_controller.get_latest_actions(limit=50, set_id=set_id_to_filter) 

        # Zerstöre alle alten Einträge
        for widget in self._history_frame.winfo_children():
            widget.destroy()

        if not actions:
            ctk.CTkLabel(self._history_frame, text="Keine Aktionen in dieser Auswahl erfasst.").grid(row=0, column=0, padx=10, pady=10, sticky="ew")
            return
            
        # Header für die Historie (Row 0)
        ctk.CTkLabel(self._history_frame, text="Satz | Zeit | Aktion | Punkt", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5, pady=(5, 0), sticky="ew")
        
        for idx, action in enumerate(actions):
            # Die Daten kommen als Dictionary aus dem GameController
            action_id = action.get('action_id')
            set_num = action.get('set_number')
            time = action.get('timestamp')[-8:] # Nur die Uhrzeit
            executor_name = action.get('executor_name', 'N/A')
            action_type = action.get('action_type')
            result_type = action.get('result_type')
            # point_for fehlt in der Abfrage des GameControllers, daher nur Platzhalter.
            point_display = "" 

            # Zusammenfassung der Aktion
            action_summary = f"[{set_num}] {executor_name} ({action_type}) -> {result_type or ''}"
            
            # Frame für den Eintrag (enthält Label und Button)
            entry_frame = ctk.CTkFrame(self._history_frame, fg_color="transparent")
            entry_frame.grid(row=idx + 1, column=0, sticky="ew", pady=2, padx=5)
            entry_frame.grid_columnconfigure(0, weight=1) # Label bekommt den Platz
            entry_frame.grid_columnconfigure(1, weight=0) # Button ist fix
            
            # Label mit Zeit und Zusammenfassung
            label_text = f"[{time}] {action_summary} {point_display}"
            ctk.CTkLabel(entry_frame, text=label_text, anchor="w", justify="left").grid(row=0, column=0, sticky="ew")

            # Bearbeiten Button
            ctk.CTkButton(
                entry_frame, 
                text="✎", 
                width=30, height=20,
                command=lambda a_id=action_id: self.show_edit_dialog(a_id)
            ).grid(row=0, column=1, sticky="e", padx=(5, 0))

    def update_score_display(self):
        """
        Aktualisiert die Anzeige des aktuellen Spielstands im score_label. 
        """
        score_own = self.game_controller.get_current_score_own()
        score_opp = self.game_controller.get_current_score_opponent()
        set_num = self.game_controller.get_set_number()
        
        self.score_label.configure(text=f"Set {set_num}: {score_own} - {score_opp}")

    # --- AKTION UND DIALOGE ---

    def show_edit_dialog(self, action_id: int):
        """Öffnet den Bearbeitungsdialog für die ausgewählte Aktion."""
        
        action_details = self.game_controller.get_action_details(action_id)
        
        if not action_details:
            print(f"Fehler: Details für Aktion ID {action_id} nicht gefunden.")
            return

        ActionEditDialog(
            master=self.master.master, 
            app_controller=self.app_controller, 
            action_id=action_id,
            details=action_details, 
            players=self.players, 
            callback=self.process_edit_action
        )
        
    def process_edit_action(self, success: bool):
        """Callback nach Bearbeitung oder Löschung einer Aktion."""
        if success:
            print("Aktion erfolgreich bearbeitet/gelöscht. Daten neu laden.")
            self.load_game_data() 

    def end_game_confirmation(self):
        """Zeigt einen Bestätigungsdialog vor dem Beenden des Spiels."""
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
        Wenn "Angriff", "Aufschlag" oder "Zuspiel" -> ActionDialog.
        """
        if action_name == "Kill":
            # Direkt zum Prozess, da Kill ein Resultat von Angriff ist
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
        """Öffnet den ActionDialog. Der Callback ist on_action_details_received."""
        ActionDialog(
            master=self.master.master, 
            executor_id=executor_id,
            action_name=action_name,
            players=self.players,
            callback=self.on_action_details_received # GEÄNDERT: Ruft zuerst den Checker auf
        )
        
    def process_final_action(self, 
        executor_id: Any, 
        action_type: Optional[str] = None, 
        result_type: Optional[str] = None, 
        target_id: Optional[int] = None,
        point_detail_type: Optional[str] = None # NEU: Für Detail-Dialog
    ):
        """
        Empfängt die vollständigen Aktionsdaten (ggf. mit PointDetails), speichert sie und 
        prüft, ob ein Folge-Dialog (Angriff) oder der Satzende-Dialog geöffnet werden muss.
        """
        
        # 1. Daten aus dem Dictionary extrahieren (falls vorhanden)
        data = {}
        if isinstance(executor_id, dict):
            data = executor_id
            executor_id = data.get('executor_id')
            action_type = data.get('action_type')
            result_type = data.get('result_type')
            target_id = data.get('target_id')
            point_detail_type = data.get('point_detail_type') # NEU
        
        # 2. Aktion speichern und den Satzende-Status abfangen
        # HINWEIS: GameController.process_action MUSS jetzt point_detail_type akzeptieren.
        success, is_set_over = self.game_controller.process_action(
            executor_id=executor_id, 
            action_type=action_type, 
            result_type=result_type,
            target_id=target_id,
            point_detail_type=point_detail_type # NEU
        )
        
        if success:
            self.update_score_display()
            self.load_action_history() 
            
            # 3. PRÜFUNG AUF SATZENDE
            if is_set_over:
                self.after(50, self.confirm_set_end)
                return

            # 4. PRÜFUNG AUF FOLGE-AKTION (Angriff nach Zuspiel)
            if action_type == "Zuspiel" and target_id is not None:
                self.after(10, lambda: self.show_result_dialog(executor_id=target_id, action_name="Angriff"))

    # --- SATZENDE LOGIK ---

    def confirm_set_end(self):
        """Zeigt einen Bestätigungsdialog zum Beenden des Satzes."""
        
        score_own = self.game_controller.get_current_score_own()
        score_opp = self.game_controller.get_current_score_opponent()
        set_num = self.game_controller.get_set_number()
        
        if not self.game_controller.check_set_end_condition():
             return

        ConfirmationDialog(
            master=self.master.master, 
            message=f"Satz {set_num} ist beendet (Score: {score_own}:{score_opp}). Wollen Sie den nächsten Satz starten?",
            callback=self.handle_set_end_action
        )

    def handle_set_end_action(self, confirmed: bool):
        """Startet den nächsten Satz oder setzt den Kontext zurück."""
        if confirmed:
            game_id = self.game_controller.get_current_game_id()
            if game_id:
                self.game_controller.start_new_set(game_id) 
                print(f"Satz {self.game_controller.get_set_number()} gestartet.")
                self.load_game_data() 
        else:
            print("Satzende abgelehnt. Weiterspielen in diesem Satz.")