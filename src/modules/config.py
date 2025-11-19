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