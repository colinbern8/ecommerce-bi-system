"""
AI-powered executive summary using Anthropic Claude API.
Loads API key from config; prepares context from analytics and generates markdown summary.
"""

from pathlib import Path
from typing import Any, Optional

import yaml

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


class AIExecutiveSummary:
    """
    Prepares analytics context and calls Claude to generate an executive summary.
    Saves the result as a markdown file.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        Load config (including Anthropic API key and model) from YAML.

        Args:
            config_path: Path to config YAML. Defaults to config/config.yaml.
        """
        if config_path is None:
            project_root = Path(__file__).resolve().parent.parent
            config_path = project_root / "config" / "config.yaml"
        self.config_path = Path(config_path)
        self._config = self._load_config()
        anth = self._config.get("anthropic", {})
        self.api_key = anth.get("api_key") or ""
        self.model = anth.get("model") or "claude-sonnet-4-20250514"
        self.max_tokens = int(anth.get("max_tokens") or 2000)
        self._client: Optional[Any] = None

    def _load_config(self) -> dict:
        """Load YAML config."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _get_client(self) -> Any:
        """Return Anthropic client; raise if not installed or no API key."""
        if Anthropic is None:
            raise ImportError("anthropic package is not installed")
        if not self.api_key or self.api_key == "your-api-key-here":
            raise ValueError("Set a valid Anthropic API key in config (anthropic.api_key)")
        if self._client is None:
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def prepare_analytics_context(self, analytics_results: dict[str, Any]) -> str:
        """
        Extract key metrics from analytics results into a text summary for the model.

        Args:
            analytics_results: Dict from BusinessAnalytics.get_all_kpis().

        Returns:
            String summary of metrics (revenue, margins, CLV, Pareto, churn).
        """
        parts = []
        mr = analytics_results.get("monthly_revenue_trends")
        if mr is not None and not mr.empty:
            total_rev = mr["revenue"].sum()
            parts.append(f"Monthly revenue (last 12 months): total={total_rev:.2f}; rows: {len(mr)}.")
        pm = analytics_results.get("profit_margins")
        if pm is not None and not pm.empty:
            parts.append(f"Profit margins by category: {pm[['category','profit_margin_pct']].to_dict('records')}.")
        clv = analytics_results.get("customer_lifetime_value")
        if clv is not None and not clv.empty:
            parts.append(f"Customer lifetime value: {len(clv)} customers; total revenue sum={clv['total_revenue'].sum():.2f}.")
        pa = analytics_results.get("pareto_analysis")
        if pa is not None and not pa.empty:
            top5 = pa.head(5)[["product_name", "revenue", "cum_pct"]].to_string()
            parts.append(f"Pareto (top 5 products):\n{top5}")
        churn = analytics_results.get("churn_features")
        if churn is not None and not churn.empty:
            churned = churn["is_churned"].sum()
            parts.append(f"Churn (no order in 90 days): {churned} churned out of {len(churn)} customers.")
        return "\n".join(parts) if parts else "No analytics data provided."

    def generate_executive_summary(
        self,
        analytics_results: dict[str, Any],
        focus_areas: Optional[list[str]] = None,
    ) -> str:
        """
        Call Claude API to generate an executive summary from analytics context.

        Args:
            analytics_results: Dict from BusinessAnalytics.get_all_kpis().
            focus_areas: Optional list of topics to emphasize (e.g. ["revenue", "churn"]).

        Returns:
            Generated summary text (markdown).
        """
        context = self.prepare_analytics_context(analytics_results)
        focus = ", ".join(focus_areas) if focus_areas else "revenue, profitability, customer value, and churn"
        user_content = (
            "You are a business analyst. Based on the following e-commerce analytics metrics, "
            "write a concise executive summary (2–4 paragraphs) in markdown. "
            f"Focus on: {focus}. Do not make up numbers; use only the provided metrics.\n\n"
            "Metrics:\n" + context
        )
        client = self._get_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": user_content}],
        )
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text
        return text

    def save_summary(self, summary: str, output_path: Optional[str] = None) -> Path:
        """
        Write summary to a markdown file.

        Args:
            summary: Full markdown text to save.
            output_path: File path. Defaults to reports/executive_summary.md.

        Returns:
            Path to the saved file.
        """
        if output_path is None:
            project_root = Path(__file__).resolve().parent.parent
            out_dir = project_root / "reports"
            out_dir.mkdir(parents=True, exist_ok=True)
            output_path = out_dir / "executive_summary.md"
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(summary)
        print(f"Summary saved: {path}")
        return path

    def generate_and_save(
        self,
        analytics_results: dict[str, Any],
        focus_areas: Optional[list[str]] = None,
        output_path: Optional[str] = None,
    ) -> Path:
        """
        Generate executive summary and save to file in one call.

        Args:
            analytics_results: Dict from get_all_kpis().
            focus_areas: Optional focus topics.
            output_path: Optional output file path.

        Returns:
            Path to saved markdown file.
        """
        summary = self.generate_executive_summary(analytics_results, focus_areas=focus_areas)
        return self.save_summary(summary, output_path=output_path)


if __name__ == "__main__":
    from pathlib import Path
    import sys
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))
    from src.database import DatabaseManager
    from src.analytics import BusinessAnalytics
    db = DatabaseManager(config_path=str(project_root / "config" / "config.yaml"))
    analytics = BusinessAnalytics(db)
    ai = AIExecutiveSummary()
    try:
        results = analytics.get_all_kpis()
        context = ai.prepare_analytics_context(results)
        print("Context length:", len(context))
        # Uncomment to call API (requires valid key):
        # path = ai.generate_and_save(results)
    except ValueError as e:
        print("Skipping API call:", e)
    finally:
        db.close()
