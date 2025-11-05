# src/modules/data/db_manager.py

import sqlite3
import os
from .models import Player, Team, Game, Set, Action # Importiere die Modelle
from ..config import DB_PATH # Wird später in config.py definiert

class DBManager:
    """
    Verwaltet die Verbindung zur SQLite-Datenbank und führt alle
    datenbankspezifischen Operationen aus.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        """Initialisiert den DBManager und stellt die Verbindung her."""
        self.db_path = db_path
        self._connection = None
        self._cursor = None
        
        # Stelle sicher, dass der Ordner existiert
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def connect(self):
        """Stellt die Verbindung zur Datenbank her."""
        try:
            self._connection = sqlite3.connect(self.db_path)
            self._cursor = self._connection.cursor()
        except sqlite3.Error as e:
            print(f"Datenbankverbindungsfehler: {e}")
            raise

    def close(self):
        """Schließt die Verbindung zur Datenbank."""
        if self._connection:
            self._connection.close()
            self._connection = None
            self._cursor = None

    def execute_query(self, query: str, params: tuple = (), fetch_id: bool = False):
        """
        Führt einen beliebigen SQL-Query aus.
        Gibt bei fetch_id=True die ID des zuletzt eingefügten Datensatzes zurück.
        """
        try:
            self.connect()
            self._cursor.execute(query, params)
            
            if fetch_id:
                # KRITISCHER SCHRITT: Speichere die ID vor dem Commit
                last_id = self._cursor.lastrowid 
                self._connection.commit()
                return last_id # Gebe die ID zurück
            else:
                self._connection.commit()
                return True
                
        except sqlite3.Error as e:
            print(f"SQL-Fehler bei Query: '{query}' mit Params {params}: {e}")
            return False if not fetch_id else None # Gebe None zurück, falls ID erwartet wird und Fehler auftritt
        finally:
            self.close()

    def setup_database(self):
        """Erstellt alle notwendigen Tabellen."""
        print("Erstelle Datenbanktabellen...")
        
        # Verwende TEXT für Booleans, da SQLite keinen nativen Boolean-Typ hat
        queries = [
            """
            CREATE TABLE IF NOT EXISTS teams (
                team_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY,
            team_id INTEGER,
            name TEXT NOT NULL,
            jersey_number INTEGER,
            position TEXT,  
            FOREIGN KEY (team_id) REFERENCES teams (team_id)
        );
            """,
            """
            CREATE TABLE IF NOT EXISTS games (
                game_id INTEGER PRIMARY KEY,
                date_time TEXT NOT NULL,
                home_team_id INTEGER,
                guest_team_id INTEGER,
                FOREIGN KEY (home_team_id) REFERENCES teams (team_id),
                FOREIGN KEY (guest_team_id) REFERENCES teams (team_id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS sets (
                set_id INTEGER PRIMARY KEY,
                game_id INTEGER,
                set_number INTEGER NOT NULL,
                score_own INTEGER DEFAULT 0,
                score_opponent INTEGER DEFAULT 0,
                FOREIGN KEY (game_id) REFERENCES games (game_id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS actions (
                action_id INTEGER PRIMARY KEY,
                set_id INTEGER,
                action_type TEXT NOT NULL,
                executor_player_id INTEGER,
                result_type TEXT,
                target_player_id INTEGER,
                point_for TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (set_id) REFERENCES sets (set_id),
                FOREIGN KEY (executor_player_id) REFERENCES players (player_id),
                FOREIGN KEY (target_player_id) REFERENCES players (player_id)
            );
            """
        ]
        
        for query in queries:
            self.execute_query(query)

    def execute_query_fetch_all(self, query: str, params: tuple = ()) -> List[Tuple]:
        """Führt einen Query aus und holt alle Ergebnisse."""
        try:
            self.connect()
            self._cursor.execute(query, params)
            results = self._cursor.fetchall()
            return results
        except sqlite3.Error as e:
            print(f"SQL-Fehler beim Fetchen: {e}")
            return []
        finally:
            self.close()

    # --- Beispiel CRUD-Methode (Weitere folgen nach Bedarf) ---
    def insert_player(self, player: Player, team_id: int):
        """Fügt einen neuen Spieler in die Datenbank ein."""
        # UPDATE: 'position' hinzugefügt
        query = "INSERT INTO players (team_id, name, jersey_number, position) VALUES (?, ?, ?, ?)" 
        self.execute_query(query, (team_id, player.name, player.jersey_number, player.position))
        
    def insert_action(self, action: Action):
        """Fügt eine neue Aktion in die Datenbank ein."""
        query = """
        INSERT INTO actions (set_id, action_type, executor_player_id, result_type, 
                             target_player_id, point_for, timestamp) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            action.set_id, 
            action.action_type, 
            action.executor_player_id, 
            action.result_type,
            action.target_player_id, 
            action.point_for, 
            action.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        )
        self.execute_query(query, params)
            
    def get_player_details_by_team(self, team_id: int) -> Dict[int, str]:
        """Holt Spielerdetails nur für ein bestimmtes Team."""
        query = "SELECT player_id, name FROM players WHERE team_id = ?"
        try:
            self.connect()
            self._cursor.execute(query, (team_id,))
            results = self._cursor.fetchall()
            self.close()
            return {row[0]: row[1] for row in results}
        except:
            return {}
        
    def insert_team(self, name: str) -> int:
        """Fügt ein neues Team ein und gibt dessen ID zurück."""
        query = "INSERT INTO teams (name) VALUES (?)"
        return self.execute_query(query, (name,), fetch_id=True) # fetch_id muss im execute_query implementiert sein

    def get_all_teams(self) -> Dict[int, str]:
        """Holt alle Teams {id: name} aus der Datenbank."""
        query = "SELECT team_id, name FROM teams"
        try:
            self.connect()
            self._cursor.execute(query)
            results = self._cursor.fetchall()
            self.close()
            return {row[0]: row[1] for row in results}
        except:
            return {}

    def get_team_players(self, team_id: int) -> List[Tuple[int, str, Optional[int]]]:
        """Holt alle Spieler eines bestimmten Teams (ID, Name, Trikotnummer)."""
        # KRITISCH: Trikotnummer zur Abfrage hinzugefügt
        query = "SELECT player_id, name, jersey_number FROM players WHERE team_id = ?"
        try:
            self.connect()
            self._cursor.execute(query, (team_id,))
            results = self._cursor.fetchall()
            self.close()
            # Das zurückgegebene Tupel hat jetzt 3 Elemente: (ID, Name, Jersey_Number)
            return results
        except Exception as e:
            # Fehlerbehandlung
            print(f"Fehler beim Abrufen der Teamspieler: {e}")
            return []

    def update_player_team(self, player_id: int, team_id: int):
        """Weist einem Spieler ein Team zu."""
        query = "UPDATE players SET team_id = ? WHERE player_id = ?"
        self.execute_query(query, (team_id, player_id))
        
    def get_all_players_details(self) -> List[Tuple[int, str, Optional[int], Optional[str], int]]:
        """
        Holt ALLE Spielerdetails (ID, Name, Nr., Pos., Team-ID) für die Verwaltung.
        """
        query = "SELECT player_id, name, jersey_number, position, team_id FROM players"
        
        # Die Methode execute_query_fetch_all wird nun verwendet
        results = self.execute_query_fetch_all(query) 
        
        # Rückgabe: Liste von (ID, Name, Jersey, Position, Team_ID)
        return results
    
    def get_player_name_by_id(self, player_id: int) -> str:
        """Gibt den Namen eines Spielers basierend auf der ID zurück."""
        query = "SELECT name FROM players WHERE player_id = ?"
        try:
            self.connect()
            self._cursor.execute(query, (player_id,))
            result = self._cursor.fetchone()
            self.close()
            return result[0] if result else "Unbekannt"
        except:
            return "Unbekannt"

    def fetch_setting_actions(self, game_id: int) -> List[Tuple]:
        """
        Holt alle Zuspiel-Aktionen für eine bestimmte Spiel-ID, 
        einschließlich des Zuspielers (executor) und des Zielspielers (target).
        """
        query = """
        SELECT 
            a.executor_player_id, 
            a.target_player_id
        FROM actions a
        JOIN sets s ON a.set_id = s.set_id
        WHERE 
            s.game_id = ? AND 
            a.action_type = 'Zuspiel'
        """
        # Wir verwenden die ID des Spiels als Parameter
        return self.execute_query_fetch_all(query, (game_id,))

    def get_all_games(self) -> List[Tuple[int, str, str]]:
        """Holt alle Spiele (ID, Datum/Zeit, Heim-Team-Name, Gast-Team-Name) ab."""
        query = """
        SELECT 
            g.game_id, 
            g.date_time, 
            th.name AS home_team_name, 
            tg.name AS guest_team_name
        FROM games g
        JOIN teams th ON g.home_team_id = th.team_id
        JOIN teams tg ON g.guest_team_id = tg.team_id
        ORDER BY g.date_time DESC
        """
        try:
            self.connect()
            self._cursor.execute(query)
            results = self._cursor.fetchall()
            self.close()
            # Das Ergebnis ist eine Liste von Tupeln: (ID, Datum, Heimname, Gastname)
            return results
        except Exception as e:
            print(f"Fehler beim Laden aller Spiele: {e}")
            return []
        
    def check_player_uniqueness(self, name: str, jersey_number: int, player_id: Optional[int] = None) -> bool:
        """
        Prüft, ob ein Spieler mit demselben Namen ODER derselben Trikotnummer bereits existiert.
        Schließt optional den aktuellen player_id beim Bearbeiten aus.
        Gibt True zurück, wenn die Kombination eindeutig ist.
        """
        query = """
            SELECT COUNT(*) FROM players 
            WHERE (name = ? OR jersey_number = ?) 
            AND player_id != ?
        """
        # Wenn player_id None ist (beim Hinzufügen), verwenden wir -1, was nie eine gültige ID sein sollte.
        exclude_id = player_id if player_id is not None else -1 
        
        try:
            self.connect()
            self._cursor.execute(query, (name, jersey_number, exclude_id))
            count = self._cursor.fetchone()[0]
            self.close()
            
            return count == 0 # True, wenn keine Duplikate gefunden wurden
        except Exception as e:
            print(f"Fehler bei Eindeutigkeitsprüfung: {e}")
            return False # Im Zweifelsfall Fehler melden

    def update_player(self, player_id: int, name: str, jersey_number: int, position: str) -> bool:
        """Aktualisiert die Details eines bestehenden Spielers."""
        query = """
            UPDATE players 
            SET name = ?, jersey_number = ?, position = ? 
            WHERE player_id = ?
        """
        try:
            self.connect()
            self._cursor.execute(query, (name, jersey_number, position, player_id))
            self.commit()
            self.close()
            return True
        except Exception as e:
            print(f"Fehler beim Aktualisieren des Spielers: {e}")
            return False