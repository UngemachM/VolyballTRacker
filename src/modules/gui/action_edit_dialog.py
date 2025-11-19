# src/modules/gui/action_edit_dialog.py

import customtkinter as ctk
from typing import Dict, Optional, Any, Tuple
from ..config import ACTION_TYPES 

class ActionEditDialog(ctk.CTkToplevel):
    """
    Pop-up-Fenster zur Bearbeitung oder Löschung einer bestehenden Aktion.
    Verwendet den direkt übergebenen app_controller.
    """
    def __init__(self, master, app_controller, action_id: int, details: Dict[str, Any], players: Dict[int, str], callback):
        super().__init__(master)
        
        self.app_controller = app_controller # Speichere den Controller direkt
        
        self.title(f"Aktion bearbeiten (ID: {action_id})")
        self.geometry("400x450")
        self.transient(master)
        self.grab_set()
        
        self.action_id = action_id
        self.details = details # Enthält action_type, executor_id, result_type, target_id, set_id etc.
        self.players = players
        self.callback = callback 
        
        # UI-Elemente
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        action_name = self.details.get('action_type', 'Unbekannt')
        executor_id = self.details.get('executor_player_id')

        ctk.CTkLabel(self, text=f"Typ: {action_name}", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=20, pady=10)
        
        self._setup_executor_selection(executor_id)
        self._setup_result_selection(action_name)
        self._setup_target_selection(action_name)
        
        # --- Bestätigungs- und Löschbuttons ---
        ctk.CTkButton(self, text="Änderung Speichern", command=self.on_submit, fg_color="green").grid(row=5, column=0, padx=5, pady=20)
        ctk.CTkButton(self, text="Aktion Löschen", command=self.on_delete, fg_color="red").grid(row=5, column=1, padx=5, pady=20)

    def _setup_executor_selection(self, current_id: int):
        """Erstellt die Auswahl für den ausführenden Spieler."""
        player_names = list(self.players.values())
        
        try:
            current_name = self.players[current_id]
        except KeyError:
             current_name = player_names[0] if player_names else "Fehler"

        ctk.CTkLabel(self, text="Spieler ändern:").grid(row=1, column=0, sticky="w", padx=20, pady=5)
        
        self.executor_var = ctk.StringVar(value=current_name)
        self.executor_menu = ctk.CTkOptionMenu(self, values=player_names, variable=self.executor_var)
        self.executor_menu.grid(row=1, column=1, sticky="ew", padx=20, pady=5)


    def _setup_result_selection(self, action_name: str):
        """Erstellt die Auswahl für den Ergebnis-Typ (Result_Type)."""
        
        # Annahme: ACTION_TYPES ist ein Dict, z.B. {'Angriff': ['Kill', 'Fehler', 'Halbes']}
        result_options = ACTION_TYPES.get(action_name, ["Gut", "Fehler"]) 
        current_result = self.details.get('result_type')
        
        if not current_result or current_result not in result_options:
            current_result = result_options[0] if result_options else ""

        ctk.CTkLabel(self, text="Ergebnis-Typ:").grid(row=2, column=0, sticky="w", padx=20, pady=5)
        
        self.result_var = ctk.StringVar(value=current_result)
        self.result_menu = ctk.CTkOptionMenu(self, values=result_options, variable=self.result_var)
        self.result_menu.grid(row=2, column=1, sticky="ew", padx=20, pady=5)


    def _setup_target_selection(self, action_name: str):
        """Erstellt die Auswahl für den Zielspieler (nur für 'Zuspiel' relevant)."""
        
        if action_name != "Zuspiel":
            self.target_name_var = None
            return

        ctk.CTkLabel(self, text="Zielspieler (Zuspiel zu):").grid(row=3, column=0, sticky="w", padx=20, pady=5)
        
        player_names = ["-- Kein Ziel --"] + list(self.players.values())
        current_target_id = self.details.get('target_player_id')
        current_target_name = self.players.get(current_target_id, "-- Kein Ziel --")
        
        self.target_name_var = ctk.StringVar(value=current_target_name)
        self.target_menu = ctk.CTkOptionMenu(self, values=player_names, variable=self.target_name_var)
        self.target_menu.grid(row=3, column=1, sticky="ew", padx=20, pady=5)


    def on_submit(self):
        """Sammelt die geänderten Daten und ruft den GameController zur Aktualisierung auf."""
        
        new_executor_name = self.executor_var.get()
        new_executor_id = next((k for k, v in self.players.items() if v == new_executor_name), None)
        
        new_target_id: Optional[int] = None
        if self.target_name_var:
            target_name = self.target_name_var.get()
            if target_name != "-- Kein Ziel --":
                new_target_id = next((k for k, v in self.players.items() if v == target_name), None)

        updated_data = {
            "action_id": self.action_id,
            "executor_id": new_executor_id,
            "result_type": self.result_var.get(),
            "target_id": new_target_id
        }
        
        # NEU: Zugriff über den gespeicherten Controller
        success = self.app_controller.get_game_controller().update_action(updated_data)
        
        self.callback(success)
        self.destroy()

    def on_delete(self):
        """Löscht die aktuelle Aktion."""
        
        # NEU: Zugriff über den gespeicherten Controller
        success = self.app_controller.get_game_controller().delete_action(self.action_id)

        self.callback(success)
        self.destroy()

    def on_close(self):
        """Wird aufgerufen, wenn der Dialog geschlossen wird, ohne zu speichern."""
        self.destroy()