import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


class ChartBuilder:
    """Générateur de graphiques Plotly"""

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def plot_sales_trend(self):
        """Courbe d'évolution"""
        if self.df.empty or 'order_date' not in self.df.columns: return go.Figure()

        df_trend = self.df.copy()
        df_trend['month'] = df_trend['order_date'].dt.to_period('M').astype(str)
        daily_sales = df_trend.groupby('month')[['sales', 'profit']].sum().reset_index()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily_sales['month'], y=daily_sales['sales'],
                                 mode='lines+markers', name='Ventes (€)', line=dict(color='#1f77b4')))
        fig.add_trace(go.Scatter(x=daily_sales['month'], y=daily_sales['profit'],
                                 mode='lines', name='Profit (€)', line=dict(color='#2ca02c', dash='dot')))
        fig.update_layout(title="Tendance Mensuelle", hovermode="x unified")
        return fig

    def plot_top_products_bar(self, n=10):
        """Barres horizontales Top Produits"""
        if self.df.empty: return go.Figure()

        col_prod = 'product_name' if 'product_name' in self.df.columns else 'product_id'
        if col_prod not in self.df.columns: return go.Figure()

        top_prod = self.df.groupby(col_prod)['sales'].sum().sort_values(ascending=True).tail(n)

        fig = px.bar(top_prod, x=top_prod.values, y=top_prod.index, orientation='h',
                     title=f"Top {n} Produits", labels={'x': 'CA (€)', 'y': ''},
                     color=top_prod.values, color_continuous_scale='Blues')
        return fig

    def plot_top_customers_bar(self, n=10):
        """Barres horizontales Top Clients (Nouveau)"""
        if self.df.empty: return go.Figure()

        col_cust = 'customer_name' if 'customer_name' in self.df.columns else 'customer_id'
        if col_cust not in self.df.columns: return go.Figure()

        top_cust = self.df.groupby(col_cust)['sales'].sum().sort_values(ascending=True).tail(n)

        fig = px.bar(top_cust, x=top_cust.values, y=top_cust.index, orientation='h',
                     title=f"Top {n} Meilleurs Clients", labels={'x': 'Achat Total (€)', 'y': ''},
                     color=top_cust.values, color_continuous_scale='Greens')
        return fig

    def plot_distribution(self, col_name, title):
        """Pie Chart générique (pour Catégorie, Segment, Région...)"""
        if col_name not in self.df.columns or self.df.empty: return None

        data = self.df.groupby(col_name)['sales'].sum().reset_index()
        fig = px.pie(data, values='sales', names=col_name, title=title, hole=0.4)
        return fig