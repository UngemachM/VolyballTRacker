# src/modules/logic/statistic_calculator.py

from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from modules.data.db_manager import DBManager

# PDF-Export Importe
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm

class StatisticCalculator:
    def __init__(self, db_manager: DBManager):
        self.db_manager = db_manager

    def fetch_all_actions_for_game(self, game_id: int) -> pd.DataFrame:
        query = """
        SELECT a.executor_player_id, a.action_type, a.result_type, a.target_player_id,
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
        df = self.fetch_all_actions_for_game(game_id)
        if df.empty: return pd.DataFrame()

        df_player = df[df['executor_player_id'] != 0].copy()
        stats = pd.DataFrame(df_player['executor_player_id'].unique(), columns=['executor_player_id'])

        def add_stat(stats_df, df_source, col_name, action_type, result_type=None):
            if result_type:
                counts = df_source[(df_source['action_type'] == action_type) & 
                                   (df_source['result_type'] == result_type)].groupby('executor_player_id').size()
            else:
                counts = df_source[df_source['action_type'] == action_type].groupby('executor_player_id').size()
            stats_df[col_name] = stats_df['executor_player_id'].map(counts).fillna(0).astype(int)

        # Basis-Zählungen (Namen synchronisiert mit GUI)
        add_stat(stats, df_player, 'Kills', 'Angriff', 'Kill')
        add_stat(stats, df_player, 'Angriffsfehler', 'Angriff', 'Fehler')
        add_stat(stats, df_player, 'Blocks', 'Block', 'Punkt')
        add_stat(stats, df_player, 'Asse', 'Aufschlag', 'Ass')
        add_stat(stats, df_player, 'Halbe_Asse', 'Aufschlag', 'Halbes Ass')
        add_stat(stats, df_player, 'Aufschlagfehler', 'Aufschlag', 'Fehler')
        add_stat(stats, df_player, 'Angriffe_Gesamt', 'Angriff')
        add_stat(stats, df_player, 'Aufschläge_Gesamt', 'Aufschlag')

        # Berechnungen
        stats['Aufschlag_Punkte'] = stats['Asse'].astype(float) + (stats['Halbe_Asse'].astype(float) * 0.5)
        
        # Quoten
        stats['Angriffsquote'] = np.where(stats['Angriffe_Gesamt'] > 0,
            (stats['Kills'] - stats['Angriffsfehler']) / stats['Angriffe_Gesamt'], 0).round(3)

        stats['Ins_Feld_Quote'] = np.where(stats['Aufschläge_Gesamt'] > 0,
            (stats['Aufschläge_Gesamt'] - stats['Aufschlagfehler']) / stats['Aufschläge_Gesamt'], 0).round(3)

        stats['Aufschlagsquote'] = np.where(stats['Aufschläge_Gesamt'] > 0,
            (stats['Aufschlag_Punkte'] - stats['Aufschlagfehler']) / stats['Aufschläge_Gesamt'], 0).round(3)

        # TOTAL-Werte
        stats['Gesamtpunkte'] = stats['Kills'] + stats['Blocks'] + stats['Aufschlag_Punkte']
        stats['Gesamtfehler'] = stats['Angriffsfehler'] + stats['Aufschlagfehler']
        stats['Gesamtversuche'] = stats['Angriffe_Gesamt'] + stats['Aufschläge_Gesamt']
        
        stats['Gesamtquote'] = np.where(stats['Gesamtversuche'] > 0,
            (stats['Gesamtpunkte'] - stats['Gesamtfehler']) / stats['Gesamtversuche'], 0).round(3)

        return stats

    def calculate_setter_attacker_efficiency(self, game_id: int) -> pd.DataFrame:
        df = self.fetch_all_actions_for_game(game_id)
        if df.empty: return pd.DataFrame()
        df_clean = df[df['executor_player_id'] != 0].copy()
        df_clean.reset_index(drop=True, inplace=True)
        seqs = []
        for i in range(len(df_clean)-1):
            curr, nxt = df_clean.iloc[i], df_clean.iloc[i+1]
            if (curr['action_type'] == 'Zuspiel' and curr['target_player_id'] and 
                nxt['action_type'] == 'Angriff' and nxt['executor_player_id'] == curr['target_player_id']):
                seqs.append({'setter_id': curr['executor_player_id'], 'attacker_id': nxt['executor_player_id'], 'res': nxt['result_type']})
        if not seqs: return pd.DataFrame()
        sdf = pd.DataFrame(seqs)
        res = sdf.groupby(['setter_id', 'attacker_id']).size().reset_index(name='Total')
        kills = sdf[sdf['res'] == 'Kill'].groupby(['setter_id', 'attacker_id']).size().reset_index(name='K')
        errs = sdf[sdf['res'] == 'Fehler'].groupby(['setter_id', 'attacker_id']).size().reset_index(name='E')
        res = res.merge(kills, on=['setter_id', 'attacker_id'], how='left').fillna(0)
        res = res.merge(errs, on=['setter_id', 'attacker_id'], how='left').fillna(0)
        res['Eff'] = ((res['K'] - res['E']) / res['Total'] * 100).round(1)
        res['Zuspieler'] = res['setter_id'].apply(lambda x: self.db_manager.get_player_name_by_id(int(x)))
        res['Angreifer'] = res['attacker_id'].apply(lambda x: self.db_manager.get_player_name_by_id(int(x)))
        return res

    def calculate_setting_distribution(self, game_id: int) -> pd.DataFrame:
        raw = self.db_manager.fetch_setting_actions(game_id)
        if not raw: return pd.DataFrame()
        df = pd.DataFrame(raw, columns=['sid', 'tid'])
        dist = df.groupby(['sid', 'tid']).size().reset_index(name='T')
        dist['Zuspieler'] = dist['sid'].apply(lambda x: self.db_manager.get_player_name_by_id(int(x)))
        dist['Angreifer'] = dist['tid'].apply(lambda x: self.db_manager.get_player_name_by_id(int(x)) if pd.notna(x) else "Kein Ziel")
        total = dist.groupby('Zuspieler')['T'].transform('sum')
        dist['P'] = (dist['T'] / total * 100).round(1)
        return dist

    def export_to_pdf(self, game_id: int, file_path: str) -> bool:
        try:
            doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
            elements = []
            styles = getSampleStyleSheet()
            
            # Styles
            title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], fontSize=22, spaceAfter=20, textColor=colors.hexColor("#2C3E50"))
            h2_style = ParagraphStyle('H2Style', parent=styles['Heading2'], fontSize=16, spaceBefore=15, spaceAfter=10, textColor=colors.hexColor("#2980B9"))
            
            elements.append(Paragraph(f"Volleyball Performance Analyse - ID {game_id}", title_style))

            # 1. Spieler
            elements.append(Paragraph("Spieler-Zusammenfassung", h2_style))
            df = self.calculate_player_general_stats(game_id)
            if not df.empty:
                data = [["Spieler", "Punkte", "G-Quote", "A-Quote", "Ins-Feld", "S-Effekt"]]
                for _, r in df.sort_values("Gesamtpunkte", ascending=False).iterrows():
                    name = self.db_manager.get_player_name_by_id(int(r['executor_player_id']))
                    data.append([name, f"{r['Gesamtpunkte']:.1f}", f"{r['Gesamtquote']*100:.1f}%", f"{r['Angriffsquote']*100:.1f}%", f"{r['Ins_Feld_Quote']*100:.1f}%", f"{r['Aufschlagsquote']*100:.1f}%"])
                
                t = Table(data, colWidths=[4*cm, 2.5*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.hexColor("#34495E")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.hexColor("#ECF0F1")])
                ]))
                elements.append(t)
            
            # 2. Kombis
            elements.append(Paragraph("Setter-Angreifer Effizienz", h2_style))
            eff_df = self.calculate_setter_attacker_efficiency(game_id)
            if not eff_df.empty:
                data = [["Zuspieler", "Angreifer", "Versuche", "Effizienz"]]
                for _, r in eff_df.sort_values("Eff", ascending=False).iterrows():
                    data.append([r['Zuspieler'], r['Angreifer'], int(r['Total']), f"{r['Eff']}%"])
                t = Table(data, colWidths=[5*cm, 5*cm, 3*cm, 4*cm])
                t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.hexColor("#16A085")), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
                elements.append(t)

            # 3. Verteilung
            elements.append(Paragraph("Zuspiel-Verteilung", h2_style))
            dist_df = self.calculate_setting_distribution(game_id)
            if not dist_df.empty:
                data = [["Zuspieler", "Angreifer", "Anzahl", "Prozent"]]
                for _, r in dist_df.iterrows():
                    data.append([r['Zuspieler'], r['Angreifer'], int(r['T']), f"{r['P']}%"])
                t = Table(data, colWidths=[5*cm, 5*cm, 3*cm, 4*cm])
                t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.hexColor("#8E44AD")), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
                elements.append(t)

            doc.build(elements)
            return True
        except Exception as e:
            print(f"Fehler PDF: {e}")
            return False