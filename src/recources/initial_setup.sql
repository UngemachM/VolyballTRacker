def setup_database(self):
        """Erstellt alle notwendigen Tabellen und führt eine einmalige Migration durch."""
        print("Erstelle Datenbanktabellen...")
        
        # --- KRITISCHE MIGRATION FÜR BEREITS EXISTIERENDE DATENBANKEN ---
        # Dieser ALTER TABLE Befehl wird ausgeführt, falls die Spalte noch fehlt.
        # Er kann nach erfolgreicher Migration der aktiven stats.db entfernt werden.
        migration_queries = [
            """
            -- Fügt die Spalte point_detail_type hinzu (falls sie fehlt).
            ALTER TABLE actions ADD COLUMN point_detail_type TEXT; 
            """
        ]
        
        for query in migration_queries:
            try:
                self.execute_query(query)
            except Exception as e:
                # Normalerweise wird hier eine Meldung wie "duplicate column name" ignoriert.
                # Wir fahren fort, falls es kein kritischer Fehler ist.
                if "duplicate column name" in str(e).lower():
                     pass # Spalte existiert bereits
                else:
                     print(f"Migrationsfehler (kann ignoriert werden, wenn Spalte existiert): {e}")


        # --- ERSTELLUNG/PRÜFUNG ALLER TABELLEN (inkl. neuer Spalten) ---
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
                point_detail_type TEXT, -- <<< NEUE SPALTE HIER ENTHALTEN
                timestamp TEXT NOT NULL,
                FOREIGN KEY (set_id) REFERENCES sets (set_id),
                FOREIGN KEY (executor_player_id) REFERENCES players (player_id),
                FOREIGN KEY (target_player_id) REFERENCES players (player_id)
            );
            """
        ]
        
        # Führt die CREATE TABLE IF NOT EXISTS Abfragen aus
        for query in queries:
            self.execute_query(query)