# src/modules/logic/game_controller.py

from typing import Optional, List, Dict, Tuple, Any
import datetime
from ..data.db_manager import DBManager
from ..data.models import Action, Set
from ..config import POINT_FOR # Importiere die definierten Konstanten

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
            
            return (max_num or 0) + 1 
        except Exception as e:
            print(f"Fehler bei Satznummer-Abruf: {e}")
            return 1 

    # --- SPIEL- UND SATZVERWALTUNG ---
    
    def start_new_game(self, own_team_id: int, opponent_name: str) -> int:
        """Erstellt Gegner-Team, startet Spiel und den ersten Satz. Gibt die ECHTE Game ID zurück."""
        
        opponent_team_id = self.db_manager.insert_team(opponent_name) 
        if not opponent_team_id:
              # Annahme: Team existierte bereits oder Fehler.
              # Wir nehmen hier einen Dummy an, sollte in realer App robust sein.
              opponent_team_id = 99 
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = "INSERT INTO games (date_time, home_team_id, guest_team_id) VALUES (?, ?, ?)"
        
        game_id = self.db_manager.execute_query(
            query, 
            (now, own_team_id, opponent_team_id), 
            fetch_id=True
        ) 
        
        if not game_id:
              raise Exception("Fehler: Konnte keine Game ID von der Datenbank erhalten.")
              
        self._current_game_id = game_id 

        self.start_new_set(self._current_game_id) 
        
        print(f"Neues Spiel gestartet. ECHTE Game ID: {game_id}")
        return game_id


    def start_new_set(self, game_id: int): 
        """Erstellt einen neuen Satz in der Datenbank mit korrekter fortlaufender Nummer."""
        
        set_number = self.get_next_set_number(game_id)
        
        new_set = Set(game_id=game_id, set_number=set_number)
        
        query = "INSERT INTO sets (game_id, set_number, score_own, score_opponent) VALUES (?, ?, ?, ?)"
        
        set_id = self.db_manager.execute_query(
            query, 
            (new_set.game_id, new_set.set_number, new_set.score_own, new_set.score_opponent), 
            fetch_id=True
        ) 
        
        if not set_id:
            raise Exception("Fehler: Konnte keine Set ID von der Datenbank erhalten.")
            
        new_set.set_id = set_id
        
        self._current_set = new_set
        print(f"Satz {set_number} gestartet (Set ID: {self._current_set.set_id})")

    def end_active_game(self):
        """Markiert das aktuelle Spiel in der Datenbank als beendet und setzt den Kontext zurück."""
        if not self._current_game_id:
            print("FEHLER: Kein Spiel aktiv, kann nicht beendet werden.")
            return
        
        print(f"Spiel {self._current_game_id} beendet. Kontext zurückgesetzt.")

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
            
        # Punktestand in der Datenbank aktualisieren (UPDATE-Query)
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

        point_for: Optional[str] = None
        
        if result_type in ['Ass', 'Kill', 'Punkt'] or action_type == 'Unser Punkt':
            point_for = POINT_FOR['Eigenes Team']
        elif result_type in ['Fehler', 'Blockiert']:
            point_for = POINT_FOR['Gegner']
            
        # Action-Objekt erstellen
        new_action = Action(
            set_id=self._current_set.set_id,
            executor_player_id=executor_id,
            action_type=action_type,
            result_type=result_type,
            target_player_id=target_id,
            point_for=point_for,
            timestamp=datetime.datetime.now()
        )
        
        self.db_manager.insert_action(new_action)
        
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
    
    def get_all_players_details(self) -> List[Tuple[int, str, Optional[int], Optional[str], Optional[int]]]:
        """Holt ALLE Spielerdetails (ID, Name, Nr., Pos., Team-ID) für die Filterung im StartDialog."""
        return self.db_manager.get_all_players_details() 

    def get_current_score_own(self) -> int:
        """Gibt den Punktestand des eigenen Teams im aktuellen Satz zurück."""
        return self._current_set.score_own if self._current_set else 0

    def get_current_score_opponent(self) -> int:
        """Gibt den Punktestand des Gegners im aktuellen Satz zurück."""
        return self._current_set.score_opponent if self._current_set else 0

    def get_set_number(self) -> int:
        """Gibt die Nummer des aktuellen Satzes zurück."""
        return self._current_set.set_number if self._current_set else 0
    
    def load_game_context(self, game_id: int):
        """
        Lädt den Kontext des letzten Satzes und die aktiven Spieler 
        für ein bestehendes Spiel aus der DB neu.
        """
        from ..data.models import Set # Stellen Sie sicher, dass Set importiert ist

        # 1. Letzten Satz laden
        set_query = "SELECT set_id, set_number, score_own, score_opponent FROM sets WHERE game_id = ? ORDER BY set_number DESC LIMIT 1"
        latest_set_data = self.db_manager.execute_query_fetch_all(set_query, (game_id,))
        
        if not latest_set_data:
            # Kein Satz vorhanden, starte neuen Satz
            print(f"Spiel {game_id} geladen, aber kein Satz gefunden. Starte Satz 1.")
            # Die Methode start_new_set muss auch implementiert sein
            self.start_new_set(game_id) 
        else:
            set_id, set_number, score_own, score_opponent = latest_set_data[0]
            self._current_set = Set(
                game_id=game_id, 
                set_number=set_number, 
                score_own=score_own, 
                score_opponent=score_opponent, 
                set_id=set_id
            )
        
        self._current_game_id = game_id

        # 2. Aktive Spieler laden (Annahme: alle Spieler des Home Teams nehmen teil)
        game_query = "SELECT home_team_id FROM games WHERE game_id = ?"
        home_team_id_data = self.db_manager.execute_query_fetch_all(game_query, (game_id,))
        
        if home_team_id_data:
            home_team_id = home_team_id_data[0][0]
            
            # Lade alle Spieler dieses Teams
            players_data = self.db_manager.get_team_players(home_team_id)
            
            # Nur die IDs für das interne Tracking speichern
            self._active_player_ids = [player[0] for player in players_data]
            print(f"Spiel {game_id} Kontext geladen. Setz-Nr.: {self._current_set.set_number}, Spieler-IDs: {self._active_player_ids}")
        else:
             print(f"Fehler: Heim-Team für Spiel {game_id} nicht gefunden.")
             
    # src/modules/logic/game_controller.py (Zusätzlich zur bestehenden Klasse)

    def get_action_details(self, action_id: int) -> Optional[Dict[str, Any]]:
        """
        Holt die Details einer einzelnen Aktion zur Bearbeitung aus der DB.
        """
        return self.db_manager.get_action_data_by_id(action_id)

    def get_latest_actions(self, limit: int = 20) -> List[Tuple]:
        """
        Holt die letzten Aktionen des aktiven Satzes/Spiels für die Historie.
        Tupel-Struktur: (action_id, set_number, time, executor_name, action_type, result_type, point_for)
        """
        if not self._current_set:
            return []
        
        # Abfrage muss die benötigten Felder liefern: 
        query = """
        SELECT a.action_id, s.set_number, SUBSTR(a.timestamp, 12, 8), p.name, 
               a.action_type, a.result_type, a.point_for
        FROM actions a
        JOIN sets s ON a.set_id = s.set_id
        LEFT JOIN players p ON a.executor_player_id = p.player_id
        WHERE s.game_id = ? 
        ORDER BY a.action_id DESC 
        LIMIT ?
        """
        params = (self._current_set.game_id, limit) 
        
        return self.db_manager.execute_query_fetch_all(query, params)

    def _recalculate_set_score(self, set_id: int) -> bool:
        """
        BERECHNET den Punktestand eines Satzes neu, indem alle Aktionen im Satz gezählt werden.
        Wird nach Bearbeitung oder Löschung aufgerufen.
        """
        # 1. Alle Aktionen des Satzes holen
        query = "SELECT point_for FROM actions WHERE set_id = ?"
        points = self.db_manager.execute_query_fetch_all(query, (set_id,))
        
        if not points:
            new_score_own, new_score_opp = 0, 0
        else:
            new_score_own = sum(1 for p in points if p[0] == 'OWN')
            new_score_opp = sum(1 for p in points if p[0] == 'OPP')

        # 2. Score in der Datenbank aktualisieren
        self.db_manager.update_set_scores(set_id, new_score_own, new_score_opp)
        
        # 3. Wenn es der aktive Satz ist, den internen Zustand aktualisieren
        if self._current_set and self._current_set.set_id == set_id:
            self._current_set.score_own = new_score_own
            self._current_set.score_opponent = new_score_opp
            
        print(f"Satz {set_id} Score neu berechnet: {new_score_own} - {new_score_opp}")
        return True

    def update_action(self, updated_data: Dict[str, Any]) -> bool:
        """
        Aktualisiert eine bestehende Aktion und löst die Neuberechnung des Scores aus.
        """
        action_id = updated_data['action_id']
        old_details = self.get_action_details(action_id)
        
        if not old_details:
            return False

        # 1. Kerndaten der Aktion aktualisieren
        success = self.db_manager.update_action_data(
            action_id=action_id,
            executor_id=updated_data['executor_id'],
            result_type=updated_data['result_type'],
            target_id=updated_data['target_id']
        )
        
        if success:
            # 2. Score neu berechnen, da sich die Aktion oder der Punktwert geändert haben könnte
            return self._recalculate_set_score(old_details['set_id'])
        return False

    def delete_action(self, action_id: int) -> bool:
        """
        Löscht eine Aktion und löst die Neuberechnung des Scores aus.
        """
        old_details = self.get_action_details(action_id)
        
        if not old_details:
            return False

        # 1. Aktion löschen
        success = self.db_manager.delete_action_data(action_id)
        
        if success:
            # 2. Score neu berechnen
            return self._recalculate_set_score(old_details['set_id'])
        return False         