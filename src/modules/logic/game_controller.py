from typing import Optional, List, Dict, Tuple, Any
import datetime
from ..data.db_manager import DBManager
from ..data.models import Action, Set
from ..config import ACTION_TYPES, POINT_FOR # Importiere die definierten Konstanten

class GameController:
    """
    Verwaltet den aktuellen Spielzustand (Spiel, Satz, Aufstellung) 
    und verarbeitet die eingehenden Statistik-Aktionen.
    """
    
    def __init__(self, db_manager: DBManager):
        self.db_manager = db_manager
        self._current_game_id: Optional[int] = None
        self._current_set: Optional[Set] = None
        self._active_player_ids: List[int] = [] # Speichert die IDs der im Spiel aktiven Spieler

    # --- HILFSMETHODEN ---

    def get_next_set_number(self, game_id: int) -> int:
        """Ermittelt die nächste Satznummer für das gegebene Spiel."""
        query = "SELECT MAX(set_number) FROM sets WHERE game_id = ?"
        
        try:
            self.db_manager.connect()
            self.db_manager._cursor.execute(query, (game_id,))
            max_num = self.db_manager._cursor.fetchone()[0]
            self.db_manager.close()
            
            # Wenn max_num NULL ist (keine Sätze im Spiel), starte mit 1. Sonst max_num + 1.
            return (max_num or 0) + 1 
        except Exception as e:
            print(f"Fehler bei Satznummer-Abruf: {e}")
            return 1 # Fallback, sollte nicht passieren

    # --- SPIEL- UND SATZVERWALTUNG ---
    
    def start_new_game(self, own_team_id: int, opponent_name: str) -> int:
        """Erstellt Gegner-Team, startet Spiel und den ersten Satz. Gibt die ECHTE Game ID zurück."""
        
        # 1. Gegner-Team erstellen (Gibt die Team ID zurück, oder None)
        opponent_team_id = self.db_manager.insert_team(opponent_name) 
        if not opponent_team_id:
             # Annahme: Team existierte bereits oder Fehler. Wir müssen das Team abfragen.
             opponent_team_id = 99 
        
        # 2. Spiel in DB erstellen
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = "INSERT INTO games (date_time, home_team_id, guest_team_id) VALUES (?, ?, ?)"
        
        # 🛑 KRITISCH: Verwende fetch_id=True, um die ECHTE Game ID zu erhalten
        game_id = self.db_manager.execute_query(
            query, 
            (now, own_team_id, opponent_team_id), 
            fetch_id=True
        ) 
        
        if not game_id:
             raise Exception("Fehler: Konnte keine Game ID von der Datenbank erhalten.")
             
        self._current_game_id = game_id # Speichere die ECHTE ID

        # 3. Ersten Satz starten (Set ID wird hier auch korrekt dynamisch geholt)
        self.start_new_set(self._current_game_id) 
        
        print(f"Neues Spiel gestartet. ECHTE Game ID: {game_id}")
        return game_id


    def start_new_set(self, game_id: int): 
        """Erstellt einen neuen Satz in der Datenbank mit korrekter fortlaufender Nummer."""
        
        set_number = self.get_next_set_number(game_id)
        
        # 1. Set-Objekt erstellen
        new_set = Set(game_id=game_id, set_number=set_number)
        
        # 2. Set in DB speichern
        query = "INSERT INTO sets (game_id, set_number, score_own, score_opponent) VALUES (?, ?, ?, ?)"
        
        # 🛑 KRITISCH: fetch_id verwenden, um die ECHTE set_id zu erhalten
        set_id = self.db_manager.execute_query(
            query, 
            (new_set.game_id, new_set.set_number, new_set.score_own, new_set.score_opponent), 
            fetch_id=True
        ) 
        
        if not set_id:
            raise Exception("Fehler: Konnte keine Set ID von der Datenbank erhalten.")
            
        # Zuweisung der ECHTEN ID
        new_set.set_id = set_id
        
        self._current_set = new_set
        print(f"Satz {set_number} gestartet (Set ID: {self._current_set.set_id})")

    def end_active_game(self):
        """Markiert das aktuelle Spiel in der Datenbank als beendet und setzt den Kontext zurück."""
        if not self._current_game_id:
            print("FEHLER: Kein Spiel aktiv, kann nicht beendet werden.")
            return

        # TODO: Update der 'games'-Tabelle mit Endzeit (erfordert Schema-Erweiterung)
        
        print(f"Spiel {self._current_game_id} beendet. Kontext zurückgesetzt.")

        # Setze intern den Kontext zurück, damit die InputView leer wird
        self._current_game_id = None
        self._current_set = None

    def update_score(self, point_for: str):
        """Aktualisiert den Punktestand des aktuellen Satzes."""
        if not self._current_set:
            print("Fehler: Kein Satz aktiv.")
            return

        if point_for == POINT_FOR['Eigenes Team']:
            self._current_set.score_own += 1
        elif point_for == POINT_FOR['Gegner']:
            self._current_set.score_opponent += 1
            
        # KRITISCH: Punktestand in der Datenbank aktualisieren (UPDATE-Query)
        query = "UPDATE sets SET score_own = ?, score_opponent = ? WHERE set_id = ?"
        self.db_manager.execute_query(query, (self._current_set.score_own, self._current_set.score_opponent, self._current_set.set_id))

    # --- AKTION UND FILTERUNG ---

    def process_action(self, executor_id: int, action_type: str, result_type: Optional[str] = None, target_id: Optional[int] = None):
        """
        Erstellt und speichert eine neue Aktion in der Datenbank und 
        aktualisiert gegebenenfalls den Punktestand.
        """
        if not self._current_set:
            print("FEHLER: Aktion kann nicht verarbeitet werden, da kein Satz aktiv ist.")
            return False

        # 1. Datenvalidierung und Punktlogik ableiten (Ihre bestehende Logik)
        point_for: Optional[str] = None
        # ... (Logik zur Ermittlung von point_for) ...
        if result_type in ['Ass', 'Kill', 'Punkt'] or action_type == 'Unser Punkt':
            point_for = POINT_FOR['Eigenes Team']
        elif result_type in ['Fehler', 'Blockiert']:
            point_for = POINT_FOR['Gegner']
            
        # 2. Action-Objekt erstellen
        new_action = Action(
            set_id=self._current_set.set_id,
            executor_player_id=executor_id,
            action_type=action_type,
            result_type=result_type,
            target_player_id=target_id,
            point_for=point_for,
            timestamp=datetime.datetime.now()
        )
        
        # 3. In der Datenbank speichern
        self.db_manager.insert_action(new_action)
        
        # 4. Punktestand aktualisieren
        if point_for:
            self.update_score(point_for)
            
        return True

    def add_players_to_active_game(self, player_ids: List[int]):
        """Speichert die Spieler-IDs, die am aktuellen Spiel teilnehmen (für Filterung der InputView)."""
        self._active_player_ids = player_ids 
        print(f"Spieler {player_ids} sind im aktiven Spiel (ID: {self._current_game_id}) registriert.")


    def get_all_players(self) -> Dict[int, str]:
        """
        Holt ALLE Spieler aus der Datenbank und filtert nach den im Spiel aktiven IDs.
        Gibt {player_id: name} zurück.
        """
        if not self._current_game_id or not self._active_player_ids:
            return {} 

        # Nutzt die gespeicherten aktiven IDs zur Abfrage
        placeholders = ', '.join(['?' for _ in self._active_player_ids])
        query = f"SELECT player_id, name FROM players WHERE player_id IN ({placeholders})"
        
        try:
            self.db_manager.connect()
            self.db_manager._cursor.execute(query, tuple(self._active_player_ids))
            results = self.db_manager._cursor.fetchall()
            self.db_manager.close()
            
            return {row[0]: row[1] for row in results}
            
        except Exception as e:
            print(f"Fehler beim Laden der aktiven Spieler: {e}")
            return {}
            
    # --- GETTER FÜR GUI ---
    
    def get_all_players_details(self) -> Dict[int, str]:
        """Holt alle Spieler des Standard-Teams (ID 1) für die initiale Auswahl im StartDialog."""
        return self.db_manager.get_player_details_by_team(team_id=1) 

    def get_current_score_own(self) -> int:
        """Gibt den Punktestand des eigenen Teams im aktuellen Satz zurück."""
        return self._current_set.score_own if self._current_set else 0

    def get_current_score_opponent(self) -> int:
        """Gibt den Punktestand des Gegners im aktuellen Satz zurück."""
        return self._current_set.score_opponent if self._current_set else 0

    def get_set_number(self) -> int:
        """Gibt die Nummer des aktuellen Satzes zurück."""
        return self._current_set.set_number if self._current_set else 0