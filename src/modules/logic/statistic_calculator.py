# src/modules/logic/statistic_calculator.py

from typing import Dict, List, Any, Optional
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
        query = """
        SELECT a.executor_player_id, a.action_type, a.result_type, a.target_player_id
        FROM actions a
        JOIN sets s ON a.set_id = s.set_id
        WHERE s.game_id = ?
        """
        
        try:
            raw_data = self.db_manager.execute_query_fetch_all(query, (game_id,))
            
            if not raw_data:
                return pd.DataFrame()
                
            df = pd.DataFrame(raw_data, columns=['executor_player_id', 'action_type', 'result_type', 'target_player_id'])
            return df
        except Exception as e:
            print(f"Fehler beim Laden der Aktionen: {e}")
            return pd.DataFrame()
    
    # --- METHODE ZUR BERECHNUNG ALLER SPIELERSTATISTIKEN ---

    def calculate_player_performance_summary(self, game_id: int) -> pd.DataFrame:
        """
        Berechnet eine zusammenfassende Tabelle mit den wichtigsten Statistiken
        für jeden Spieler im Spiel.
        """
        df = self.fetch_all_actions_for_game(game_id)
        
        if df.empty:
            return pd.DataFrame(columns=[
                'Spieler', 'Angriffe', 'Kills', 'Angriffsfehler', 'Angriffs-Eff. (%)', 
                'Kill-Rate (%)', 'Aufschläge', 'Asse', 'Aufschlagfehler', 
                'Ass-Rate (%)', 'Blockpunkte', 'Zuspiele', 'Zuspiel_Fehler', 
                'Zuspiel-Fehlerquote (%)'
            ])

        # 1. Spalten für Zählungen erstellen (Vektorisiert)
        df['Attack_Total'] = (df['action_type'] == 'Angriff').astype(int)
        df['Attack_Kill'] = (df['result_type'] == 'Kill').astype(int)
        df['Attack_Error'] = ((df['result_type'] == 'Fehler') & (df['action_type'] == 'Angriff')).astype(int)
        
        df['Serve_Total'] = (df['action_type'] == 'Aufschlag').astype(int)
        df['Serve_Ace'] = (df['result_type'] == 'Ass').astype(int)
        df['Serve_Error'] = ((df['result_type'] == 'Fehler') & (df['action_type'] == 'Aufschlag')).astype(int)
        
        df['Block_Point'] = ((df['action_type'] == 'Block') & (df['result_type'] == 'Punkt')).astype(int)
        
        df['Set_Total'] = (df['action_type'] == 'Zuspiel').astype(int)
        df['Set_Error'] = ((df['result_type'] == 'Fehler') & (df['action_type'] == 'Zuspiel')).astype(int)
        
        # 2. Aggregation: Gruppierung nach Spieler-ID und Summierung der Zählungen
        summary_df = df.groupby('executor_player_id').agg(
            Angriffe=('Attack_Total', 'sum'),
            Kills=('Attack_Kill', 'sum'),
            Angriffsfehler=('Attack_Error', 'sum'),
            Aufschläge=('Serve_Total', 'sum'),
            Asse=('Serve_Ace', 'sum'),
            Aufschlagfehler=('Serve_Error', 'sum'),
            Blockpunkte=('Block_Point', 'sum'),
            Zuspiele=('Set_Total', 'sum'),
            Zuspiel_Fehler=('Set_Error', 'sum')
        ).reset_index()

        # 3. Berechnung der Raten und Effizienzen (Prozentwerte)
        
        summary_df['Angriffs-Eff. (%)'] = (summary_df['Kills'] - summary_df['Angriffsfehler']) / summary_df['Angriffe']
        summary_df['Kill-Rate (%)'] = (summary_df['Kills'] / summary_df['Angriffe'])
        summary_df['Ass-Rate (%)'] = (summary_df['Asse'] / summary_df['Aufschläge'])
        summary_df['Zuspiel-Fehlerquote (%)'] = (summary_df['Zuspiel_Fehler'] / summary_df['Zuspiele'])

        # 4. Spielernamen hinzufügen (mit Ausnahme von ID 0 = Gegner)
        def get_name(player_id):
            if player_id == 0:
                return "Gegner (Team-Punkt)" 
            name = self.db_manager.get_player_name_by_id(int(player_id))
            return name if name else f"ID: {int(player_id)}"

        summary_df['Spieler'] = summary_df['executor_player_id'].apply(get_name)
        
        summary_df = summary_df[summary_df['executor_player_id'] != 0]

        # 5. Finalisierung und Formatierung
        final_columns = [
            'Spieler', 
            'Angriffe', 'Kills', 'Angriffsfehler', 'Angriffs-Eff. (%)', 'Kill-Rate (%)',
            'Aufschläge', 'Asse', 'Aufschlagfehler', 'Ass-Rate (%)',
            'Blockpunkte', 
            'Zuspiele', 'Zuspiel_Fehler', 'Zuspiel-Fehlerquote (%)'
        ]
        
        summary_df = summary_df.fillna(0)
        summary_df[['Angriffs-Eff. (%)', 'Kill-Rate (%)', 'Ass-Rate (%)', 'Zuspiel-Fehlerquote (%)']] *= 100

        return summary_df[final_columns].round(1)

    # --- METHODE ZUR BERECHNUNG DER ANGRIIFSEFFIZIENZ (TEAM) ---
    
    def calculate_attack_efficiency(self, game_id: int, player_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Berechnet die Angriffseffizienz (Kill - Fehler) / Gesamtangriffe.
        (Primär für die Team-Anzeige in AnalysisView)
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

        # Angriffsfehler sind Result 'Fehler' bei Action 'Angriff'
        kills = len(attack_df[attack_df['result_type'] == 'Kill'])
        errors = len(attack_df[attack_df['result_type'] == 'Fehler'])
        
        efficiency = (kills - errors) / total_attacks
        
        return {
            "efficiency": round(efficiency, 3), 
            "kills": kills, 
            "errors": errors, 
            "total_attacks": total_attacks
        }

    # --- METHODE ZUR BERECHNUNG DER ZUSPIELVERTEILUNG (ÜBERARBEITET) ---

    def calculate_setting_distribution(self, game_id: int) -> pd.DataFrame:
        """
        Berechnet, wie oft ein Zuspieler zu welchem Angreifer zugespielt hat,
        inklusive prozentualer Verteilung und Zuspiel-Fehlern.
        """
        # Daten abrufen
        df = self.fetch_all_actions_for_game(game_id)
        
        if df.empty:
            return pd.DataFrame()
            
        # Filtern nach Zuspiel-Aktionen
        setting_df = df[df['action_type'] == 'Zuspiel']

        # Aggregation: Zähle die Zuspiel-Versuche pro Zuspieler und Zielspieler
        distribution = setting_df.groupby(['executor_player_id', 'target_player_id']).size().reset_index(name='Total')
        
        # Zähle die Fehler pro Zuspieler (nur executor_player_id nötig)
        setting_errors = setting_df[(setting_df['result_type'] == 'Fehler')].groupby('executor_player_id').size().reset_index(name='Fehler')
        
        # Fehler-DF mit Distribution-DF zusammenführen, um Fehler pro Zuspieler zu erhalten
        setter_stats = distribution.groupby('executor_player_id')['Total'].sum().reset_index(name='Zuspiele Gesamt')
        setter_stats = pd.merge(setter_stats, setting_errors, on='executor_player_id', how='left').fillna(0)
        
        # Gesamtstatistik wieder mit Distribution zusammenführen
        distribution = pd.merge(distribution, setter_stats[['executor_player_id', 'Zuspiele Gesamt', 'Fehler']], on='executor_player_id', how='left')

        # Spielernamen hinzufügen
        def get_name(player_id):
            if pd.isna(player_id) or player_id is None:
                return "Kein Ziel"
            name = self.db_manager.get_player_name_by_id(int(player_id))
            return name if name else f"ID: {int(player_id)}"

        distribution['Zuspieler'] = distribution['executor_player_id'].apply(get_name)
        distribution['Angreifer'] = distribution['target_player_id'].apply(get_name)

        # Prozentsätze berechnen
        distribution['Anteil am Zuspieler (%)'] = (distribution['Total'] / distribution['Zuspiele Gesamt'] * 100).round(1)
        
        # Zuspieler-Statistik pro Zeile wiederholen
        distribution['Zuspieler Fehler (%)'] = (distribution['Fehler'] / distribution['Zuspiele Gesamt'] * 100).round(1)

        # Spalten für die Anzeige optimieren
        final_columns = [
            'Zuspieler', 
            'Angreifer', 
            'Total', 
            'Anteil am Zuspieler (%)', 
            'Zuspiele Gesamt', 
            'Fehler',
            'Zuspieler Fehler (%)'
        ]

        return distribution[final_columns]