"""
Main pipeline: analytics, visualizations, churn model, and AI executive summary.
"""

import sys
from pathlib import Path

# Ensure project root and src are on path
PROJECT_ROOT = Path(__file__).resolve().parent
SRC = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from database import DatabaseManager
from analytics import BusinessAnalytics
from visualizations import BusinessVisualizations
from ai_summary import AIExecutiveSummary
from churn_model import ChurnPredictionModel


def main() -> None:
    """Run full pipeline: KPIs, visualizations, churn model, AI summary; then close DB."""
    print("=" * 70)
    print("E-Commerce Analytics Pipeline")
    print("=" * 70)

    config_path = PROJECT_ROOT / "config" / "config.yaml"
    db = DatabaseManager(config_path=str(config_path))
    analytics = BusinessAnalytics(db)
    viz = BusinessVisualizations()
    ai_summary = AIExecutiveSummary(config_path=str(config_path))
    churn_model = ChurnPredictionModel()

    print("\n--- Running analytics ---")
    analytics_results = analytics.get_all_kpis()

    print("\n--- Generating visualizations ---")
    viz.generate_all_visualizations(analytics_results)

    print("\n--- Training churn model ---")
    churn_df = analytics_results.get("churn_features")
    if churn_df is not None and not churn_df.empty:
        churn_model.train_and_evaluate(churn_df)
    else:
        print("Churn features empty; skipping churn model.")

    print("\n--- Generating AI executive summary ---")
    try:
        ai_summary.generate_and_save(analytics_results)
    except (ValueError, ImportError) as e:
        print(f"AI summary skipped (set API key in config to enable): {e}")

    print("\n" + "=" * 70)
    print("Outputs:")
    print("  - Reports: reports/")
    print("  - Visualizations: reports/visualizations/")
    print("  - Churn model results: reports/churn_model_results.txt")
    print("  - Executive summary: reports/executive_summary.md (if API key set)")
    print("=" * 70)

    db.close()
    print("Done.")


if __name__ == "__main__":
    main()
