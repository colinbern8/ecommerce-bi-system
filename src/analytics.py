"""
Business analytics and KPI calculations.
Uses DatabaseManager to run SQL queries with CTEs; all metrics filter for Completed orders.
"""

from typing import Any

import pandas as pd

from database import DatabaseManager


class BusinessAnalytics:
    """
    Computes business KPIs: revenue trends, profit margins, CLV, Pareto, churn features.
    All order-based metrics consider only order_status = 'Completed'.
    """

    def __init__(self, db: DatabaseManager) -> None:
        """
        Initialize with a DatabaseManager instance.

        Args:
            db: DatabaseManager for executing queries.
        """
        self.db = db

    def calculate_monthly_revenue_trends(self) -> pd.DataFrame:
        """
        Revenue by month for the last 12 months (completed orders only).

        Returns:
            DataFrame with columns: year_month, revenue, order_count.
        """
        query = """
        WITH completed_orders AS (
            SELECT o.order_id, o.order_date
            FROM orders o
            WHERE o.order_status = 'Completed'
            AND o.order_date >= date('now', '-12 months')
        ),
        monthly AS (
            SELECT
                strftime('%Y-%m', co.order_date) AS year_month,
                SUM(oi.quantity * oi.unit_price) AS revenue,
                COUNT(DISTINCT co.order_id) AS order_count
            FROM completed_orders co
            JOIN order_items oi ON oi.order_id = co.order_id
            GROUP BY strftime('%Y-%m', co.order_date)
        )
        SELECT year_month, revenue, order_count
        FROM monthly
        ORDER BY year_month;
        """
        return self.db.execute_query(query)

    def calculate_profit_margins(self) -> pd.DataFrame:
        """
        Revenue, cost, profit, and profit margin by product category (completed orders).

        Returns:
            DataFrame with columns: category, revenue, cost, profit, profit_margin_pct.
        """
        query = """
        WITH completed_items AS (
            SELECT oi.product_id, oi.quantity, oi.unit_price, oi.unit_cost
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            WHERE o.order_status = 'Completed'
        ),
        by_category AS (
            SELECT
                p.category,
                SUM(ci.quantity * ci.unit_price) AS revenue,
                SUM(ci.quantity * ci.unit_cost) AS cost
            FROM completed_items ci
            JOIN products p ON p.product_id = ci.product_id
            GROUP BY p.category
        )
        SELECT
            category,
            revenue,
            cost,
            (revenue - cost) AS profit,
            CASE WHEN revenue > 0 THEN 100.0 * (revenue - cost) / revenue ELSE 0 END AS profit_margin_pct
        FROM by_category
        ORDER BY revenue DESC;
        """
        return self.db.execute_query(query)

    def calculate_customer_lifetime_value(self) -> pd.DataFrame:
        """
        Customer-level total revenue (CLV) for completed orders.

        Returns:
            DataFrame with columns: customer_id, total_revenue, order_count.
        """
        query = """
        WITH completed_orders AS (
            SELECT order_id, customer_id
            FROM orders
            WHERE order_status = 'Completed'
        ),
        customer_revenue AS (
            SELECT
                co.customer_id,
                SUM(oi.quantity * oi.unit_price) AS total_revenue,
                COUNT(DISTINCT co.order_id) AS order_count
            FROM completed_orders co
            JOIN order_items oi ON oi.order_id = co.order_id
            GROUP BY co.customer_id
        )
        SELECT customer_id, total_revenue, order_count
        FROM customer_revenue
        ORDER BY total_revenue DESC;
        """
        return self.db.execute_query(query)

    def perform_pareto_analysis(self) -> pd.DataFrame:
        """
        Product-level revenue (completed orders) with cumulative revenue for Pareto.

        Returns:
            DataFrame with columns: product_id, product_name, revenue, cum_revenue, cum_pct.
        """
        query = """
        WITH completed_items AS (
            SELECT oi.product_id, (oi.quantity * oi.unit_price) AS line_revenue
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            WHERE o.order_status = 'Completed'
        ),
        product_revenue AS (
            SELECT
                ci.product_id,
                SUM(ci.line_revenue) AS revenue
            FROM completed_items ci
            GROUP BY ci.product_id
        ),
        ranked AS (
            SELECT
                pr.product_id,
                p.product_name,
                pr.revenue,
                SUM(pr.revenue) OVER (ORDER BY pr.revenue DESC) AS cum_revenue
            FROM product_revenue pr
            JOIN products p ON p.product_id = pr.product_id
        ),
        total AS (
            SELECT SUM(revenue) AS total_revenue FROM product_revenue
        )
        SELECT
            r.product_id,
            r.product_name,
            r.revenue,
            r.cum_revenue,
            CASE WHEN t.total_revenue > 0 THEN 100.0 * r.cum_revenue / t.total_revenue ELSE 0 END AS cum_pct
        FROM ranked r
        CROSS JOIN total t
        ORDER BY r.revenue DESC;
        """
        return self.db.execute_query(query)

    def calculate_churn_features(self) -> pd.DataFrame:
        """
        Customer-level features for churn: churn = no order in last 90 days.
        Includes order counts, recency, revenue, and is_churned flag.

        Returns:
            DataFrame with churn features and is_churned (1 = churned).
        """
        query = """
        WITH cutoff AS (
            SELECT date('now', '-90 days') AS cutoff_date
        ),
        completed_orders AS (
            SELECT o.order_id, o.customer_id, o.order_date
            FROM orders o, cutoff c
            WHERE o.order_status = 'Completed'
            AND o.order_date >= date('now', '-1 year')
        ),
        last_order AS (
            SELECT customer_id, MAX(order_date) AS last_order_date
            FROM completed_orders
            GROUP BY customer_id
        ),
        customer_metrics AS (
            SELECT
                co.customer_id,
                COUNT(DISTINCT co.order_id) AS order_count_12m,
                SUM(oi.quantity * oi.unit_price) AS revenue_12m,
                lo.last_order_date
            FROM completed_orders co
            JOIN order_items oi ON oi.order_id = co.order_id
            JOIN last_order lo ON lo.customer_id = co.customer_id
            GROUP BY co.customer_id, lo.last_order_date
        ),
        with_churn AS (
            SELECT
                cm.*,
                CASE WHEN cm.last_order_date < (SELECT cutoff_date FROM cutoff) THEN 1 ELSE 0 END AS is_churned
            FROM customer_metrics cm
        )
        SELECT * FROM with_churn ORDER BY customer_id;
        """
        return self.db.execute_query(query)

    def get_all_kpis(self) -> dict[str, Any]:
        """
        Run all analytics methods and return a single results dictionary.

        Returns:
            Dict with keys: monthly_revenue_trends, profit_margins,
            customer_lifetime_value, pareto_analysis, churn_features.
        """
        print("Computing monthly revenue trends...")
        monthly_revenue_trends = self.calculate_monthly_revenue_trends()
        print("Computing profit margins...")
        profit_margins = self.calculate_profit_margins()
        print("Computing customer lifetime value...")
        customer_lifetime_value = self.calculate_customer_lifetime_value()
        print("Performing Pareto analysis...")
        pareto_analysis = self.perform_pareto_analysis()
        print("Computing churn features...")
        churn_features = self.calculate_churn_features()

        return {
            "monthly_revenue_trends": monthly_revenue_trends,
            "profit_margins": profit_margins,
            "customer_lifetime_value": customer_lifetime_value,
            "pareto_analysis": pareto_analysis,
            "churn_features": churn_features,
        }


if __name__ == "__main__":
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    import sys
    sys.path.insert(0, str(project_root))
    from src.database import DatabaseManager
    db = DatabaseManager(config_path=str(project_root / "config" / "config.yaml"))
    analytics = BusinessAnalytics(db)
    try:
        results = analytics.get_all_kpis()
        for k, v in results.items():
            print(k, type(v), len(v) if hasattr(v, "__len__") else "N/A")
    finally:
        db.close()
