# coding=utf-8
import requests
import re
import itertools
from wxpy import *
import datetime
import time
import numpy as np

# 通过和风接口获取天气预报,分为daily和hourly两种类型
def get_foreast(location, foreast_type):
    if foreast_type == 'hourly':
        response = requests.get('https://api.heweather.net/s6/weather/hourly?location='+location+'&key=0f0fc22e93634ba0b796c46fdb88f1a8')
        result = response.json()
        hourly_foreast_list = result['HeWeather6'][0]['hourly']
        return hourly_foreast_list
    elif foreast_type == 'daily':
        response = requests.get('https://api.heweather.net/s6/weather/forecast?location='+location+'&key=0f0fc22e93634ba0b796c46fdb88f1a8')
        result = response.json()
        daily_foreast = result['HeWeather6'][0]['daily_forecast']
        return daily_foreast

def get_rain_hour_count_dict(location_list):
    rain_hour_count_dict = {}
    for location in location_list:
        hourly_foreast_list = get_foreast(location, 'hourly')
    
        step = 17 #7点至23点共17小时
        rain_hours = get_rain_hours(hourly_foreast_list, step)
        rain_hour_count_dict[location] = len(rain_hours)
        
    return rain_hour_count_dict
    

# 根据hourly_foreast_list，获取接下来step个小时的下雨时间
def get_rain_hours(hourly_foreast_list, step):
    hours = [ re.split(r'[ :]', hourly_foreast_list[x]['time'])[1] for x in range(step)]
    hour_bool = [ int(hourly_foreast_list[x]['pop'])> pop_threshhold for x in range(step)]

    result_list = []
    for hour in itertools.compress(hours, hour_bool):
        result_list = tuple(itertools.compress(hours, hour_bool))
        
    return result_list

# 根据daily_notification_time 将今明两天的时间点区分开
def today_tomorrow_filter(result_list):
    return list(filter(lambda x:(int(x)>daily_notification_time), result_list)),list( filter(lambda x:(int(x)<=daily_notification_time), result_list))

def toStr(l):
    return f'{l[0]}-{l[-1]}'

# 将联系的时间点连接起来，比如15，16，17连接为15-17
def combine(a):
    a = list(map(int,a))
    times = np.split(a, np.where(np.diff(a) != 1)[0] + 1)
    result = []
    for time in times:
        if len(time) == 1:
            result.append(str(time[0]))
        elif len(time) >= 2:
            result.append(str(time[0])+'-'+str(time[-1]))
    return result

# 生成每日天气预报
def get_daily_msg(location):
    
    daily_foreast = get_foreast(location, 'daily')
    hourly_foreast_list = get_foreast(location,'hourly')
    
    today=datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    today_str = today.strftime('%Y-%m-%d')
    tomorrow_str = tomorrow.strftime('%Y-%m-%d')

    daily_msg ='【'+location+ '明日天气预报】\n'
    # 生成基本的天气预报，包括气温和下雨概率
    for record in daily_foreast:
        if tomorrow_str == record['date']:
            if record['cond_txt_d'] == record['cond_txt_n']:
                daily_msg += '明天' + record['cond_txt_n']
            else:   
                daily_msg += '明天'+ record['cond_txt_d'] + '转' + record['cond_txt_n']
            daily_msg += '\n最高气温为' + record['tmp_max'] + '℃，最低气温为' + record['tmp_min'] + '℃\n有' +\
                record['pop'] + '%的概率下雨'
    # 生成每日可能性比较大的下雨时间
    step = 24
    rain_hours = get_rain_hours(hourly_foreast_list, step)
    today_list, tomorrow_list = today_tomorrow_filter(rain_hours)
    today_list = combine(today_list)
    tomorrow_list = combine(tomorrow_list)
    
    if len(rain_hours) > 0:
        daily_msg += '\n降雨可能性较大的时间为'
        if len(today_list) > 0 and len(tomorrow_list) > 0:
            daily_msg += '今天'+ ','.join([x+'点' for x in today_list]) +'和明天'+ ','.join([x+'点' for x in tomorrow_list])
        elif len(today_list) > 0:
            daily_msg += '今天'+ ','.join([x+'点' for x in today_list])
        elif len(tomorrow_list) > 0:
            daily_msg += '明天'+ ','.join([x+'点' for x in tomorrow_list])

    return daily_msg

def get_daily_msg_dict(location_list):
    daily_msg_dict = {}
    for location in location_list:
        daily_msg_dict[location] = get_daily_msg(location)
    return daily_msg_dict
        

# 生成两小时天气预报
def get_hourly_msg(location):
    
    hourly_foreast_list = get_foreast(location, 'hourly')
    
    step = 2
    rain_hours = get_rain_hours(hourly_foreast_list, step) 
    
    if len(rain_hours) > 0:
        hourly_msg = location
        hourly_msg += '接下来两小时将有降雨，出门记得带伞\n'
        for i in range(2):
            hourly_msg += re.split(r'[ :]', hourly_foreast_list[i]['time'])[1] +'点的天气状况为'+ hourly_foreast_list[i]['cond_txt']+ ',下雨的概率为' +  hourly_foreast_list[i]['pop'] + '%\n'
        return hourly_msg
    else:
        return ''

def get_hourly_msg_dict(location_list):
    hourly_msg_dict = {}
    for location in location_list:
        hourly_msg_dict[location] = get_hourly_msg(location)
    return hourly_msg_dict
    
# 发送天气预报
def send_msg(msg, target):
    print('Start to search...')
    my_friend = bot.friends().search(target)[0]
    print('Ready to send...')
    print(my_friend)
    my_friend.send(msg)
    print('Sended')
    print(msg)
        

if __name__ == '__main__':

    targets = {'临海':['曹超芹小天使'],
          '南山':['甄淑怡','梁奕菡']}
    # 每日天气预报发送时间
    daily_notification_time = 21
    morning_notification_time = 7
    # 降雨提醒的阈值
    pop_threshhold = 60
    rain_hours_threshhold = 8
    
    location_list = list(targets.keys())
    
    # 启动微信机器人
    bot = Bot(console_qr=True)
#     bot = Bot()
    
    # 计算当前距离下一个整点的时间，睡眠至下个整点前一分钟
    localtime = time.localtime(time.time())
    offset = 59 - localtime.tm_min
    time.sleep(offset * 60)
    
    # 初始化
    hourly_msg_targets = []
    rain_hour_count_dict = get_rain_hour_count_dict(location_list)
    for location in targets:
        # 如果降雨没有超过阈值，开启两小时预报
        if rain_hour_count_dict[location] < rain_hours_threshhold:
            hourly_msg_targets.append(location)
    
    while(True):
        localtime = time.localtime(time.time())
        print(localtime)
        time.sleep(5)
        
        if(localtime.tm_min == 0):
            
            # 当时间介于7点至23点之间发送天气预报
            if(localtime.tm_hour >=7 and localtime.tm_hour <=23):
                
                # 每天早上7点统计当天需要发送两小时天气预报的城市，连续降雨超过8小时的城市关闭两小时天气预报
                if(localtime.tm_hour == morning_notification_time and localtime.tm_min == 0):
                    hourly_msg_targets = []
                    rain_hour_count_dict = get_rain_hour_count_dict(location_list)
                    print(rain_hour_count_dict)
                    for location in targets:
                        # 如果降雨没有超过阈值，开启两小时预报
                        if rain_hour_count_dict[location] < rain_hours_threshhold:
                            hourly_msg_targets.append(location)
                        # 如果降雨超过阈值，关闭两小时预报
                        elif rain_hour_count_dict[location] >= rain_hours_threshhold:
                            target_names = targets[location]
                            for target in target_names:
                                morning_msg = location +'今日将连续降雨超过8小时，已关闭今日两小时降雨预报，出门记得带伞'
#                                 print(morning_msg, target)
                                send_msg(morning_msg, target)
                        
                # 发送两小时天气预报
                hourly_msg_dict = get_hourly_msg_dict(location_list)
                for location in hourly_msg_targets:
                    hourly_msg = hourly_msg_dict[location]
                    if hourly_msg != '':
                        target_names = targets[location]
                        for target in target_names:
                            send_msg(hourly_msg, target)
#                             print(hourly_msg, target)
            
                # 每晚21点发送第二天天气预报
                if (localtime.tm_hour == daily_notification_time and localtime.tm_min == 0):
                    daily_msg_dict = get_daily_msg_dict(location_list)
                    for location in targets:
                        daily_msg = daily_msg_dict[location]
                        target_names = targets[location]
                        for target in target_names: 
                            send_msg(daily_msg, target)
#                             print(daily_msg, target)
                    
            # 消息发送后，睡眠59分钟
            time.sleep(59 * 60)
