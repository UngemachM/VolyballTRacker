# src/modules/gui/set_end_dialog.py

import customtkinter as ctk
from typing import Callable

class SetEndDialog(ctk.CTkToplevel):
    """
    Dialog, der bei Satzende erscheint. Bietet Optionen: Nächster Satz starten oder Spiel beenden.
    """
    def __init__(self, master, winning_score: int, losing_score: int, callback_next_set: Callable, callback_end_game: Callable):
        super().__init__(master)
        
        self.title("Satz beendet!")
        self.geometry("400x200")
        self.transient(master)
        self.grab_set()
        
        self.callback_next_set = callback_next_set
        self.callback_end_game = callback_end_game
        
        self.grid_columnconfigure((0, 1), weight=1)
        
        message = (f"SATZ ENDE: {winning_score} - {losing_score}.\n"
                   f"Wie soll es weitergehen?")
        
        ctk.CTkLabel(self, text=message, font=ctk.CTkFont(weight="bold", size=14), justify="center").grid(row=0, column=0, columnspan=2, padx=20, pady=15)
        
        # Button: Nächster Satz
        ctk.CTkButton(self, text="▶️ Nächsten Satz starten", command=self.on_next_set, fg_color="green").grid(row=1, column=0, padx=10, pady=10)
        
        # Button: Spiel beenden
        ctk.CTkButton(self, text="🏁 Spiel beenden", command=self.on_end_game, fg_color="red").grid(row=1, column=1, padx=10, pady=10)

    def on_next_set(self):
        """Ruft den Callback zum Starten des nächsten Satzes auf und schließt den Dialog."""
        self.destroy()
        self.callback_next_set() 

    def on_end_game(self):
        """Ruft den Callback zum Beenden des Spiels auf und schließt den Dialog."""
        self.destroy()
        self.callback_end_game()