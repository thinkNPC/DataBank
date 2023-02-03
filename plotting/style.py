npc_palette = [
    '#662583',
    '#881866',
    '#C7215D',
    '#EC0080',
    '#EE4023',
    '#F26F21',
    '#F89C1C',
    '#FFCA05',
]

npc_palette_main = npc_palette[:3]
npc_palette_highlight = npc_palette[3:7]

npc_grey = '#E1E1E1'

chart_background = '#f7f7f7'
dark_grey = '#333333'
NULL_GREY = '#CCCCCC'

npc_logo = 'https://npproduction.wpenginepowered.com/wp-content/themes/npc/img/logos/npc-logo.svg'

def npc_style(fig):
  fig.update_layout(
      font_family="Arial",
      font_size=15,
      font_color=dark_grey,
      plot_bgcolor=chart_background,
  )
  axis_args = dict(
      showgrid=False,
      tickfont=dict(size=12),
  )
  fig.update_yaxes(**axis_args)
  fig.update_xaxes(**axis_args)

  fig.add_layout_image(
    dict(
        source=npc_logo,
        xref="paper", yref="paper",
        x=0.95, y=0.95,
        sizex=0.2, sizey=0.2,
        xanchor="right", yanchor="top"
    )
  )
