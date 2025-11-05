# src/modules/gui/start_dialog.py

import customtkinter as ctk
from typing import Dict, List, Tuple, Any

class StartGameDialog(ctk.CTkToplevel):
    """
    Dialog zur Auswahl des eigenen Teams, Eingabe des Gegners und Auswahl der Spieler.
    """
    def __init__(self, master, app_controller, teams: Dict[int, str], players: Dict[int, str], callback):
        super().__init__(master)
        
        self.title("Neues Spiel starten")
        self.geometry("700x500")
        self.transient(master)
        self.grab_set()
        
        self.app_controller = app_controller
        self.game_controller = app_controller.get_game_controller()
        self.callback = callback
        
        self.teams = teams # {ID: Name}
        self.all_players = players # {ID: Name}
        self.selected_player_ids = []
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # --- Teams und Gegnername ---
        self._setup_team_selection()
        
        # --- Spieler-Auswahl (Linke Seite) ---
        self._setup_player_selection()
        
        # --- Start Button ---
        ctk.CTkButton(self, text="▶️ Spiel starten & speichern", 
                      command=self.start_game_and_save).grid(row=4, column=0, columnspan=2, pady=20)

    def _setup_team_selection(self):
        # 1. Eigenes Team auswählen
        ctk.CTkLabel(self, text="1. Eigenes Team:").grid(row=0, column=0, sticky="w", padx=20, pady=5)
        team_names = list(self.teams.values())
        self.team_var = ctk.StringVar(value=team_names[0] if team_names else "Kein Team gefunden")
        self.team_menu = ctk.CTkOptionMenu(self, values=team_names, variable=self.team_var)
        self.team_menu.grid(row=0, column=1, sticky="ew", padx=20, pady=5)
        
        # 2. Gegnernamen eingeben
        ctk.CTkLabel(self, text="2. Gegnername:").grid(row=1, column=0, sticky="w", padx=20, pady=5)
        self.opponent_entry = ctk.CTkEntry(self, placeholder_text="Name des gegnerischen Teams")
        self.opponent_entry.grid(row=1, column=1, sticky="ew", padx=20, pady=5)

    def _setup_player_selection(self):
        ctk.CTkLabel(self, text="3. Spieler auswählen (im Spiel):", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, columnspan=2, sticky="w", padx=20, pady=10)
        
        self.player_frame = ctk.CTkScrollableFrame(self, label_text="Verfügbare Spieler")
        self.player_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=20, pady=10)
        
        # Checkboxen für jeden Spieler
        self.checkboxes: Dict[int, ctk.CTkCheckBox] = {}
        for idx, (player_id, player_name) in enumerate(self.all_players.items()):
            var = ctk.BooleanVar(value=False)
            cb = ctk.CTkCheckBox(self.player_frame, text=player_name, variable=var)
            cb.grid(row=idx // 3, column=idx % 3, padx=10, pady=5, sticky="w")
            self.checkboxes[player_id] = cb

    def start_game_and_save(self):
        """Verarbeitet die Eingaben und startet das Spiel."""
        
        own_team_name = self.team_var.get()
        opponent_name = self.opponent_entry.get().strip()
        
        if not opponent_name:
            # Fehlerbehandlung
            return

        # 1. Gewähltes Team und Gegner vorbereiten
        own_team_id = next((k for k, v in self.teams.items() if v == own_team_name), None)
        
        # Erstelle Gegner-Team und Dummy-Spieler
        game_id = self.game_controller.start_new_game(
            own_team_id=own_team_id, 
            opponent_name=opponent_name
        )
        
        # 2. Ausgewählte Spieler erfassen
        self.selected_player_ids = [
            p_id for p_id, cb in self.checkboxes.items() if cb.get()
        ]
        
        # 3. Spieler zum Spiel hinzufügen (WICHTIG!)
        self.game_controller.add_players_to_active_game(self.selected_player_ids)
        
        # 4. Callback aufrufen und Dialog schließen
        self.callback(game_id)
        self.destroy()