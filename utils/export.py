"""
Module d'exportation PDF uniquement
"""
from fpdf import FPDF
import pandas as pd


class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Rapport de Ventes - BI Dashboard', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def generate_pdf_report(df_filtered, kpi_metrics, forecast_df=None):
    """
    Génère un fichier PDF binaire prêt au téléchargement
    """
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # --- 1. KPI ---
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, txt="1. Performance (KPI)", ln=True)
    pdf.set_font("Arial", size=11)

    if kpi_metrics:
        # On remplace € par EUR pour compatibilité PDF
        sales = f"{kpi_metrics.get('total_sales', 0):,.2f} EUR"
        profit = f"{kpi_metrics.get('total_profit', 0):,.2f} EUR"
        qty = f"{kpi_metrics.get('total_quantity', 0):,.0f}"

        pdf.cell(0, 8, txt=f"Chiffre d'Affaires : {sales}", ln=True)
        pdf.cell(0, 8, txt=f"Profit Total : {profit}", ln=True)
        pdf.cell(0, 8, txt=f"Quantité Vendue : {qty}", ln=True)
    else:
        pdf.cell(0, 10, txt="Données indisponibles.", ln=True)

    pdf.ln(10)

    # --- 2. PRÉVISIONS ---
    if forecast_df is not None and not forecast_df.empty:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, txt="2. Prévisions", ln=True)
        pdf.set_font("Arial", size=10)

        pdf.set_fill_color(220, 220, 220)
        pdf.cell(90, 8, "Date", 1, 0, 'C', 1)
        pdf.cell(90, 8, "Ventes (EUR)", 1, 1, 'C', 1)

        for _, row in forecast_df.head(5).iterrows():
            d = str(row['Date'])[:10]
            v = f"{row['Predicted_Sales']:.2f}"
            pdf.cell(90, 8, d, 1, 0, 'C')
            pdf.cell(90, 8, v, 1, 1, 'C')
        pdf.ln(10)

    # --- 3. DATA ---
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, txt="3. Données récentes (Top 20)", ln=True)
    pdf.set_font("Arial", size=8)

    cols = ['order_date', 'category', 'sales', 'country/region']
    final_cols = [c for c in cols if c in df_filtered.columns]

    if final_cols:
        col_width = 190 / len(final_cols)
        pdf.set_fill_color(240, 240, 240)

        for c in final_cols:
            pdf.cell(col_width, 8, c.capitalize(), 1, 0, 'C', 1)
        pdf.ln()

        for _, row in df_filtered[final_cols].head(20).iterrows():
            for c in final_cols:
                # Encodage latin-1 obligatoire pour FPDF standard
                val = str(row[c]).replace('€', '').encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(col_width, 6, val[:25], 1, 0, 'C')
            pdf.ln()

    return pdf.output(dest='S').encode('latin-1')