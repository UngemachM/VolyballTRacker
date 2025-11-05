# src/modules/gui/action_dialog.py

import customtkinter as ctk
from typing import Dict, List, Optional
# Importieren von Konstanten aus der Konfigurationsdatei
from ..config import ACTION_TYPES 

class ActionDialog(ctk.CTkToplevel):
    """
    Pop-up-Fenster zur Erfassung von Details (Result_Type und Target_Player)
    für komplexe Aktionen wie Angriff, Aufschlag und Zuspiel.
    """
    def __init__(self, master, executor_id: int, action_name: str, players: Dict[int, str], callback):
        super().__init__(master)
        
        self.title(f"Aktion: {action_name}")
        self.geometry("300x350")
        self.transient(master)  # Hält den Dialog über dem Hauptfenster
        self.grab_set()         # Blockiert Interaktion mit dem Hauptfenster
        
        self.executor_id = executor_id
        self.action_name = action_name
        self.players = players
        self.callback = callback # Funktion in InputView, die die Daten verarbeitet
        self.result_data = None
        
        # UI-Elemente
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text=f"Spieler: {self.players.get(executor_id)}", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=20, pady=10)
        
        self._setup_result_selection()
        self._setup_target_selection()
        
        # Bestätigungsbutton
        ctk.CTkButton(self, text="Speichern", command=self.on_submit).grid(row=5, column=0, columnspan=2, pady=20)

    def _setup_result_selection(self):
        """Erstellt die Auswahl für den Ergebnis-Typ (z.B. Kill, Fehler, Halbes)."""
        
        # Holen der Optionen aus config.py
        result_options = ACTION_TYPES.get(self.action_name, ["Gut", "Fehler"]) 
        
        ctk.CTkLabel(self, text="Ergebnis-Typ:").grid(row=1, column=0, sticky="w", padx=20, pady=5)
        
        self.result_var = ctk.StringVar(value=result_options[0])
        self.result_menu = ctk.CTkOptionMenu(self, values=result_options, variable=self.result_var)
        self.result_menu.grid(row=1, column=1, sticky="ew", padx=20, pady=5)

    def _setup_target_selection(self):
        """Erstellt die Auswahl für den Zielspieler ('Zuspiel zu')."""
        
        # Das Zielfeld ist nur für 'Zuspiel' relevant
        if self.action_name != "Zuspiel":
            self.target_id_var = None
            return

        ctk.CTkLabel(self, text="Zuspiel zu:").grid(row=2, column=0, sticky="w", padx=20, pady=5)
        
        # Füge alle Spielernamen zur Dropdown-Liste hinzu
        player_names = ["-- Kein Ziel --"] + list(self.players.values())
        
        self.target_name_var = ctk.StringVar(value=player_names[0])
        self.target_menu = ctk.CTkOptionMenu(self, values=player_names, variable=self.target_name_var)
        self.target_menu.grid(row=2, column=1, sticky="ew", padx=20, pady=5)

    def on_submit(self):
        """Sammelt die Daten und ruft den Callback in InputView auf."""
        
        result_type = self.result_var.get()
        target_id: Optional[int] = None

        if self.action_name == "Zuspiel":
            # Finde die Spieler-ID basierend auf dem gewählten Namen
            target_name = self.target_name_var.get()
            if target_name != "-- Kein Ziel --":
                # Reverse lookup der ID
                target_id = next((k for k, v in self.players.items() if v == target_name), None)

        self.result_data = {
            "executor_id": self.executor_id,
            "action_type": self.action_name,
            "result_type": result_type,
            "target_id": target_id
        }
        
        self.callback(self.result_data)
        self.destroy() 

    def on_close(self):
        """Wird aufgerufen, wenn der Dialog geschlossen wird, ohne zu speichern."""
        self.destroy()