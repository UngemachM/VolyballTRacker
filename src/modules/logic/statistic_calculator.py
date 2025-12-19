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
        res['Efficiency'] = ((res['K'] - res['E']) / res['Total'] * 100).round(1)
        res['Zuspieler'] = res['setter_id'].apply(lambda x: self.db_manager.get_player_name_by_id(int(x)))
        res['Angreifer'] = res['attacker_id'].apply(lambda x: self.db_manager.get_player_name_by_id(int(x)))
        return res

    def calculate_setting_distribution(self, game_id: int) -> pd.DataFrame:
        raw = self.db_manager.fetch_setting_actions(game_id)
        if not raw: return pd.DataFrame()
        df = pd.DataFrame(raw, columns=['sid', 'tid'])
        dist = df.groupby(['sid', 'tid']).size().reset_index(name='Total')
        dist['Zuspieler'] = dist['sid'].apply(lambda x: self.db_manager.get_player_name_by_id(int(x)))
        dist['Angreifer'] = dist['tid'].apply(lambda x: self.db_manager.get_player_name_by_id(int(x)) if pd.notna(x) else "Kein Ziel")
        total = dist.groupby('Zuspieler')['Total'].transform('sum')
        dist['Prozent'] = (dist['Total'] / total * 100).round(1)
        return dist

    def export_to_pdf(self, game_id: int, file_path: str) -> bool:
        """Erstellt ein professionelles PDF mit allen GUI-Statistiken."""
        try:
            doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
            elements = []
            styles = getSampleStyleSheet()
            
            # Custom Styles
            title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], fontSize=22, spaceAfter=20, textColor=colors.toColor("#2C3E50"))
            name_style = ParagraphStyle('NameStyle', parent=styles['Heading2'], fontSize=18, spaceBefore=15, textColor=colors.toColor("#2C3E50"))
            cat_style = ParagraphStyle('CatStyle', parent=styles['Normal'], fontSize=11, fontName='Helvetica-Bold', textColor=colors.toColor("#7F8C8D"))
            
            elements.append(Paragraph(f"Volleyball Performance Analyse - ID {game_id}", title_style))

            # 1. AUSFÜHRLICHE SPIELER-DETAILS
            elements.append(Paragraph("1. Spieler-Zusammenfassung", styles['Heading1']))
            df = self.calculate_player_general_stats(game_id)
            
            if not df.empty:
                for _, r in df.sort_values("Gesamtpunkte", ascending=False).iterrows():
                    p_name = self.db_manager.get_player_name_by_id(int(r['executor_player_id']))
                    elements.append(Paragraph(f"Spieler: {p_name}", name_style))
                    
                    col_w = [4.5*cm, 4.5*cm, 4.5*cm, 4.5*cm] # Definierte Breite für 4 Spalten

                    # Block 1: TOTAL (4 Attribute)
                    total_table = Table([
                        [Paragraph("📊 TOTAL", cat_style), "", "", ""],
                        ["Punkte", "Fehler", "Versuche", "Blocks"],
                        [f"{r['Gesamtpunkte']:.1f}", str(int(r['Gesamtfehler'])), str(int(r['Gesamtversuche'])), str(int(r['Blocks']))]
                    ], colWidths=col_w)
                    
                    # Block 2: ANGRIFF (4 Attribute)
                    atk_table = Table([
                        [Paragraph("⚔️ ANGRIFF", cat_style), "", "", ""],
                        ["Kills", "Fehler", "Quote %", "Versuche"],
                        [str(int(r['Kills'])), str(int(r['Angriffsfehler'])), f"{r['Angriffsquote']*100:.1f}%", str(int(r['Angriffe_Gesamt']))]
                    ], colWidths=col_w)
                    
                    # Block 3: AUFSCHLAG (5 Attribute)
                    srv_table = Table([
                        [Paragraph("🚀 AUFSCHLAG", cat_style), "", "", "", ""],
                        ["S-Punkte", "S-Fehler", "In-Feld %", "S-Effekt %", "Versuche"],
                        [f"{r['Aufschlag_Punkte']:.1f}", str(int(r['Aufschlagfehler'])), f"{r['Ins_Feld_Quote']*100:.1f}%", f"{r['Aufschlagsquote']*100:.1f}%", str(int(r['Aufschläge_Gesamt']))]
                    ], colWidths=[3.6*cm]*5)

                    # Styling
                    s = TableStyle([
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                        ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0,0), (-1,-1), 10),
                        ('GRID', (0,1), (-1,-1), 0.5, colors.grey),
                        ('BACKGROUND', (0,2), (0,2), colors.toColor("#EBF5FB")), # Highlight Punkte
                        ('BACKGROUND', (1,2), (1,2), colors.toColor("#FDEDEC")), # Highlight Fehler
                    ])
                    
                    for t in [total_table, atk_table, srv_table]:
                        t.setStyle(s)
                        elements.append(t)
                        elements.append(Spacer(1, 4))

                    elements.append(Spacer(1, 15))

            # 2. KOMBI EFFIZIENZ (neue Seite)
            elements.append(PageBreak())
            elements.append(Paragraph("2. Setter-Angreifer Effizienz", styles['Heading1']))
            eff_df = self.calculate_setter_attacker_efficiency(game_id)
            if not eff_df.empty:
                data = [["Zuspieler", "Angreifer", "Versuche", "Effizienz"]]
                for _, r in eff_df.sort_values("Efficiency", ascending=False).iterrows():
                    data.append([r['Zuspieler'], r['Angreifer'], int(r['Total']), f"{r['Efficiency']}%"])
                t = Table(data, colWidths=[4.5*cm]*4)
                t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.toColor("#16A085")), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
                elements.append(t)

            # 3. VERTEILUNG
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("3. Zuspiel-Verteilung", styles['Heading1']))
            dist_df = self.calculate_setting_distribution(game_id)
            if not dist_df.empty:
                data = [["Zuspieler", "Angreifer", "Versuche", "Prozent"]]
                for _, r in dist_df.iterrows():
                    data.append([r['Zuspieler'], r['Angreifer'], int(r['Total']), f"{r['Prozent']}%"])
                t = Table(data, colWidths=[4.5*cm]*4)
                t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.toColor("#8E44AD")), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
                elements.append(t)

            doc.build(elements)
            return True
        except Exception as e:
            print(f"Fehler PDF: {e}")
            return False