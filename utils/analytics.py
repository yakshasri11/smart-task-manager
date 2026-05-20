import pandas as pd
import numpy as np


def compute_stats(tasks: list) -> dict:
    """
    takes a list of task dicts and returns analytics summary
    using pandas for data manipulation and numpy for calculations
    """

    
    if not tasks:
        return {
            "total": 0,
            "completed": 0,
            "pending": 0,
            "in_progress": 0,
            "completion_pct": 0.0,
            "high_priority_count": 0,
            "priority_breakdown": {"low": 0, "medium": 0, "high": 0},
            "avg_per_day": 0.0,
        }

    df = pd.DataFrame(tasks)

    total       = len(df)
    completed   = int((df["status"] == "completed").sum())
    pending     = int((df["status"] == "pending").sum())
    in_progress = int((df["status"] == "in_progress").sum())

    
    completion_pct = float(np.round((completed / total) * 100, 1))

    
    prio_counts = df["priority"].value_counts().to_dict()
    priority_breakdown = {
        "low":    int(prio_counts.get("low", 0)),
        "medium": int(prio_counts.get("medium", 0)),
        "high":   int(prio_counts.get("high", 0)),
    }

    high_priority_count = priority_breakdown["high"]

    
    df["created_at"] = pd.to_datetime(df["created_at"])
    days_active = df["created_at"].dt.date.nunique()
    avg_per_day = float(np.round(total / max(days_active, 1), 2))

    return {
        "total":                total,
        "completed":            completed,
        "pending":              pending,
        "in_progress":          in_progress,
        "completion_pct":       completion_pct,
        "high_priority_count":  high_priority_count,
        "priority_breakdown":   priority_breakdown,
        "avg_per_day":          avg_per_day,
    }