# src/modules/logic/statistic_calculator.py

from typing import Dict, List, Any
import pandas as pd
from modules.data.db_manager import DBManager

class StatisticCalculator:
    """
    Berechnet alle statistischen Kennzahlen (Quoten, Effizienz, Verteilungen)
    basierend auf den Aktionen in der Datenbank.
    """
    def __init__(self, db_manager: DBManager):
        self.db_manager = db_manager

    def fetch_all_actions_for_game(self, game_id: int) -> pd.DataFrame:
        """
        Fragt alle Aktionen für ein gegebenes Spiel ab und gibt sie als Pandas DataFrame zurück.
        Pandas ist ideal für schnelle Aggregationen und Berechnungen.
        """
        # TODO: Implementierung einer Methode in DBManager, die Aktionen nach Game ID abfragt
        
        # Vereinfachte Platzhalter-Abfrage
        query = """
        SELECT a.executor_player_id, a.action_type, a.result_type, a.target_player_id
        FROM actions a
        JOIN sets s ON a.set_id = s.set_id
        WHERE s.game_id = ?
        """
        
        try:
            self.db_manager.connect()
            df = pd.read_sql_query(query, self.db_manager._connection, params=(game_id,))
            self.db_manager.close()
            return df
        except Exception as e:
            print(f"Fehler beim Laden der Aktionen: {e}")
            return pd.DataFrame()

    def calculate_attack_efficiency(self, game_id: int, player_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Berechnet die Angriffseffizienz (Kill - Fehler) / Gesamtangriffe.
        """
        df = self.fetch_all_actions_for_game(game_id)
        
        if df.empty:
            return {"efficiency": 0, "kills": 0, "errors": 0, "total_attacks": 0}

        # Filtern nach Angriffen
        attack_df = df[df['action_type'] == 'Angriff']
        
        if player_id:
            attack_df = attack_df[attack_df['executor_player_id'] == player_id]

        total_attacks = len(attack_df)
        if total_attacks == 0:
            return {"efficiency": 0, "kills": 0, "errors": 0, "total_attacks": 0}

        kills = len(attack_df[attack_df['result_type'] == 'Kill'])
        errors = len(attack_df[attack_df['result_type'] == 'Fehler'])
        
        efficiency = (kills - errors) / total_attacks
        
        return {
            "efficiency": round(efficiency, 3), 
            "kills": kills, 
            "errors": errors, 
            "total_attacks": total_attacks
        }

    def calculate_setting_distribution(self, game_id: int) -> pd.DataFrame:
        """Berechnet, wie oft ein Zuspieler zu welchem Angreifer zugespielt hat."""
        
        # 1. Daten abrufen: Wir verwenden die neue Methode im DBManager
        raw_data = self.db_manager.fetch_setting_actions(game_id)
        
        if not raw_data:
            return pd.DataFrame()

        # Konvertiere raw_data zu einem DataFrame: 
        # Spalten: ['executor_id', 'target_id']
        df = pd.DataFrame(raw_data, columns=['executor_id', 'target_id'])
        
        # 2. Aggregation: Zähle die Zuspiel-Versuche pro Zuspieler und Zielspieler
        distribution = df.groupby(['executor_id', 'target_id']).size().reset_index(name='Total')
        
        # 3. Spielernamen für die Lesbarkeit hinzufügen
        
        # Mapping Funktion für Spieler-Namen
        def get_name(player_id):
            if pd.isna(player_id) or player_id is None:
                return "Kein Ziel"
            return self.db_manager.get_player_name_by_id(int(player_id))

        distribution['Zuspieler'] = distribution['executor_id'].apply(get_name)
        distribution['Angreifer'] = distribution['target_id'].apply(get_name)

        # 4. Prozentsätze berechnen (optional, aber hilfreich)
        total_by_setter = distribution.groupby('Zuspieler')['Total'].transform('sum')
        distribution['Prozent'] = (distribution['Total'] / total_by_setter * 100).round(1)

        return distribution[['Zuspieler', 'Angreifer', 'Total', 'Prozent']]