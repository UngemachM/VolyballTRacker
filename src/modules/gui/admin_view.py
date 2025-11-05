import customtkinter as ctk
from typing import Dict, List, Tuple, Optional
from ..config import VOLLEYBALL_POSITIONS
from ..data.models import Player # Für die Erstellung neuer Spieler

class AdminView(ctk.CTkFrame):
    """
    Ansicht zur Verwaltung von Spielern und Teams (Erstellen, Bearbeiten, Zuweisen).
    """
    def __init__(self, master, app_controller, **kwargs):
        super().__init__(master, **kwargs)
        self.app_controller = app_controller
        self.db_manager = app_controller.get_db_manager()
        self.edit_player_id: Optional[int] = None # ID des Spielers, der gerade bearbeitet wird
        
        # Datenspeicher für Teams und Spieler
        self.teams: Dict[int, str] = {}
        self.all_player_details: List[Tuple[int, str, Optional[int], Optional[str], Optional[int]]] = []
        
        # Grid Konfiguration (2 Spalten für Spieler und Teams)
        self.grid_columnconfigure(0, weight=1) 
        self.grid_columnconfigure(1, weight=1) 
        self.grid_rowconfigure(0, weight=1)

        # --- Spieler-Verwaltung (Linke Spalte) ---
        self.player_main_frame = ctk.CTkFrame(self)
        self.player_main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.player_main_frame.grid_columnconfigure(0, weight=1)
        self.player_main_frame.grid_rowconfigure(2, weight=1) # Platz für die Liste

        ctk.CTkLabel(self.player_main_frame, text="SPIELER VERWALTUNG", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        # Erstellt das Eingabe-Frame und speichert die Entry-Widgets als Attribute
        self.player_input_frame = self._create_add_player_section(self.player_main_frame, row=1, col=0)
        
        # Erstellt den Container für die Spielerliste
        self._create_player_list_section(self.player_main_frame, row=2, col=0)
        
        # --- Team-Verwaltung (Rechte Spalte) ---
        self.team_frame = ctk.CTkFrame(self)
        self.team_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.team_frame.grid_columnconfigure(0, weight=1)
        self.team_frame.grid_rowconfigure(2, weight=1) # Platz für die Team-Liste

        ctk.CTkLabel(self.team_frame, text="TEAM VERWALTUNG", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        self._create_add_team_section(self.team_frame, row=1, col=0)
        self._create_team_list_section(self.team_frame, row=2, col=0)
        
        # Initialer Daten-Load
        self.load_team_list()
        self.load_player_list() 


    # --- Spieler-Sektionen ---

    def _create_add_player_section(self, master, row, col):
        """Erstellt die Eingabefelder zum Hinzufügen/Bearbeiten neuer Spieler."""
        add_frame = ctk.CTkFrame(master)
        add_frame.grid(row=row, column=col, sticky="ew", padx=10, pady=5)
        add_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(add_frame, text="Spieler erstellen / bearbeiten:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        
        # 1. Eingabe Name
        ctk.CTkLabel(add_frame, text="Name:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.player_name_entry = ctk.CTkEntry(add_frame, placeholder_text="Name") 
        self.player_name_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        # 2. Eingabe Trikotnummer
        ctk.CTkLabel(add_frame, text="Nr.:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.jersey_number_entry = ctk.CTkEntry(add_frame, placeholder_text="Nr.") 
        self.jersey_number_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        # 3. Eingabe Position
        ctk.CTkLabel(add_frame, text="Position:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.position_var = ctk.StringVar(value=VOLLEYBALL_POSITIONS[0]) 
        self.position_menu = ctk.CTkOptionMenu(add_frame, values=VOLLEYBALL_POSITIONS, variable=self.position_var)
        self.position_menu.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        
        # Hinzufügen/Speichern Button
        self.add_player_button = ctk.CTkButton(add_frame, text="Spieler hinzufügen", command=self.save_player_changes) 
        self.add_player_button.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

        # Bearbeitung abbrechen Button
        self.cancel_edit_button = ctk.CTkButton(add_frame, text="Bearbeitung abbrechen", command=self.cancel_editing, fg_color="gray")
        self.cancel_edit_button.grid(row=5, column=0, columnspan=2, padx=10, pady=5)
        self.cancel_edit_button.grid_remove() # Zuerst verstecken
        
        return add_frame


    def _create_player_list_section(self, master, row, col):
        """Erstellt den scrollbaren Container für die Liste der aktuellen Spieler."""
        list_frame = ctk.CTkFrame(master)
        list_frame.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.player_list_container = ctk.CTkScrollableFrame(list_frame, label_text="Alle Spieler")
        self.player_list_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.player_list_container.grid_columnconfigure(0, weight=1)
        self.player_list_container.grid_columnconfigure(1, weight=0) # Für den Bearbeiten-Button


    def load_player_list(self):
        """Lädt Spielerdetails aus der DB und aktualisiert die Liste mit allen Attributen."""
        # Lösche alte Widgets
        for widget in self.player_list_container.winfo_children():
            widget.destroy()
            
        # Lade Daten neu
        self.all_player_details = self.db_manager.get_all_players_details() 
        self.teams = self.db_manager.get_all_teams()
        
        for idx, (player_id, name, jersey_number, position, team_id) in enumerate(self.all_player_details):
            
            team_name = self.teams.get(team_id, "Kein Team") 
            jersey_display = f"#{jersey_number}" if jersey_number else "N/A"
            position_display = position if position else "Unbekannt"
            
            label_text = (f"[{player_id}] **{name}** ({jersey_display} / {position_display})\n"
                          f"Team: {team_name}")
            
            ctk.CTkLabel(self.player_list_container, 
                         text=label_text, 
                         anchor="w",
                         justify="left",
                         wraplength=300
                         ).grid(row=idx, column=0, sticky="ew", padx=5, pady=5)
                         
            # Bearbeiten Button
            edit_button = ctk.CTkButton(self.player_list_container, 
                                        text="Bearbeiten", 
                                        command=lambda pid=player_id: self.select_player_for_edit(pid),
                                        width=100)
            edit_button.grid(row=idx, column=1, padx=5, pady=5)


    def select_player_for_edit(self, player_id: int):
        """Lädt die Daten des ausgewählten Spielers in die Eingabefelder."""
        
        # Daten des Spielers aus der Liste der geladenen Details finden
        player_data = next((p for p in self.all_player_details if p[0] == player_id), None)
        
        if not player_data:
            print(f"Fehler: Spieler-ID {player_id} nicht in Details gefunden.")
            return

        # Speichere die ID, um den Bearbeitungsmodus zu aktivieren
        self.edit_player_id = player_id
        
        # Lade Daten in die Felder (Index 1=Name, 2=Nummer, 3=Position)
        self.player_name_entry.delete(0, "end")
        self.player_name_entry.insert(0, player_data[1])
        
        self.jersey_number_entry.delete(0, "end")
        self.jersey_number_entry.insert(0, str(player_data[2] or ""))
        
        self.position_var.set(player_data[3] or VOLLEYBALL_POSITIONS[0]) # Setze Dropdown-Wert

        # Aktualisiere den Button-Text und zeige den Abbrechen-Button
        self.add_player_button.configure(text="Spieler speichern")
        self.cancel_edit_button.grid()
        print(f"Spieler {player_data[1]} zum Bearbeiten geladen.")


    def cancel_editing(self):
        """Bricht den Bearbeitungsmodus ab und setzt die UI zurück."""
        self.edit_player_id = None
        
        # Felder leeren
        self.player_name_entry.delete(0, "end")
        self.jersey_number_entry.delete(0, "end")
        self.position_var.set(VOLLEYBALL_POSITIONS[0]) # Dropdown zurücksetzen

        # UI zurücksetzen
        self.add_player_button.configure(text="Spieler hinzufügen")
        self.cancel_edit_button.grid_remove()
        print("Bearbeitungsmodus abgebrochen.")


    def save_player_changes(self):
        """
        Speichert neue Spieler oder aktualisiert bestehende Spieler, 
        inklusive Eindeutigkeitsprüfung.
        """
        name = self.player_name_entry.get().strip()
        jersey_number_str = self.jersey_number_entry.get().strip()
        position = self.position_var.get()
        
        # Validierung 1: Name darf nicht leer sein
        if not name:
            print("Fehler: Name ist erforderlich!")
            return

        # Validierung 2: Trikotnummer
        try:
            jersey_number = int(jersey_number_str) if jersey_number_str else None
        except ValueError:
            print("Fehler: Trikotnummer muss eine ganze Zahl sein.")
            return

        # Validierung 3: Eindeutigkeitsprüfung
        if not self.db_manager.check_player_uniqueness(name, jersey_number, self.edit_player_id):
            print("Fehler: Ein Spieler mit diesem Namen ODER dieser Trikotnummer existiert bereits!")
            return
            
        
        if self.edit_player_id:
            # BEARBEITEN-MODUS
            success = self.db_manager.update_player(self.edit_player_id, name, jersey_number, position)
            if success:
                print(f"Spieler ID {self.edit_player_id} erfolgreich aktualisiert.")
                self.cancel_editing() # UI zurücksetzen
            else:
                print("FEHLER beim Aktualisieren des Spielers.")
        else:
            # HINZUFÜGEN-MODUS
            
            # Annahme: Wir fügen den Spieler zu Team 1 hinzu (dies müsste später wählbar sein)
            team_id = 1 
            
            new_player = Player(name=name, jersey_number=jersey_number, position=position)
            
            # Die Methode insert_player() muss das Player-Objekt und die team_id unterstützen
            success = self.db_manager.insert_player(new_player, team_id) 
            if success:
                print(f"Spieler '{name}' erfolgreich hinzugefügt.")
                self.cancel_editing() # Leert die Felder nach erfolgreichem Hinzufügen
            else:
                print("FEHLER beim Hinzufügen des Spielers.")

        self.load_player_list()
        
    # --- Team-Sektionen ---

    def _create_add_team_section(self, master, row, col):
        """Erstellt den Bereich zum Erstellen und Bearbeiten von Teams."""
        add_frame = ctk.CTkFrame(master)
        add_frame.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
        add_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(add_frame, text="Team Name:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.team_name_entry = ctk.CTkEntry(add_frame)
        self.team_name_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkButton(add_frame, text="Team erstellen", command=self.add_team).grid(row=1, column=0, columnspan=2, padx=10, pady=10)

        # Auswahl der Spieler für das Team (Bearbeitungsmodus)
        ctk.CTkLabel(add_frame, text="Team bearbeiten/Spieler zuweisen:").grid(row=2, column=0, columnspan=2, padx=10, pady=10)
        
        self.team_to_edit_var = ctk.StringVar(value="-- Team wählen --")
        self.team_to_edit_menu = ctk.CTkOptionMenu(add_frame, values=["-- Team wählen --"], variable=self.team_to_edit_var)
        self.team_to_edit_menu.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        
        # Player Checkbox Frame (Wird bei Team-Auswahl befüllt)
        self.team_player_select_frame = ctk.CTkScrollableFrame(add_frame, label_text="Spieler im Team")
        self.team_player_select_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.team_player_checkboxes: Dict[int, ctk.BooleanVar] = {}
        
        self.team_to_edit_menu.configure(command=self.display_team_players_for_edit)
        ctk.CTkButton(add_frame, text="Zuweisung speichern", command=self.save_team_player_assignment).grid(row=5, column=0, columnspan=2, padx=10, pady=10)


    def _create_team_list_section(self, master, row, col):
        """Erstellt den Bereich zur Anzeige der Team-Liste."""
        self.team_list_frame = ctk.CTkScrollableFrame(master, label_text="Alle Teams")
        self.team_list_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        self.team_list_frame.grid_columnconfigure(0, weight=1)
        self.team_list_widgets = []

    def add_team(self):
        """Erstellt ein neues Team in der DB."""
        name = self.team_name_entry.get().strip()
        if not name:
            print("Teamname darf nicht leer sein.")
            return

        team_id = self.db_manager.insert_team(name)
        if team_id:
            print(f"Team '{name}' erfolgreich erstellt mit ID {team_id}.")
            self.team_name_entry.delete(0, 'end')
            self.load_team_list()
            self.team_to_edit_var.set(name) # Wähle das neue Team direkt aus
            self.display_team_players_for_edit(name)

    def load_team_list(self):
        """Lädt alle Teams und aktualisiert die Anzeige und das Bearbeitungs-Dropdown."""
        # Teams für das Dropdown laden
        self.teams: Dict[int, str] = self.db_manager.get_all_teams()
        team_names = list(self.teams.values())
        self.team_to_edit_menu.configure(values=team_names if team_names else ["-- Kein Team --"])
        if not team_names:
            self.team_to_edit_var.set("-- Kein Team --")
            
        # Anzeige der Liste (Frame leeren)
        for widget in self.team_list_widgets:
            widget.destroy()
        self.team_list_widgets = []
        
        row = 0
        for team_id, name in self.teams.items():
            # KRITISCHE KORREKTUR: Spieler-Tupel haben jetzt 3 Elemente (ID, Name, Nr.)
            players = self.db_manager.get_team_players(team_id) 
            
            # Jetzt kann p[2] für die Trikotnummer verwendet werden
            player_names = ", ".join([f"{p[1]} (#{p[2]})" if p[2] else p[1] for p in players])
            
            label_text = f"[{team_id}] {name} ({len(players)} Spieler): {player_names}"
            # ... (Rest der Logik bleibt gleich)
            label = ctk.CTkLabel(self.team_list_frame, text=label_text, justify="left", wraplength=350)
            label.grid(row=row, column=0, padx=5, pady=2, sticky="w")
            self.team_list_widgets.append(label)
            row += 1
            
        # Lade alle Spieler, die für die Checkboxen benötigt werden
        self.all_player_details: List[Tuple[int, str, Optional[int], Optional[str], Optional[int]]] = self.db_manager.get_all_players_details()


    def display_team_players_for_edit(self, team_name):
        """Zeigt Checkboxen aller Spieler und markiert diejenigen des ausgewählten Teams."""
        
        # Frame leeren
        for widget in self.team_player_select_frame.winfo_children():
            widget.destroy()
        self.team_player_checkboxes = {}
        
        if team_name == "-- Team wählen --" or not team_name:
            return

        selected_team_id = next((k for k, v in self.teams.items() if v == team_name), None)
        if not selected_team_id:
            return

        row_idx = 0
        col_idx = 0
        
        # Die 5 Werte werden korrekt entpackt: (player_id, player_name, jersey_number, position, current_team_id)
        for player_id, player_name, jersey_number, position, current_team_id in self.all_player_details:
            
            # Prüfen, ob der Spieler bereits im ausgewählten Team ist
            is_checked = (current_team_id == selected_team_id)
            
            # Text für die Checkbox
            jersey_display = f"#{jersey_number}" if jersey_number else "N/A"
            checkbox_text = f"{player_name} ({jersey_display} / {position or 'N/A'})"
            
            var = ctk.BooleanVar(value=is_checked)
            cb = ctk.CTkCheckBox(self.team_player_select_frame, text=checkbox_text, variable=var)
            cb.grid(row=row_idx, column=col_idx, padx=10, pady=5, sticky="w")
            self.team_player_checkboxes[player_id] = var

            col_idx += 1
            if col_idx >= 2: # Max 2 Spalten
                col_idx = 0
                row_idx += 1

    def save_team_player_assignment(self):
        """Speichert die Zuweisung der Spieler zum ausgewählten Team."""
        team_name = self.team_to_edit_var.get()
        selected_team_id = next((k for k, v in self.teams.items() if v == team_name), None)
        
        if not selected_team_id:
            print("Fehler: Kein gültiges Team zum Speichern ausgewählt.")
            return

        players_to_assign = []
        players_to_unassign = []

        # Durchlaufen aller Spieler und prüfen, ob sie zugeordnet werden sollen
        for player_id, var in self.team_player_checkboxes.items():
            is_checked = var.get()
            
            # Finde den aktuellen Team-Zustand des Spielers in self.all_player_details
            current_player_team_id = next((p[4] for p in self.all_player_details if p[0] == player_id), None)
            
            if is_checked and current_player_team_id != selected_team_id:
                # Spieler wurde ausgewählt, muss zugewiesen werden
                players_to_assign.append(player_id)
            elif not is_checked and current_player_team_id == selected_team_id:
                # Spieler wurde abgewählt, muss von diesem Team entfernt werden (Team ID auf NULL/0 setzen)
                players_to_unassign.append(player_id)


        # Zuweisungs-Aktionen durchführen
        for player_id in players_to_assign:
            self.db_manager.update_player_team(player_id, selected_team_id)
            
        # Spieler, die abgewählt wurden, auf 'Kein Team' (NULL in der DB) setzen
        for player_id in players_to_unassign:
            # Annahme: update_player_team(id, None) setzt die Team-ID auf NULL
            self.db_manager.update_player_team(player_id, None) 

        print(f"Zuweisungen für Team '{team_name}' gespeichert.")
        self.load_player_list()
        self.load_team_list()