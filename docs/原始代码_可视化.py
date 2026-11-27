#数据可视化
Data_visual(Year, Quarterly2, Quarterly3)
#数据可视化
																
																
																import webbrowser as web
																# 数据可视化
def Data_visual(Year2, Quarterly1, Quarterly2):
    import os
    # 比较季度之间的各个基金持仓股票总市值的柱状图
    Compare_Quarterlys_market_value_Stock_name = pd.read_csv('基金数据分析/处理数据/' + '连续二季度各个基金持仓股票持股总市值' + Position_Area + '-' + Quarterly1 + '与' + Quarterly2 + '.csv')
    Compare_Quarterlys_market_value_Stock_name_bar = Bar()
    Compare_Quarterlys_market_value_Stock_name_bar.add_xaxis(Compare_Quarterlys_market_value_Stock_name['股票名称'].tolist())
    Compare_Quarterlys_market_value_Stock_name_bar.add_yaxis(Quarterly1 + '各个基金持仓股票持股总市值',Compare_Quarterlys_market_value_Stock_name[Quarterly1 + '各个基金持仓股票持股总市值'].tolist())
    Compare_Quarterlys_market_value_Stock_name_bar.add_yaxis(Quarterly2 + '各个基金持仓股票持股总市值',Compare_Quarterlys_market_value_Stock_name[Quarterly2 + '各个基金持仓股票持股总市值'].tolist())
    Compare_Quarterlys_market_value_Stock_name_bar.set_global_opts(title_opts=opts.TitleOpts(title="比较季度之间各个基金持仓股票持股总市值"))
    Compare_Quarterlys_market_value_Stock_name_bar.render('基金数据分析/可视化结果/' + Quarterly1 + '与' + Quarterly2 + '比较季度之间各个基金持仓股票持股总市值统计.html')
    web.open_new_tab('基金数据分析\可视化结果\\' + Quarterly1 + '与' + Quarterly2 + '比较季度之间各个基金持仓股票持股总市值统计.html')
    # 比较季度之间的各个基金持仓股票总市值的柱状图

    # 比较季度之间重仓股票持有基金数量的柱状图
    Compare_Quarterlys_Position_number = pd.read_csv(
        '基金数据分析/处理数据/' + '连续二季度股票持有的基金持有家数' + Position_Area + '-' + Quarterly1 + '与' + Quarterly2 + '.csv')
    Compare_Quarterlys_Position_number_bar = Bar()
    Compare_Quarterlys_Position_number_bar.add_xaxis(Compare_Quarterlys_Position_number['股票名称'].tolist())
    Compare_Quarterlys_Position_number_bar.add_yaxis(Quarterly1 + '基金持有家数', Compare_Quarterlys_Position_number[Quarterly1 + '基金持有家数'].tolist())
    Compare_Quarterlys_Position_number_bar.add_yaxis(Quarterly2 + '基金持有家数', Compare_Quarterlys_Position_number[Quarterly2 + '基金持有家数'].tolist())
    Compare_Quarterlys_Position_number_bar.set_global_opts(title_opts=opts.TitleOpts(title="比较季度之间重仓股票持有基金数量"))
    Compare_Quarterlys_Position_number_bar.render('基金数据分析/可视化结果/' + Quarterly1 + '与' + Quarterly2 + '重仓前10股票基金持有家数统计.html')
    web.open_new_tab('基金数据分析\可视化结果\\' + Quarterly1 + '与' + Quarterly2 + '重仓前10股票基金持有家数统计.html')
    # 比较季度之间重仓股票持有基金数量的柱状图

    # 比较季度之间收益率的柱状图
    Compare_Quarterlys_Rate_return = pd.read_csv('基金数据分析/处理数据/' + '连续二季度基金收益率前200' + Position_Area + '-' + Quarterly1 + '与' + Quarterly2 + '.csv')
    Compare_Quarterlys_Rate_return.head(10)
    Compare_Quarterlys_Rate_return_bar = Bar()
    Compare_Quarterlys_Rate_return_bar.add_xaxis(Compare_Quarterlys_Rate_return['基金名称'].tolist())
    Compare_Quarterlys_Rate_return_bar.add_yaxis(Quarterly1 + '收益率',Compare_Quarterlys_Rate_return[Quarterly1 + '收益率'].tolist())
    Compare_Quarterlys_Rate_return_bar.add_yaxis(Quarterly2 + '收益率',Compare_Quarterlys_Rate_return[Quarterly2 + '收益率'].tolist())
    Compare_Quarterlys_Rate_return_bar.set_global_opts(title_opts=opts.TitleOpts(title="比较季度之间收益率"))
    Compare_Quarterlys_Rate_return_bar.render('基金数据分析/可视化结果/' + Quarterly1 + '与' + Quarterly2 + '收益率统计.html')
    web.open_new_tab('基金数据分析\可视化结果\\' + Quarterly1 + '与' + Quarterly2 + '收益率统计.html')
    # 比较季度之间收益率的柱状图
# 数据可视化
