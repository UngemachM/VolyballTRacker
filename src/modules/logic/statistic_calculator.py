# src/modules/logic/statistic_calculator.py

from typing import Dict, List, Any, Optional
import pandas as pd
from modules.data.db_manager import DBManager
# HINWEIS: Optional mÃ¶glicherweise nicht in allen Umgebungen nÃ¶tig, aber fÃ¼r Typ-Sicherheit beibehalten.

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
        """
        query = """
        SELECT a.executor_player_id, a.action_type, a.result_type, a.target_player_id
        FROM actions a
        JOIN sets s ON a.set_id = s.set_id
        WHERE s.game_id = ?
        """
        
        try:
            self.db_manager.connect()
            # Der DBManager mÃ¼sste eine ._connection bereitstellen oder read_sql_query anpassen
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
        
    # --- NEU: ANFORDERUNG 2: AUFSCHLAG QUOTE ---

    def calculate_service_rate(self, game_id: int, player_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Berechnet die Aufschlag-Quote: (Ass + Ins Feld) / Gesamt-Aufschläge.
        """
        df = self.fetch_all_actions_for_game(game_id)
        
        if df.empty:
            return {"rate": 0.0, "total_serves": 0, "aces": 0, "in_court": 0}

        service_df = df[df['action_type'] == 'Aufschlag']
        
        if player_id:
            service_df = service_df[service_df['executor_player_id'] == player_id]

        total_serves = len(service_df)
        if total_serves == 0:
            return {"rate": 0.0, "total_serves": 0, "aces": 0, "in_court": 0}

        # Aces ('Ass') und Ins Feld ('Ins Feld')
        aces = len(service_df[service_df['result_type'] == 'Ass'])
        in_court = len(service_df[service_df['result_type'] == 'Ins Feld'])
        
        rate = (aces + in_court) / total_serves
        
        return {
            "rate": round(rate, 3), 
            "aces": aces,
            "in_court": in_court,
            "total_serves": total_serves
        }

    # --- NEU: ANFORDERUNG 1: GENERAL STATS AGGREGATOR ---

    def calculate_player_general_stats(self, game_id: int) -> pd.DataFrame:
        """
        Aggregiert alle relevanten Aktionen pro Spieler fÃ¼r die Spielerzusammenfassung.
        """
        df = self.fetch_all_actions_for_game(game_id)

        if df.empty:
            return pd.DataFrame()

        # Filtern von Aktionen ohne Spieler (executor_player_id = 0)
        df_player = df[df['executor_player_id'] != 0].copy()

        if df_player.empty:
             return pd.DataFrame()

        # Initialisiere alle Spieler, die Aktionen ausgefÃ¼hrt haben
        stats = pd.DataFrame(df_player['executor_player_id'].unique(), columns=['executor_player_id'])

        # Funktion zur ZÃ¤hlung spezifischer Ergebnisse
        def count_result(df, action_type, result_type):
            return df[(df['action_type'] == action_type) & (df['result_type'] == result_type)].groupby('executor_player_id').size()

        # HILFSFUNKTION: Aggregiert und fÃ¼gt Spalte hinzu, fÃ¼llt N/A mit 0
        def add_stat_column(stats_df, df_source, col_name, action_type, result_type=None):
            if result_type:
                counts = count_result(df_source, action_type, result_type)
            else:
                counts = df_source[df_source['action_type'] == action_type].groupby('executor_player_id').size()
                
            stats_df[col_name] = stats_df['executor_player_id'].map(counts).fillna(0).astype(int)
            
        
        add_stat_column(stats, df_player, 'Kills', 'Angriff', 'Kill')
        add_stat_column(stats, df_player, 'Angriffsfehler', 'Angriff', 'Fehler')
        add_stat_column(stats, df_player, 'Blockpunkte', 'Block', 'Punkt')
        add_stat_column(stats, df_player, 'Aufschlag-Asse', 'Aufschlag', 'Ass')
        add_stat_column(stats, df_player, 'Aufschlagfehler', 'Aufschlag', 'Fehler')
        add_stat_column(stats, df_player, 'Angriffe Gesamt', 'Angriff')
        add_stat_column(stats, df_player, 'Aufschläge Gesamt', 'Aufschlag')


        # Berechne Angriffseffizienz (wird fÃ¼r Filtering/Anzeige benÃ¶tigt)
        stats['Angriffseffizienz'] = (stats['Kills'] - stats['Angriffsfehler']) / stats['Angriffe Gesamt'].replace(0, pd.NA) 
        stats['Angriffseffizienz'] = stats['Angriffseffizienz'].fillna(0).round(3)

        return stats[['executor_player_id', 'Kills', 'Angriffsfehler', 'Blockpunkte', 
                      'Aufschlag-Asse', 'Aufschlagfehler', 'Angriffe Gesamt', 
                      'Aufschläge Gesamt', 'Angriffseffizienz']]


    def calculate_setting_distribution(self, game_id: int) -> pd.DataFrame:
        """Berechnet, wie oft ein Zuspieler zu welchem Angreifer zugespielt hat."""
        
        # 1. Daten abrufen: Wir verwenden die neue Methode im DBManager
        raw_data = self.db_manager.fetch_setting_actions(game_id)
        
        if not raw_data:
            return pd.DataFrame()

        # Konvertiere raw_data zu einem DataFrame: 
        # Spalten: ['executor_id', 'target_id']
        df = pd.DataFrame(raw_data, columns=['executor_id', 'target_id'])
        
        # 2. Aggregation: ZÃ¤hle die Zuspiel-Versuche pro Zuspieler und Zielspieler
        distribution = df.groupby(['executor_id', 'target_id']).size().reset_index(name='Total')
        
        # 3. Spielernamen fÃ¼r die Lesbarkeit hinzufÃ¼gen
        
        # Mapping Funktion fÃ¼r Spieler-Namen
        def get_name(player_id):
            if pd.isna(player_id) or player_id is None:
                return "Kein Ziel"
            # Annahme: get_player_name_by_id existiert im DBManager und ist performant
            return self.db_manager.get_player_name_by_id(int(player_id))

        distribution['Zuspieler'] = distribution['executor_id'].apply(get_name)
        distribution['Angreifer'] = distribution['target_id'].apply(get_name)

        # 4. ProzentsÃ¤tze berechnen 
        total_by_setter = distribution.groupby('Zuspieler')['Total'].transform('sum')
        distribution['Prozent'] = (distribution['Total'] / total_by_setter * 100).round(1)

        return distribution[['Zuspieler', 'Angreifer', 'Total', 'Prozent', 'executor_id']] # <<< executor_id fÃ¼r die Kachel-Ansicht beibehalten