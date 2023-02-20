import enum
import os
from collections import namedtuple
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns

import utils
from plotting.style import NULL_GREY, npc_style, CONTRAST

UTLA_HEXES = "utla_hex.csv"
LTLA_HEXES = "ltla_hex.csv"


@dataclass
class Geographylevel:
    name_col: str
    code_col: str
    hex_file: str
    hex_scale: float
    boundry_file: str
    rename_col_map: dict


GEOGRAPHY = {
    "LTLA": Geographylevel(
        "la_name",
        "la_code",
        "ltla_hex.csv",
        1,
        "Local_Authority_Districts_(December_2022)_Boundaries_UK_BFC.json",
        {"LAD22CD": "la_code"},
    ),
    "UTLA": Geographylevel(
        "utla_name",
        "utla_code",
        "utla_hex.csv",
        0.8,
        "Counties_and_Unitary_Authorities_(December_2022)_UK_BFC.json",
        {"CTYUA22CD": "utla_code"},
    ),
    "region": Geographylevel(
        "region_name", "region_code", None, 1, "Regions_(December_2022)_EN_BFC.json", {}
    ),
    "country": Geographylevel(
        "country_name",
        "country_code",
        None,
        1,
        "Countries_(December_2022)_GB_BFC.json",
        {},
    ),
}


def get_hexes(geography_level):
    df = pd.read_csv(os.path.join(utils.RESOURCE_DIR, geography_level.hex_file))
    df = df.rename(columns=geography_level.rename_col_map)
    return df


def plot_hexes(df, geography, plot_col, palette="magma_r", zmax=None, highlight=None):
    G = GEOGRAPHY[geography]
    hexes = get_hexes(G)
    df = pd.merge(hexes, df, how="left", on=G.code_col)

    fig = go.Figure()
    df["display_color"] = df[plot_col]
    if zmax:
        mask = df["display_color"] > zmax
        df.loc[mask, "display_color"] = zmax

    df_valid = df.loc[df[plot_col].notnull()].copy()
    df_null = df.loc[df[plot_col].isnull()].copy()
    df_null["display_color"] = NULL_GREY

    for sub_df in [df_valid, df_null]:
        fig.add_trace(
            go.Scatter(
                x=sub_df["grid_x"],
                y=sub_df["grid_y"],
                mode="markers",
                marker_symbol="hexagon",
                marker_size=12,
                marker_color=sub_df["display_color"],
                marker=dict(
                    colorscale=sns.color_palette(palette).as_hex(),
                ),
                text=sub_df[G.name_col],
                customdata=sub_df[plot_col].round(0),
                hovertemplate="%{text}: %{customdata}",
                name="",
            )
        )
    
    if highlight is not None:
        dfh = df[df[G.code_col].isin(highlight.values)]
        fig.add_trace(
                go.Scatter(
                x=dfh["grid_x"],
                y=dfh["grid_y"],
                mode="markers",
                hoverinfo='skip',
                marker=dict(
                    symbol="hexagon",
                    size=12,
                    color='rgba(0,0,0,0)',
                    line=dict(
                        color=CONTRAST,
                        width=1.5,
                    )
                )
            )
        )

    fig.update_yaxes(
        scaleanchor="x",
        scaleratio=1,
    )
    npc_style(fig)
    fig.update_layout(
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    fig.update_layout(
        autosize=False,
        width=350 * G.hex_scale,
        height=350 * G.hex_scale,
        margin=dict(b=0, t=0, r=0, l=0),
    )

    return fig