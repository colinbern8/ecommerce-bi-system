"""
Business visualization generation using matplotlib and seaborn.
Saves PNG figures to reports/visualizations/ at DPI 300.
"""

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


class BusinessVisualizations:
    """
    Generates standard business charts from analytics DataFrames.
    Output directory is created in __init__; all plots can save as PNG.
    """

    def __init__(self, output_dir: str = "reports/visualizations") -> None:
        """
        Set up output directory, seaborn style, and color palette.

        Args:
            output_dir: Directory for saved plots (relative to project root or absolute).
        """
        project_root = Path(__file__).resolve().parent.parent
        self.output_dir = Path(output_dir)
        if not self.output_dir.is_absolute():
            self.output_dir = project_root / self.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        sns.set_style("whitegrid")
        sns.set_palette("husl")
        self.dpi = 300
        print(f"BusinessVisualizations: output directory = {self.output_dir}")

    def plot_monthly_revenue_trends(self, df: pd.DataFrame, save: bool = True) -> None:
        """
        Dual-axis chart: bars for revenue, line for order count by month.

        Args:
            df: DataFrame with year_month, revenue, order_count.
            save: If True, save PNG to output_dir.
        """
        if df.empty:
            print("plot_monthly_revenue_trends: empty DataFrame, skipping")
            return
        fig, ax1 = plt.subplots(figsize=(10, 5))
        x = range(len(df))
        ax1.bar(x, df["revenue"], color="steelblue", alpha=0.8, label="Revenue")
        ax1.set_ylabel("Revenue", color="steelblue")
        ax1.set_xlabel("Month")
        ax1.tick_params(axis="y", labelcolor="steelblue")
        ax2 = ax1.twinx()
        ax2.plot(x, df["order_count"], color="coral", marker="o", label="Order count")
        ax2.set_ylabel("Order count", color="coral")
        ax2.tick_params(axis="y", labelcolor="coral")
        ax1.set_xticks(x)
        ax1.set_xticklabels(df["year_month"], rotation=45, ha="right")
        ax1.set_title("Monthly Revenue Trends")
        fig.tight_layout()
        if save:
            path = self.output_dir / "monthly_revenue_trends.png"
            fig.savefig(path, dpi=self.dpi, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved: {path}")
        else:
            plt.show()

    def plot_profit_margins(self, df: pd.DataFrame, save: bool = True) -> None:
        """
        Horizontal bar chart for profit margin by category; optional scatter for revenue vs profit.

        Args:
            df: DataFrame with category, revenue, cost, profit, profit_margin_pct.
            save: If True, save PNG.
        """
        if df.empty:
            print("plot_profit_margins: empty DataFrame, skipping")
            return
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        sns.barplot(data=df, y="category", x="profit_margin_pct", ax=ax1, palette="viridis")
        ax1.set_xlabel("Profit margin (%)")
        ax1.set_ylabel("Category")
        ax1.set_title("Profit Margin by Category")
        sc = ax2.scatter(df["revenue"], df["profit"], c=df["profit_margin_pct"], cmap="viridis", s=80)
        ax2.set_xlabel("Revenue")
        ax2.set_ylabel("Profit")
        ax2.set_title("Revenue vs Profit by Category")
        plt.colorbar(sc, ax=ax2, label="Profit margin %")
        fig.tight_layout()
        if save:
            path = self.output_dir / "profit_margins.png"
            fig.savefig(path, dpi=self.dpi, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved: {path}")
        else:
            plt.show()

    def plot_customer_lifetime_value(self, df: pd.DataFrame, save: bool = True) -> None:
        """
        Histogram of CLV and pie chart of revenue share by order-count bucket.

        Args:
            df: DataFrame with customer_id, total_revenue, order_count.
            save: If True, save PNG.
        """
        if df.empty:
            print("plot_customer_lifetime_value: empty DataFrame, skipping")
            return
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        ax1.hist(df["total_revenue"], bins=30, color="teal", alpha=0.7, edgecolor="black")
        ax1.set_xlabel("Total revenue (CLV)")
        ax1.set_ylabel("Number of customers")
        ax1.set_title("Customer Lifetime Value Distribution")
        buckets = pd.cut(df["order_count"], bins=[0, 1, 3, 10, 1000], labels=["1", "2-3", "4-10", "11+"])
        rev_by_bucket = df.groupby(buckets)["total_revenue"].sum()
        ax2.pie(rev_by_bucket, labels=rev_by_bucket.index, autopct="%1.1f%%", startangle=90)
        ax2.set_title("Revenue Share by Order Count Bucket")
        fig.tight_layout()
        if save:
            path = self.output_dir / "customer_lifetime_value.png"
            fig.savefig(path, dpi=self.dpi, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved: {path}")
        else:
            plt.show()

    def plot_pareto_analysis(self, df: pd.DataFrame, save: bool = True) -> None:
        """
        Bar chart of product revenue with cumulative % line (Pareto).

        Args:
            df: DataFrame with product_id, product_name, revenue, cum_revenue, cum_pct.
            save: If True, save PNG.
        """
        if df.empty:
            print("plot_pareto_analysis: empty DataFrame, skipping")
            return
        # Limit to top N for readability
        top_n = min(25, len(df))
        plot_df = df.head(top_n)
        fig, ax1 = plt.subplots(figsize=(12, 5))
        x = range(len(plot_df))
        ax1.bar(x, plot_df["revenue"], color="slateblue", alpha=0.8, label="Revenue")
        ax1.set_ylabel("Revenue")
        ax1.set_xlabel("Product (top by revenue)")
        ax2 = ax1.twinx()
        ax2.plot(x, plot_df["cum_pct"], color="darkred", marker="o", linewidth=2, label="Cumulative %")
        ax2.set_ylabel("Cumulative % of total revenue")
        ax2.set_ylim(0, 105)
        ax1.set_xticks(x)
        ax1.set_xticklabels(plot_df["product_name"].str[:20], rotation=45, ha="right")
        ax1.set_title("Pareto Analysis: Product Revenue")
        fig.tight_layout()
        if save:
            path = self.output_dir / "pareto_analysis.png"
            fig.savefig(path, dpi=self.dpi, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved: {path}")
        else:
            plt.show()

    def plot_churn_risk_distribution(self, df: pd.DataFrame, save: bool = True) -> None:
        """
        Bar chart of churned vs not churned count; histogram of a churn feature (e.g. order_count_12m).

        Args:
            df: DataFrame with is_churned and churn features (e.g. order_count_12m).
            save: If True, save PNG.
        """
        if df.empty:
            print("plot_churn_risk_distribution: empty DataFrame, skipping")
            return
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        churn_counts = df["is_churned"].value_counts().sort_index()
        churn_counts.plot(kind="bar", ax=ax1, color=["green", "red"], alpha=0.8)
        ax1.set_xticklabels(["Not churned", "Churned"], rotation=0)
        ax1.set_ylabel("Number of customers")
        ax1.set_title("Churn Distribution")
        ax2.hist(df["order_count_12m"], bins=20, color="purple", alpha=0.7, edgecolor="black")
        ax2.set_xlabel("Order count (last 12 months)")
        ax2.set_ylabel("Count")
        ax2.set_title("Order Count Distribution")
        fig.tight_layout()
        if save:
            path = self.output_dir / "churn_risk_distribution.png"
            fig.savefig(path, dpi=self.dpi, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved: {path}")
        else:
            plt.show()

    def generate_all_visualizations(self, analytics_results: dict[str, Any]) -> None:
        """
        Call all plot methods with the corresponding DataFrames from get_all_kpis().

        Args:
            analytics_results: Dict from BusinessAnalytics.get_all_kpis().
        """
        self.plot_monthly_revenue_trends(analytics_results.get("monthly_revenue_trends", pd.DataFrame()), save=True)
        self.plot_profit_margins(analytics_results.get("profit_margins", pd.DataFrame()), save=True)
        self.plot_customer_lifetime_value(analytics_results.get("customer_lifetime_value", pd.DataFrame()), save=True)
        self.plot_pareto_analysis(analytics_results.get("pareto_analysis", pd.DataFrame()), save=True)
        self.plot_churn_risk_distribution(analytics_results.get("churn_features", pd.DataFrame()), save=True)
        print("All visualizations generated.")


if __name__ == "__main__":
    from pathlib import Path
    import sys
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))
    from src.database import DatabaseManager
    from src.analytics import BusinessAnalytics
    db = DatabaseManager(config_path=str(project_root / "config" / "config.yaml"))
    analytics = BusinessAnalytics(db)
    viz = BusinessVisualizations()
    try:
        results = analytics.get_all_kpis()
        viz.generate_all_visualizations(results)
    finally:
        db.close()
