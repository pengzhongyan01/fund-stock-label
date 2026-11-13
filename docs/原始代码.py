# 融合基金持仓和股票的市值，并进行标签化，为下一步的训练提供数据
    merge_position_and_market(position_area, current_quarter, previous_quarter)
# 融合基金持仓和股票的市值，并进行标签化，为下一步的训练提供数据
#融合基金持仓和股票的市值，并进行标签化，为下一步的训练提供数据
#添加标签
def get_stock_label():
    import akshare as ak
    #爬取股票的历史数据
    stock_data=pd.read_csv('基金数据分析/处理数据/'+'股票对应的基金持有家数和总市值.csv')
    stock_data[current_quarter+'股票流通市值']='0'
    stock_data[previous_quarter + '股票流通市值'] = '0'
    stock_data['标签']='3'
    stock_data = stock_data.dropna(axis=0)
    #取出股票代码
    top_position_current_quarter = pd.read_csv(
        '基金数据分析/数据清洗后/' + previous_year + '年' + fund_type + '型基金近一年高收益率基金的' + '前十大持仓-' + current_quarter + '.csv')
    top_position_previous_quarter = pd.read_csv(
        '基金数据分析/数据清洗后/' + current_year + '年' + fund_type + '型基金近一年高收益率基金的' + '前十大持仓-' + previous_quarter + '.csv')
    for i in range(len(stock_data)):
        flag=False
        stock_code=[]
        for j in range(len(top_position_current_quarter)):
            if stock_data.iloc[i,0]==top_position_current_quarter.iloc[j,4]:
                stock_code=top_position_current_quarter.loc[j,'持仓股票代码'][1:]
                if stock_code[0:1]=='6':
                    stock_code='sh'+str(stock_code)
                    flag = True
                if stock_code[0:2]=='00':
                    stock_code = 'sz' + str(stock_code)
                    flag=True
                break
            if stock_data.iloc[i,0]==top_position_previous_quarter.iloc[j,4]:
                stock_code=top_position_previous_quarter.loc[j,'持仓股票代码'][1:]
                if stock_code[0:1]=='6':
                    stock_code='sh'+str(stock_code)
                    flag = True
                if stock_code[0:2]=='00':
                    stock_code = 'sz' + str(stock_code)
                    flag = True
                #flag=True
                break
        if (flag==True) and (str(stock_code[2:3]=='6') or str(stock_code[2:4]=='00') or len(stock_code)==8):
            try:
                history_data=ak.stock_zh_a_daily(symbol=str(stock_code),start_date='20260305',end_date='20260519',adjust='qfq')
            except:
                print('网络原因'+str(stock_code)+'股票的价格数据未爬取！')
            #print(history_data)
            if len(history_data)>141:
                price1=stock_data.iloc[0,4]#
                outstanding_share1=history_data.iloc[0,6]
                stock_data.loc[i,current_quarter+'股票流通市值']=price1*outstanding_share1
                price2 = stock_data.iloc[58, 4]
                outstanding_share2 = history_data.iloc[0, 6]
                stock_data.loc[i, previous_quarter+'股票流通市值'] = price2 * outstanding_share2
                begin_price=history_data.iloc[118,4]#任意20交易日的开始价格
                end_price=history_data.iloc[141,4]#任意20交易日的结束价格
                if float(end_price) >= 1.2 * float(begin_price):
                    stock_data.iloc[i, 7] = 1  # 优
                if ((float(end_price) >= (1.1 * float(begin_price))) and (
                        float(end_price) < (1.2 * float(begin_price)))):
                    stock_data.iloc[i, 7] = 2  # 良
                if ((float(end_price) >= (0.85 * float(begin_price))) and (
                        float(end_price) < (1.1 * float(begin_price)))):
                    stock_data.iloc[i, 7] = 3  # 中
                if float(end_price) < (0.85 * float(begin_price)):
                    stock_data.iloc[i, 7] = 4  # 差
    stock_data.to_csv('基金数据分析/处理数据/' + '股票对应的基金持有家数和总市值和股票市值及标签.csv',
                          encoding='utf-8-sig', index=False)
    print("标注完毕！")
    # 取出股票代码
# 添加标签
def merge_position_and_market(position_area,current_quarter,previous_quarter):
    compare_quarterlys_market_value_stock_name = pd.read_csv(
        '基金数据分析/处理数据/' + '连续二季度各个基金持仓股票持股总市值' + position_area + '-' + current_quarter + '与' + previous_quarter+ '.csv')
    compare_quarterlys_position_number = pd.read_csv(
        '基金数据分析/处理数据/' + '连续二季度股票持有的基金持有家数' + position_area + '-' + current_quarter + '与' + previous_quarter+'.csv')
    merge_position_and_market_value=[]
    for i in range(len(compare_quarterlys_position_number)):
        for j in range(len(compare_quarterlys_market_value_stock_name)):
            if compare_quarterlys_position_number.iloc[i,0]==compare_quarterlys_market_value_stock_name.iloc[j,0]:#股票名称相同
                temp = {'股票名称': compare_quarterlys_position_number.iloc[i, 0],
                        current_quarter + '基金持有家数': compare_quarterlys_position_number.iloc[i, 1],
                        previous_quarter + '基金持有家数': compare_quarterlys_position_number.iloc[i, 2],
                        current_quarter + '各个基金持仓股票持股总市值': compare_quarterlys_market_value_stock_name.iloc[j, 1],
                        previous_quarter + '各个基金持仓股票持股总市值': compare_quarterlys_market_value_stock_name.iloc[j, 2],
                        }
                merge_position_and_market_value.append(temp)
                break
    #持有股票的基金数量及对应的市值
    header = ['股票名称', current_quarter + '基金持有家数',
              previous_quarter + '基金持有家数', current_quarter + '各个基金持仓股票持股总市值',
              previous_quarter + '各个基金持仓股票持股总市值']  # 数据列名
    with open('基金数据分析/处理数据/' + '股票对应的基金持有家数和总市值.csv', 'w', newline='',
              encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=header)  # 提前预览列名，当下面代码写入数据时，会将其一一对应。
        writer.writeheader()  # 写入列名
        writer.writerows(merge_position_and_market_value)
    f.close()
    # 持有股票的基金数量及对应的市值
    #添加标签
    get_stock_label()
    # 添加标签
#融合基金持仓和股票的市值，并进行标签化，为下一步的训练提供数据
