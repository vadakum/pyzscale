

import pandas as pd
from pyecharts import options as opts
from pyecharts.globals import ThemeType
from pyecharts.charts import Line
from notebooks.img_symbols import down_arrow

"""
plot_trade_signals
"""
def plot_trade_signals(signal_df : pd.DataFrame, 
                       trade_df, 
                       sum_df, 
                       show_pnl_markers=True,
                       show_legends=True, 
                       signal_mark_points=None,
                       mark_offset=2):
    x_data = list(signal_df.ulexts)
    y_data = list(signal_df.ulpx)
    atm_data = list(signal_df.atm)
    val_data = list(signal_df.val)
    #cpx_data = list(signal_df.cpx)
    #ppx_data = list(signal_df.ppx)

    net_pnl = sum_df.net_pnl.item()
    trds = sum_df.num_trades.item()
    cost = sum_df.tcost.item()
    max_profit = sum_df.max_profit.item()
    max_loss = sum_df.max_loss.item()
    lot_size = sum_df.lot_size.item()
    
    title = f"PnL {net_pnl}"
    sub_title = f"Trds {trds} MaxP {max_profit} MaxL {max_loss} Cost {cost} LotSize {lot_size}"
    title_color = 'lightgreen' if net_pnl >= 0 else '#ff5050'
    
    def get_buy_sell_trade_point(row):
        color = 'lightgreen' if row.side == 'BUY' else '#ff5050'
        symbol = 'arrow' if row.side == 'BUY' else down_arrow

        marks = []
        marks.append(opts.MarkPointItem(coord=[row.time, row.ulpx], 
                    symbol=symbol,               
                    symbol_size=[12, 12],
                    itemstyle_opts=opts.ItemStyleOpts(color=color),)
                    )
        if show_pnl_markers:
            if row['profit'] != 0:
                marks.append(opts.MarkPointItem(coord=[row.time, row.ulpx + mark_offset * 2], 
                        value=f"{row['profit']}" if show_legends else '',
                        #value=f"{row['profit']}, {row['sigval']}" if show_legends else '',
                        symbol='square',               
                        symbol_size=[15, 15],
                        itemstyle_opts=opts.ItemStyleOpts(
                            color='rgba(20,250,20,0.4)' if row.profit >= 0 else 'rgba(250,40,40,0.5)'),
                            )
            )
        return marks
        
    
    mark_points = []
    buy_sell_df = trade_df[(trade_df.side == 'BUY') | (trade_df.side == 'SELL')]
    for _, row in buy_sell_df.iterrows():
        mark_points.extend(get_buy_sell_trade_point(row))
    if signal_mark_points:
        mark_points.extend(signal_mark_points)
    #----------------------------------------------------------------------------------------        
    line = (
        Line(init_opts=opts.InitOpts(theme=ThemeType.DARK, width='1300px', height='425px'))
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title=title, 
                subtitle=sub_title,
                title_textstyle_opts=opts.TextStyleOpts(color=title_color, font_size=18),
                subtitle_textstyle_opts=opts.TextStyleOpts(font_size=13, color='orange'),
                
                ),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",#formatter='{c}'
            ),
            datazoom_opts=[
                opts.DataZoomOpts(range_start=0, range_end=100),
                opts.DataZoomOpts(type_="inside", range_start=0, range_end=100),
            ],        
            yaxis_opts=opts.AxisOpts(
                type_="value",
                min_ = 'dataMin',
                position="left",
                axistick_opts=opts.AxisTickOpts(is_show=True),
                splitline_opts=opts.SplitLineOpts(is_show=True),
            ),
        )
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis(
            series_name='atm',
            y_axis=atm_data,
            yaxis_index=0,
            linestyle_opts=opts.LineStyleOpts(curve=0, type_="solid", color='yellow', width=0.6),       
            is_symbol_show=False,
        )
        .add_yaxis(
            series_name="ulpx",
            y_axis=y_data,
            yaxis_index=0,
            linestyle_opts=opts.LineStyleOpts(curve=0, type_="solid", color='lightblue'),
            symbol="emptyCircle",
            is_symbol_show=False,
            is_smooth=False,
            label_opts=opts.LabelOpts(is_show=False,font_size = 8,),
            markpoint_opts=opts.MarkPointOpts(
                data=mark_points, 
                label_opts=opts.LabelOpts(position="top", distance=10, font_size = 12)
            ),
        )
        .add_yaxis(
            series_name='val',
            y_axis=val_data,
            yaxis_index=1,
            linestyle_opts=opts.LineStyleOpts(curve=0, type_="dotted", color='cyan', width=0.7),       
            is_symbol_show=False,
        )
        .extend_axis(
            yaxis=opts.AxisOpts(
            type_="value",
            name="ybaxis",
            min_='dataMin',
            position="right",
            axistick_opts=opts.AxisTickOpts(is_show=True),
            splitline_opts=opts.SplitLineOpts(is_show=True),    
            axisline_opts=opts.AxisLineOpts(
                linestyle_opts=opts.LineStyleOpts(color="#5793f3")
            ),            
        )
    )


    )
    return line
