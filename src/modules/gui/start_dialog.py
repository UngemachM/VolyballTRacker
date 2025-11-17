# src/modules/gui/start_dialog.py

import customtkinter as ctk
from typing import Dict, List, Tuple, Any

class StartGameDialog(ctk.CTkToplevel):
    """
    Dialog zur Auswahl des eigenen Teams, Eingabe des Gegners und Auswahl der Spieler.
    """
    def __init__(self, master, app_controller, teams: Dict[int, str], players: List[Tuple], callback):
        super().__init__(master)
        
        self.title("Neues Spiel starten")
        self.geometry("700x500")
        self.transient(master)
        self.grab_set()
        
        self.app_controller = app_controller
        self.game_controller = app_controller.get_game_controller()
        self.callback = callback
        
        self.teams = teams 
        # players: List[Tuple[ID, Name, Nr., Pos., Team-ID]]
        self.all_player_details = players 
        self.selected_player_ids = []
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # --- Teams und Gegnername ---
        self._setup_team_selection()
        
        # --- Spieler-Auswahl ---
        self._setup_player_selection()
        
        # KRITISCHE KORREKTUR: Spielerliste für das initial ausgewählte Team laden
        initial_team_name = self.team_var.get()
        if initial_team_name not in ["Kein Team gefunden", "-- Team wählen --"]:
            self.update_player_selection_based_on_team(initial_team_name)
        
        # --- Start Button ---
        ctk.CTkButton(self, text="▶️ Spiel starten & speichern", 
                      command=self.start_game_and_save).grid(row=4, column=0, columnspan=2, pady=20)

    def _setup_team_selection(self):
        # 1. Eigenes Team auswählen
        ctk.CTkLabel(self, text="1. Eigenes Team:").grid(row=0, column=0, sticky="w", padx=20, pady=5)
        
        team_names = list(self.teams.values())
        initial_value = team_names[0] if team_names else "Kein Team gefunden"
        
        self.team_var = ctk.StringVar(value=initial_value)
        
        self.team_menu = ctk.CTkOptionMenu(
            self, 
            values=team_names if team_names else [initial_value], 
            variable=self.team_var,
            command=self.update_player_selection_based_on_team 
        )
        self.team_menu.grid(row=0, column=1, sticky="ew", padx=20, pady=5)
        
        # 2. Gegnernamen eingeben
        ctk.CTkLabel(self, text="2. Gegnername:").grid(row=1, column=0, sticky="w", padx=20, pady=5)
        self.opponent_entry = ctk.CTkEntry(self, placeholder_text="Name des gegnerischen Teams")
        self.opponent_entry.grid(row=1, column=1, sticky="ew", padx=20, pady=5)

    def _setup_player_selection(self):
        ctk.CTkLabel(self, text="3. Spieler auswählen (im Spiel):", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, columnspan=2, sticky="w", padx=20, pady=10)
        
        self.player_frame = ctk.CTkScrollableFrame(self, label_text="Verfügbare Spieler")
        self.player_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=20, pady=10)
        
        self.checkboxes: Dict[int, ctk.CTkCheckBox] = {}


    def update_player_selection_based_on_team(self, team_name):
        """
        Filtert die Spielerliste basierend auf dem ausgewählten Team und 
        füllt das ScrollableFrame neu.
        """
        
        # 1. Frame leeren
        for widget in self.player_frame.winfo_children():
            widget.destroy()
        self.checkboxes = {}

        # 2. Gewählte Team-ID ermitteln
        selected_team_id = next((k for k, v in self.teams.items() if v == team_name), None)
        
        if not selected_team_id:
            ctk.CTkLabel(self.player_frame, text="Bitte Team wählen oder in Verwaltung anlegen.").grid(row=0, column=0, padx=10, pady=10)
            return

        # 3. Filterung und Anzeige
        row_idx = 0
        col_idx = 0
        
        # Filtern nach der Team-ID des Spielers (Index 4 des Tupels)
        # Tupel-Struktur: (ID, Name, Nr., Pos., Team-ID)
        filtered_players = [
            (pid, name, jnum, pos) 
            for pid, name, jnum, pos, tid in self.all_player_details 
            if tid == selected_team_id
        ]
        
        if not filtered_players:
            ctk.CTkLabel(self.player_frame, text="Keine Spieler in diesem Team registriert. Bitte in Verwaltung zuweisen.").grid(row=0, column=0, padx=10, pady=10)
            return
            
        for player_id, player_name, jersey_number, position in filtered_players:
            
            jersey_display = f"#{jersey_number}" if jersey_number else "N/A"
            checkbox_text = f"{player_name} ({jersey_display})"
            
            var = ctk.BooleanVar(value=False)
            cb = ctk.CTkCheckBox(self.player_frame, text=checkbox_text, variable=var)
            cb.grid(row=row_idx, column=col_idx, padx=10, pady=5, sticky="w")
            self.checkboxes[player_id] = cb

            col_idx += 1
            if col_idx >= 3: 
                col_idx = 0
                row_idx += 1

    def start_game_and_save(self):
        """Verarbeitet die Eingaben und startet das Spiel."""
        
        own_team_name = self.team_var.get()
        opponent_name = self.opponent_entry.get().strip()
        
        if not opponent_name:
            print("Fehler: Gegnername darf nicht leer sein.")
            return
        
        if not self.checkboxes:
            print("Fehler: Bitte wählen Sie mindestens einen Spieler aus dem Team.")
            return

        # 1. Gewähltes Team und Gegner vorbereiten
        own_team_id = next((k for k, v in self.teams.items() if v == own_team_name), None)
        
        game_id = self.game_controller.start_new_game(
            own_team_id=own_team_id, 
            opponent_name=opponent_name
        )
        
        # 2. Ausgewählte Spieler erfassen
        self.selected_player_ids = [
            p_id for p_id, cb in self.checkboxes.items() if cb.get()
        ]
        
        # 3. Spieler zum Spiel hinzufügen
        self.game_controller.add_players_to_active_game(self.selected_player_ids)
        
        # 4. Callback aufrufen und Dialog schließen
        self.callback(game_id)
        self.destroy()