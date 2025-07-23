

import pandas as pd
from pyecharts import options as opts
from pyecharts.globals import ThemeType
from pyecharts.charts import Line


def plot_df_simple(df: pd.DataFrame, 
                   x_col: str, 
                   y_cols: list[str],
                   mark_points = {},
                   title: str = 'DF Plot',
                   theme = ThemeType.DARK,
                   zoom=False,
                   ):
    line_plot = Line(init_opts=opts.InitOpts(
        theme=theme, width='1200px', height='400px'))
    
    line_plot.set_global_opts(
        title_opts=opts.TitleOpts(title=title),
        legend_opts=opts.LegendOpts(pos_left="center", pos_top="7%"),
        xaxis_opts=opts.AxisOpts(
            name=x_col, 
            splitarea_opts=opts.SplitLineOpts(is_show=True),
        ),
        tooltip_opts=opts.TooltipOpts(trigger="axis"),
        yaxis_opts=opts.AxisOpts(
            type_="value",
            min_='dataMin',
            axistick_opts=opts.AxisTickOpts(is_show=True),
            splitline_opts=opts.SplitLineOpts(is_show=True),
            #is_scale=True,
        ),
        datazoom_opts=[
            opts.DataZoomOpts(range_start=0, range_end=100),
            opts.DataZoomOpts(
                type_="inside", range_start=0, range_end=100),
        ] if zoom else []
        ,)

    # add axis 
    line_plot.add_xaxis(xaxis_data=df[x_col].values.tolist())  

    for col_name in y_cols:
        col_series = df[col_name].values.tolist()
        
        mpoints = []
        if col_name in mark_points:
            mpoints = mark_points[col_name]

        line_plot.add_yaxis(
            series_name=col_name,
            y_axis=col_series,
            linestyle_opts=opts.LineStyleOpts(type_='solid', opacity=0.8),
            label_opts=opts.LabelOpts(is_show=False),
            is_symbol_show=False,
            markpoint_opts=opts.MarkPointOpts(
                data=mpoints, 
                label_opts=opts.LabelOpts(position="top", distance=10, font_size = 12)
            ),
        )
    
    return line_plot
