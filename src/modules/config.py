# src/modules/config.py

import os
import sys

# Pfad zur SQLite-Datenbank
if getattr(sys, 'frozen', False):
# App läuft als PyInstaller-Exe
    BASE_DIR = sys._MEIPASS
else:
# App läuft im Entwicklungsmodus
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Datenbankpfad: Wird im 'resources/db' Ordner innerhalb des BASE_DIR gesucht
DB_FOLDER = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), 'resources', 'db')
DB_PATH = os.path.join(DB_FOLDER, 'stats.db')

# --- Allgemeine Konstanten ---

# Rollen und Aktionen (für GUI und Validierung)
ACTION_TYPES = {
    'Zuspiel': ['Gut', 'Mittel',"Schlecht", 'Fehler'],
    'Angriff': ['Kill', 'Halber',"lob","smart","Gepritscht",  'Fehler', 'Blockiert'],
    'Aufschlag': ['Ass',"Halbes", 'Ins Feld', 'Fehler'],
    'Block': ['Punkt', 'Fehler']
}

POINT_FOR = {
    'Eigenes Team': 'OWN',
    'Gegner': 'OPP'
}

# NEU: Konstanten für Volleyball-Positionen
VOLLEYBALL_POSITIONS = [
    "Mitte", 
    "Außen", 
    "Diagonal", 
    "Zuspiel", 
    "Libero", 
    "Universal"
]

# --- NEU: POINT MAPPING ZUR KORREKTEN PUNKTEVERGABE ---
POINT_MAPPING = {
    # 1. Direkte eigene Punkte (OWN)
    ("Kill", "Angriff"): "OWN", 
    ("Block", "Punkt"): "OWN", 
    ("Ass", "Aufschlag"): "OWN",
    ("Unser Punkt", "Unser Punkt"): "OWN", # Spezieller Fall für 'Unser Punkt' Button
    
    # 2. Direkte gegnerische Punkte (OPP) durch eigenen Fehler
    ("Fehler", "Angriff"): "OPP",
    ("Fehler", "Aufschlag"): "OPP",
    ("Blockiert", "Angriff"): "OPP", # Block vom Gegner = Punkt Gegner
    ("Fehler", "Zuspiel"): "OPP",
    ("Fehler", "Block"): "OPP",
    
    # Alle anderen Resultate (Halber, Gut, Mittel, Ins Feld, lob, smart, Gepritscht) lösen keinen Punkt aus.
}

POINT_DETAIL_OUTCOMES = {
    "Punkt am Netz (Angriff)": "P_ATTACK",
    "Punkt am Netz (Block)": "P_BLOCK",
    
    # Details zum Boden/Fehler
    "Boden Gegner (Punktgewinn)": "P_OPP_FLOOR_ERR",
    "Boden wir (Punktverlust)": "P_OWN_FLOOR_ERR",
    
    # Details zur Sicherung/Kontrolle (könnten später im GameController als "halbe Punkte" behandelt werden)
    "Sicherung Gegner (Kontrolle)": "S_OPP_SAVE",
    "Sicherung wir (Kontrolle)": "S_OWN_SAVE",
}