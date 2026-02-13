from __future__ import annotations

import pandas as pd


def basic_statistics(df: pd.DataFrame) -> str:
    """
    Return an HTML table with basic summary statistics for all columns.
    """
    # include='all' to also show non-numeric columns (count, unique, top, freq)
    summary = df.describe(include="all").transpose()
    summary.index.name = "column"
    summary.reset_index(inplace=True)

    return summary.to_html(
        classes="table table-striped table-sm",
        border=0,
        index=False,
        justify="center",
    )


def column_overview(df: pd.DataFrame) -> str:
    """
    Return an HTML table summarizing column dtypes and missing values.
    """
    info_df = pd.DataFrame(
        {
            "column": df.columns,
            "dtype": df.dtypes.astype(str).values,
            "missing": df.isnull().sum().values,
            "non_null": df.notnull().sum().values,
        }
    )

    return info_df.to_html(
        classes="table table-bordered table-sm",
        border=0,
        index=False,
        justify="center",
    )

def generate_text_insights(df: pd.DataFrame) -> list[dict]:
    """
    Generate structured natural language insights from numerical columns.
    """
    insights = []
    numeric_df = df.select_dtypes(include=["number"])

    if numeric_df.empty:
        return []

    for col in numeric_df.columns:
        col_data = numeric_df[col].dropna()
        if col_data.empty:
            continue

        max_val = col_data.max()
        min_val = col_data.min()
        mean_val = col_data.mean()

        # Trend Analysis
        if len(col_data) > 1:
            mid = len(col_data) // 2
            first_half = col_data.iloc[:mid].mean()
            second_half = col_data.iloc[mid:].mean()
            
            if second_half > first_half:
                trend = "Showing an upward (increasing) trajectory"
            elif second_half < first_half:
                trend = "Showing a downward (decreasing) trajectory"
            else:
                trend = "Currently stable with no significant movement"
        else:
            trend = "Insufficient data to determine a trend"

        insights.append({
            "column": col,
            "max": f"{max_val:,.2f}",
            "min": f"{min_val:,.2f}",
            "avg": f"{mean_val:,.2f}",
            "trend": trend
        })

    return insights
