# src/modules/logic/statistic_calculator.py

from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from modules.data.db_manager import DBManager

# Importe für den PDF-Export
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

class StatisticCalculator:
    """
    Berechnet alle statistischen Kennzahlen (Quoten, Effizienz, Verteilungen)
    basierend auf den Aktionen in der Datenbank.
    """
    def __init__(self, db_manager: DBManager):
        self.db_manager = db_manager

    def fetch_all_actions_for_game(self, game_id: int) -> pd.DataFrame:
        """
        Fragt alle Aktionen für ein gegebenes Spiel ab und gibt sie als Pandas DataFrame zurück,
        sortiert nach set_id und timestamp.
        """
        query = """
        SELECT 
            a.executor_player_id, a.action_type, a.result_type, a.target_player_id,
            a.set_id, a.timestamp 
        FROM actions a
        JOIN sets s ON a.set_id = s.set_id
        WHERE s.game_id = ?
        ORDER BY a.set_id ASC, a.timestamp ASC
        """
        
        try:
            self.db_manager.connect()
            df = pd.read_sql_query(query, self.db_manager._connection, params=(game_id,))
            self.db_manager.close()
            return df
        except Exception as e:
            print(f"Fehler beim Laden der Aktionen: {e}")
            return pd.DataFrame()

    def calculate_player_general_stats(self, game_id: int) -> pd.DataFrame:
        """
        Aggregiert erweiterte Statistiken pro Spieler für die Dashboard-Ansicht.
        """
        df = self.fetch_all_actions_for_game(game_id)
        if df.empty:
            return pd.DataFrame()

        # Filtern von Aktionen ohne Spieler (executor_player_id = 0)
        df_player = df[df['executor_player_id'] != 0].copy()
        if df_player.empty:
             return pd.DataFrame()

        # Initialisiere alle Spieler, die Aktionen ausgeführt haben
        stats = pd.DataFrame(df_player['executor_player_id'].unique(), columns=['executor_player_id'])

        def add_stat_column(stats_df, df_source, col_name, action_type, result_type=None):
            if result_type:
                counts = df_source[(df_source['action_type'] == action_type) & 
                                   (df_source['result_type'] == result_type)].groupby('executor_player_id').size()
            else:
                counts = df_source[df_source['action_type'] == action_type].groupby('executor_player_id').size()
            stats_df[col_name] = stats_df['executor_player_id'].map(counts).fillna(0).astype(int)

        # Basis-Zählungen
        add_stat_column(stats, df_player, 'Kills', 'Angriff', 'Kill')
        add_stat_column(stats, df_player, 'Angriffsfehler', 'Angriff', 'Fehler')
        add_stat_column(stats, df_player, 'Blockpunkte', 'Block', 'Punkt')
        add_stat_column(stats, df_player, 'Asse', 'Aufschlag', 'Ass')
        add_stat_column(stats, df_player, 'Aufschlagfehler', 'Aufschlag', 'Fehler')
        add_stat_column(stats, df_player, 'Angriffe_Gesamt', 'Angriff')
        add_stat_column(stats, df_player, 'Aufschläge_Gesamt', 'Aufschlag')

        # Erweiterte Berechnungen
        # 1. Gesamtpunkte (Summe aller direkten Punktgewinne)
        stats['Gesamtpunkte'] = stats['Kills'] + stats['Blockpunkte'] + stats['Asse']
       

        # 2. Aufschlag-Fehlerquote (Fehler pro Gesamtaufschläge)
        stats['Service_Error_Rate'] = np.where(
            stats['Aufschläge_Gesamt'] > 0,
            stats['Aufschlagfehler'] / stats['Aufschläge_Gesamt'],
            0
        ).round(3)

        # 3. Angriffseffizienz: (Kills - Fehler) / Gesamt
        stats['Angriffseffizienz'] = np.where(
            stats['Angriffe_Gesamt'] > 0,
            (stats['Kills'] - stats['Angriffsfehler']) / stats['Angriffe_Gesamt'],
            0
        ).round(3)

        return stats

    def calculate_setter_attacker_efficiency(self, game_id: int) -> pd.DataFrame:
        """
        Berechnet die Effizienz für spezifische Zuspieler-Angreifer-Kombinationen.
        """
        df = self.fetch_all_actions_for_game(game_id)
        if df.empty:
            return pd.DataFrame()
        
        df_clean = df[df['executor_player_id'] != 0].copy()
        df_clean.reset_index(drop=True, inplace=True)
        
        sequences = []
        for i in range(len(df_clean) - 1):
            curr, nxt = df_clean.iloc[i], df_clean.iloc[i+1]
            
            # Prüfen auf Sequenz: Zuspiel mit Ziel -> Angriff durch Zielspieler
            if (curr['action_type'] == 'Zuspiel' and curr['target_player_id'] and 
                nxt['action_type'] == 'Angriff' and nxt['executor_player_id'] == curr['target_player_id']):
                
                sequences.append({
                    'setter_id': curr['executor_player_id'],
                    'attacker_id': nxt['executor_player_id'],
                    'result_type': nxt['result_type']
                })

        if not sequences: return pd.DataFrame()
        
        seq_df = pd.DataFrame(sequences)
        summary = seq_df.groupby(['setter_id', 'attacker_id']).size().reset_index(name='Total')
        
        kills = seq_df[seq_df['result_type'] == 'Kill'].groupby(['setter_id', 'attacker_id']).size().reset_index(name='Kills')
        errors = seq_df[seq_df['result_type'] == 'Fehler'].groupby(['setter_id', 'attacker_id']).size().reset_index(name='Errors')
        
        summary = summary.merge(kills, on=['setter_id', 'attacker_id'], how='left').fillna(0)
        summary = summary.merge(errors, on=['setter_id', 'attacker_id'], how='left').fillna(0)
        
        summary['Efficiency'] = ((summary['Kills'] - summary['Errors']) / summary['Total'] * 100).round(1)
        
        def get_name(p_id): return self.db_manager.get_player_name_by_id(int(p_id))
        summary['Zuspieler'] = summary['setter_id'].apply(get_name)
        summary['Angreifer'] = summary['attacker_id'].apply(get_name)

        return summary[['Zuspieler', 'Angreifer', 'Total', 'Kills', 'Errors', 'Efficiency']]

    def calculate_setting_distribution(self, game_id: int) -> pd.DataFrame:
        """Berechnet die prozentuale Verteilung der Zuspiele pro Zuspieler."""
        raw_data = self.db_manager.fetch_setting_actions(game_id)
        if not raw_data: return pd.DataFrame()

        df = pd.DataFrame(raw_data, columns=['executor_id', 'target_id'])
        dist = df.groupby(['executor_id', 'target_id']).size().reset_index(name='Total')
        
        def get_name(p_id): return self.db_manager.get_player_name_by_id(int(p_id)) if pd.notna(p_id) else "Kein Ziel"
        dist['Zuspieler'] = dist['executor_id'].apply(get_name)
        dist['Angreifer'] = dist['target_id'].apply(get_name)

        total_by_setter = dist.groupby('Zuspieler')['Total'].transform('sum')
        dist['Prozent'] = (dist['Total'] / total_by_setter * 100).round(1)

        return dist[['Zuspieler', 'Angreifer', 'Total', 'Prozent']]

    def export_to_pdf(self, game_id: int, file_path: str) -> bool:
        """Erstellt einen detaillierten PDF-Bericht des Spiels."""
        try:
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()

            elements.append(Paragraph(f"Volleyball Spiel-Analyse - Spiel ID: {game_id}", styles['Title']))
            elements.append(Spacer(1, 12))

            df = self.calculate_player_general_stats(game_id)
            if not df.empty:
                elements.append(Paragraph("Spieler-Statistiken", styles['Heading2']))
                elements.append(Spacer(1, 6))

                # Tabellendaten vorbereiten
                # In src/modules/logic/statistic_calculator.py

            data = [["Spieler", "Punkte", "Kills", "Blocks", "Asse", "Effizienz", "Srv. Err"]]
            for _, row in df.iterrows():
                name = self.db_manager.get_player_name_by_id(int(row['executor_player_id']))
                data.append([
                    name,
                    str(int(row['Gesamtpunkte'])),
                    str(int(row['Kills'])),
                    str(int(row['Blockpunkte'])),
                    str(int(row['Asse'])),
                    f"{row['Angriffseffizienz']*100:.1f}%",
                    f"{row['Service_Error_Rate']*100:.0f}%"
                ])

                table = Table(data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey])
                ]))
                elements.append(table)

            doc.build(elements)
            return True
        except Exception as e:
            print(f"Fehler beim PDF-Export: {e}")
            return False