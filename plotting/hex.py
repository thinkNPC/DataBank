import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns

import utils
from plotting.style import NULL_GREY, npc_style

UTLA_HEXES = "utla_hex.csv"
LTLA_HEXES = "ltla_hex.csv"


def get_hexes(fname):
    df = pd.read_csv(os.path.join(utils.RESOURCE_DIR, fname))
    return df


def plot_hexes(hexes, df, loc_col, plot_col):
    print(df.head(10))
    df = pd.merge(hexes, df, how="left", on=loc_col)
    fig = go.Figure()
    df["display_color"] = df[plot_col]
    zmax = 15
    mask = df["display_color"] > zmax
    df.loc[mask, "display_color"] = zmax

    df_valid = df.loc[df[plot_col].notnull()]
    fig.add_trace(
        go.Scatter(
            x=df_valid["grid_x"],
            y=df_valid["grid_y"],
            text=df_valid["la_name"],
            hoverinfo="z+text",
            mode="markers",
            marker_symbol="hexagon",
            marker_size=12,
            marker_color=df_valid["display_color"],
            marker=dict(
                colorscale=sns.color_palette("magma_r").as_hex(),
            ),
        )
    )
    df_null = df.loc[df[plot_col].isnull()]
    fig.add_trace(
        go.Scatter(
            x=df_null["grid_x"],
            y=df_null["grid_y"],
            text=df_null["la_name"],
            hoverinfo="z+text",
            mode="markers",
            marker_symbol="hexagon",
            marker_size=12,
            marker_color=NULL_GREY,
        )
    )
    fig.update_yaxes(
        scaleanchor="x",
        scaleratio=1,
    )
    npc_style(fig)
    return fig
