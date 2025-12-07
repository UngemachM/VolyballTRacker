# src/modules/gui/point_detail_dialog.py

import customtkinter as ctk
from typing import Dict, Callable
from ..config import POINT_DETAIL_OUTCOMES

class PointDetailDialog(ctk.CTkToplevel):
    """
    Pop-up-Fenster zur Erfassung von Punkt-Detailinformationen, 
    wie vom Benutzer gewünscht (Boden, Sicherung etc.).
    """
    def __init__(self, master, action_type: str, callback: Callable[[str], None]):
        super().__init__(master)
        
        self.title("Punktdetails erfassen")
        self.geometry("300x350")
        self.transient(master)  
        self.grab_set()         
        
        self.callback = callback 
        
        # UI-Elemente
        self.grid_columnconfigure(0, weight=1)

        # Titel
        ctk.CTkLabel(self, text=f"Detail für: {action_type}", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=20, pady=(10, 5))
        ctk.CTkLabel(self, text="Punkt-Detail auswählen:").grid(row=1, column=0, sticky="w", padx=20, pady=5)
        
        # Optionen vorbereiten
        self.options = list(POINT_DETAIL_OUTCOMES.keys())
        
        self.detail_var = ctk.StringVar(value=self.options[0])
        self.detail_menu = ctk.CTkOptionMenu(self, values=self.options, variable=self.detail_var)
        self.detail_menu.grid(row=2, column=0, sticky="ew", padx=20, pady=5)

        # Submit Button
        ctk.CTkButton(self, text="Speichern", command=self.on_submit).grid(row=3, column=0, padx=20, pady=20)

    def on_submit(self):
        """Sammelt die Daten und ruft den Callback auf."""
        selected_key = self.detail_var.get()
        # Hole den Code (z.B. P_OPP_FLOOR_ERR)
        detail_code = POINT_DETAIL_OUTCOMES.get(selected_key, "UNKNOWN")
        
        self.callback(detail_code)
        self.destroy()