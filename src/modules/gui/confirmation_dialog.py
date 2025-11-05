# src/modules/gui/confirmation_dialog.py

import customtkinter as ctk

class ConfirmationDialog(ctk.CTkToplevel):
    """
    Ein einfacher Dialog zur Bestätigung einer Aktion (Ja/Nein).
    """
    def __init__(self, master, message: str, callback):
        super().__init__(master)
        
        self.title("Bestätigung erforderlich")
        self.geometry("350x150")
        self.transient(master)
        self.grab_set()
        
        self.callback = callback
        
        self.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(self, text=message, wraplength=300).grid(row=0, column=0, columnspan=2, padx=20, pady=15)
        
        # Ja Button
        ctk.CTkButton(self, text="Ja", command=lambda: self.on_response(True), fg_color="red", hover_color="darkred").grid(row=1, column=0, padx=10, pady=10)
        
        # Nein Button
        ctk.CTkButton(self, text="Nein", command=lambda: self.on_response(False)).grid(row=1, column=1, padx=10, pady=10)

    def on_response(self, confirmed: bool):
        """Übergibt die Antwort an den Callback und schließt den Dialog."""
        self.callback(confirmed)
        self.destroy()
        
    def on_close(self):
        """Behandelt das Schließen des Fensters (als Nein gewertet)."""
        self.on_response(False)