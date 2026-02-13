from __future__ import annotations
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import numpy as np
from typing import Dict

def _first_numeric_column(df: pd.DataFrame) -> str | None:
    numeric_cols = df.select_dtypes(include="number").columns
    return numeric_cols[0] if len(numeric_cols) > 0 else None

def _first_categorical_column(df: pd.DataFrame, max_unique: int = 15) -> str | None:
    non_numeric = df.select_dtypes(exclude="number")
    for col in non_numeric.columns:
        if non_numeric[col].nunique(dropna=True) <= max_unique:
            return col
    return None

def create_charts(df: pd.DataFrame, output_dir: str = None) -> Dict[str, str]:
    """
    Create a set of interactive 3D Plotly charts for statistical outputs.
    Returns a dict mapping chart name -> Plotly JSON string.
    """
    charts: Dict[str, str] = {}
    
    numeric_col = _first_numeric_column(df)
    categorical_col = _first_categorical_column(df)

    # 1. 3D Distribution (Histogram in 3D Space)
    if numeric_col:
        counts, bins = np.histogram(df[numeric_col].dropna(), bins=20)
        bin_centers = (bins[:-1] + bins[1:]) / 2
        
        # Create a 3D Bar effect using Mesh3d or multiple Scatter3d points
        # For simplicity and performance, we'll use Scatter3d with vertical lines (stems)
        # to represent the histogram bars in 3D.
        fig = go.Figure()
        
        # Consolidate stems into a single trace for performance
        stem_x = []
        stem_y = []
        stem_z = []
        
        for i in range(len(counts)):
            stem_x.extend([bin_centers[i], bin_centers[i], None])
            stem_y.extend([0, counts[i], None])
            stem_z.extend([0, 0, None])

        fig.add_trace(go.Scatter3d(
            x=stem_x,
            y=stem_y,
            z=stem_z,
            mode='lines',
            line=dict(color='#000000', width=8),
            showlegend=False,
            hoverinfo='skip'
        ))

            
        # Add the tops
        fig.add_trace(go.Scatter3d(
            x=bin_centers,
            y=counts,
            z=[0] * len(counts),
            mode='markers',
            marker=dict(size=8, color='#FFD600', symbol='diamond', line=dict(color='black', width=2)), # YELLOW TOPS
            name='Frequency',
            hovertemplate="<b>Value Range:</b> %{x}<br><b>Count:</b> %{y}<extra></extra>"
        ))


        fig.update_layout(
            title=f"3D Distribution of {numeric_col}",
            scene=dict(
                xaxis_title=numeric_col,
                yaxis_title="Frequency",
                zaxis_title="",
                zaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                bgcolor='rgba(0,0,0,0)',
                dragmode='orbit' # Explicitly set for rotation stability
            ),
            hoverlabel=dict(
                bgcolor="#FFD600",
                bordercolor="#000000",
                font_size=12,
                font_family="Outfit",
                font_color="#000000"
            ),
            font_family="Outfit",
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, b=0, t=40)
        )
        charts["distribution"] = fig.to_json()

    # 2. 3D Line Chart (Trend Analysis with Depth)
    if numeric_col:
        # Downsample for performance if dataset is large
        plot_df = df.copy()
        if len(plot_df) > 1000:
            plot_df = plot_df.sample(n=1000).sort_index()

        y_values = plot_df[numeric_col].values
        x_values = plot_df.index
        z_values = np.linspace(0, 10, len(y_values))

        fig = go.Figure()
        fig.add_trace(go.Scatter3d(
            x=x_values,
            y=y_values,
            z=z_values,
            mode='lines+markers',
            line=dict(color='#000000', width=4), # Black line
            marker=dict(size=4, color='#FFD600', opacity=1, line=dict(color='black', width=1)), # Yellow markers
            name="Trend",
            hovertemplate="<b>Index:</b> %{x}<br><b>Value:</b> %{y}<br><b>Sequence:</b> %{z}<extra></extra>"
        ))

        fig.update_layout(
            title=f"3D Trend Analysis: {numeric_col}",
            scene=dict(
                xaxis_title="Observation ID",
                yaxis_title=numeric_col,
                zaxis_title="Time Depth",
                bgcolor='rgba(0,0,0,0)',
                dragmode='orbit'
            ),
            hoverlabel=dict(
                bgcolor="#FFD600",
                bordercolor="#000000",
                font_size=12,
                font_family="Outfit",
                font_color="#000000"
            ),
            font_family="Outfit",
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, b=0, t=40)
        )
        charts["trend"] = fig.to_json()

    # 3. 3. 3D Bar Chart (Categorical Aggregation)
    if categorical_col and numeric_col:
        agg_df = df.groupby(categorical_col)[numeric_col].mean().reset_index().sort_values(by=numeric_col, ascending=False).head(10)
        
        fig = go.Figure()
        
        # Create 3D Cylinders/Bars
        colors = ['#FFD600', '#000000', '#FFD600', '#000000'] # Alternating brand colors
        for i, row in agg_df.iterrows():
            fig.add_trace(go.Scatter3d(
                x=[row[categorical_col], row[categorical_col]],
                y=[0, row[numeric_col]],
                z=[i, i],
                mode='lines+markers',
                line=dict(color=colors[i % len(colors)], width=15),
                marker=dict(size=10, symbol='square', line=dict(color='black', width=2)),
                name=str(row[categorical_col]),
                hovertemplate=f"<b>{categorical_col}:</b> {row[categorical_col]}<br><b>Avg {numeric_col}:</b> {row[numeric_col]:.2f}<extra></extra>"
            ))

        fig.update_layout(
            title=f"3D Average {numeric_col} by {categorical_col}",
            scene=dict(
                xaxis_title=categorical_col,
                yaxis_title=f"Avg {numeric_col}",
                zaxis_title="Category Index",
                bgcolor='rgba(0,0,0,0)',
                dragmode='orbit'
            ),
            hoverlabel=dict(
                bgcolor="#FFD600",
                bordercolor="#000000",
                font_size=12,
                font_family="Outfit",
                font_color="#000000"
            ),
            font_family="Outfit",
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, b=0, t=40)
        )
        charts["categorical"] = fig.to_json()

    # 4. 3D Pie Chart (Volumetric Composition)
    if categorical_col:
        counts = df[categorical_col].value_counts().head(10).reset_index()
        counts.columns = [categorical_col, 'count']
        
        theta = np.linspace(0, 2*np.pi, len(counts), endpoint=False)
        radius = counts['count'].values
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter3d(
            x=np.cos(theta) * 10,
            y=np.sin(theta) * 10,
            z=radius,
            mode='markers+text',
            marker=dict(
                size=radius/radius.max() * 30,
                color=radius,
                colorscale=[[0, '#000000'], [1, '#FFD600']], # Black to Yellow
                showscale=False,
                line=dict(color='black', width=2)
            ),

            text=counts[categorical_col],
            name="Composition",
            hovertemplate="<b>Category:</b> %{text}<br><b>Count:</b> %{z}<extra></extra>"
        ))

        fig.update_layout(
            title=f"3D Composition of {categorical_col}",
            scene=dict(
                xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, title=""),
                yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, title=""),
                zaxis_title="Count",
                bgcolor='rgba(0,0,0,0)',
                dragmode='orbit'
            ),
            hoverlabel=dict(
                bgcolor="#FFD600",
                bordercolor="#000000",
                font_size=12,
                font_family="Outfit",
                font_color="#000000"
            ),
            font_family="Outfit",
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, b=0, t=40)
        )
        charts["composition"] = fig.to_json()

    return charts



