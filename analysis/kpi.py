import pandas as pd


class KPICalculator:
    """Calculateur d'indicateurs de performance (KPI)"""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        if 'order_date' in self.df.columns:
            self.df['order_date'] = pd.to_datetime(self.df['order_date'])

    def get_global_metrics(self):
        """Retourne les KPI principaux incluant SALES"""
        if self.df.empty: return {}

        # 1. KPI Sales (Ajouté)
        total_sales = self.df['sales'].sum() if 'sales' in self.df.columns else 0

        # 2. Autres KPI
        total_profit = self.df['profit'].sum() if 'profit' in self.df.columns else 0
        total_quantity = self.df['quantity'].sum() if 'quantity' in self.df.columns else 0

        order_count = self.df['order_id'].nunique() if 'order_id' in self.df.columns else 0
        avg_basket = total_sales / order_count if order_count > 0 else 0
        profit_margin = (total_profit / total_sales * 100) if total_sales > 0 else 0

        # Croissance Mensuelle
        growth = 0.0
        if 'order_date' in self.df.columns and 'sales' in self.df.columns:
            monthly_sales = self.df.set_index('order_date').resample('M')['sales'].sum()
            if len(monthly_sales) >= 2:
                last = monthly_sales.iloc[-1]
                prev = monthly_sales.iloc[-2]
                if prev > 0: growth = ((last - prev) / prev) * 100

        return {
            "total_sales": total_sales,
            "total_profit": total_profit,
            "total_quantity": total_quantity,
            "order_count": order_count,
            "avg_basket": avg_basket,
            "profit_margin": profit_margin,
            "growth": growth
        }

    def get_top_customers(self, n=10):
        col = 'customer_name' if 'customer_name' in self.df.columns else 'customer_id'
        if col not in self.df.columns: return pd.DataFrame()
        return (self.df.groupby(col).agg({'sales': 'sum', 'order_id': 'nunique'})
                .rename(columns={'order_id': 'commandes'})
                .sort_values('sales', ascending=False).head(n))