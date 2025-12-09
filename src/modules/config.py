# src/config.py

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
    'Block': ['Punkt', 'Fehler','Touch'],
    'Sicherung': ['Gut', 'Fehler']
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

# --- NEU: Detail-Optionen für Punkte (für PointDetailDialog) ---
POINT_DETAIL_OUTCOMES = {
    
    "Block": "BLOCK",
    "Sicherung Gegner": "OPP_SAVE",
    "Touch": "Touch",
    "Fehler":"Fehler"
}

# --- NEU: Punktewertungen (Fallback/Direkt-Aktionen) ---
POINT_MAPPING = {
    ("Kill", "Angriff"): "OWN", 
    ("Block", "Punkt"): "OWN", 
    ("Ass", "Aufschlag"): "OWN",
    ("Unser Punkt", "Unser Punkt"): "OWN", 
    
    ("Fehler", "Angriff"): "OPP",
    ("Fehler", "Aufschlag"): "OPP",
    ("Blockiert", "Angriff"): "OPP", 
    ("Fehler", "Zuspiel"): "OPP",
    ("Fehler", "Block"): "OPP",
    ("Touch", "Block"): None,
}

# --- KRITISCHE KORREKTUR: Mapping der Detailcodes zur finalen Punktzuweisung (für GameController) ---
POINT_DETAIL_CODE_MAPPING = {
    # Punkte für das EIGENE TEAM
    "P_ATTACK": "OWN",        
    "P_BLOCK": "OWN",         
    "P_OPP_FLOOR_ERR": "OWN", 
    
    # PUNKT FÜR DEN GEGNER
    "P_OWN_FLOOR_ERR": "OPP", 

    # Keine Punkte
    "S_OPP_SAVE": None,
    "S_OWN_SAVE": None,
}