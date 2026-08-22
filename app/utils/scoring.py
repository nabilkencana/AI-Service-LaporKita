from typing import Optional
from app.core.config import settings


def normalize_support_count(support_count: int, max_support: int = 100) -> float:
    """Normalize community upvotes to a 0.0 - 1.0 scale."""
    if support_count <= 0:
        return 0.0
    return min(1.0, support_count / max_support)


def normalize_density_factor(report_density: int, max_density: int = 50) -> float:
    """Normalize local cluster report density to a 0.0 - 1.0 scale."""
    if report_density <= 0:
        return 0.0
    return min(1.0, report_density / max_density)


def calculate_urgency_score(
    damage_severity: float,
    support_count: int = 0,
    report_density: int = 0,
    category_name: Optional[str] = None,
    custom_category_weight: Optional[float] = None,
) -> float:
    """
    Calculate Smart Priority urgency score based on Rules.md §1.3 formula:
    urgency_score = (w1 * damage_severity) + (w2 * support_count_normalized)
                  + (w3 * location_density_factor) + (w4 * category_urgency_weight)
    """
    # Clamp damage severity between 0.0 and 1.0
    damage_sev = max(0.0, min(1.0, damage_severity))
    support_norm = normalize_support_count(support_count)
    density_norm = normalize_density_factor(report_density)

    # Category weight lookup
    if custom_category_weight is not None:
        cat_weight = max(0.0, min(1.0, custom_category_weight))
    elif category_name and category_name in settings.DEFAULT_CATEGORY_WEIGHTS:
        cat_weight = settings.DEFAULT_CATEGORY_WEIGHTS[category_name]
    else:
        cat_weight = 0.5  # default moderate weight

    w1 = settings.WEIGHT_DAMAGE_SEVERITY
    w2 = settings.WEIGHT_SUPPORT_COUNT
    w3 = settings.WEIGHT_LOCATION_DENSITY
    w4 = settings.WEIGHT_CATEGORY_URGENCY

    total_score = (
        (w1 * damage_sev)
        + (w2 * support_norm)
        + (w3 * density_norm)
        + (w4 * cat_weight)
    )

    # Ensure result is bounded [0.0, 1.0] and rounded to 4 decimal places
    return round(max(0.0, min(1.0, total_score)), 4)
