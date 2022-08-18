import configparser
import json
import math
import random

from geopy.geocoders import Nominatim
import folium

from telethon.sync import TelegramClient
from telethon import connection

# для корректного переноса времени сообщений в json
from datetime import date, datetime

# класс для работы с сообщениями
from telethon.tl.functions.messages import GetHistoryRequest

# Считываем учетные данные
config = configparser.ConfigParser()
config.read("config.ini")

# Присваиваем значения внутренним переменным
api_id = int(config['Telegram']['api_id'])
api_hash = config['Telegram']['api_hash']
username = config['Telegram']['username']

client = TelegramClient(username, api_id, api_hash)
client.start()
locator = Nominatim(user_agent="myapp")


async def dump_all_messages(channel):
    """Записывает json-файл с информацией о всех сообщениях канала/чата"""
    offset_msg = 0  # номер записи, с которой начинается считывание
    limit_msg = 100  # максимальное число записей, передаваемых за один раз

    all_messages = []  # список всех сообщений
    total_messages = 0
    total_count_limit = 0  # поменяйте это значение, если вам нужны не все сообщения
    info = []

    class DateTimeEncoder(json.JSONEncoder):
        '''Класс для сериализации записи дат в JSON'''

        def default(self, o):
            if isinstance(o, datetime):
                return o.isoformat()
            if isinstance(o, bytes):
                return list(o)
            return json.JSONEncoder.default(self, o)

    while True:
        history = await client(GetHistoryRequest(
            peer=channel,
            offset_id=offset_msg,
            offset_date=None, add_offset=0,
            limit=limit_msg, max_id=0, min_id=0,
            hash=0))
        if not history.messages:
            break
        messages = history.messages
        for message in messages:
            if message.message is not None and message.message != "":
                info.append((message.message, message.id))
            all_messages.append(message.to_dict())
        offset_msg = messages[len(messages) - 1].id
        total_messages = len(all_messages)
        if total_count_limit != 0 and total_messages >= total_count_limit:
            break

    with open('channel_messages.json', 'w', encoding='utf8') as outfile:
        json.dump(all_messages, outfile, ensure_ascii=False, cls=DateTimeEncoder)
    return info


loc_l = [59.9386, 30.3141]


def find_coordinates_by_name(name, start, end, nearest=None, new_name=None):
    try:
        location = locator.geocode("Санкт-Петербург " + name[start:end])
        if math.fabs(location.latitude - loc_l[0]) < 0.5 and math.fabs(location.longitude - loc_l[1]) < 0.5:
            if nearest is None:
                return [location.latitude, location.longitude]
            else:
                if math.fabs(nearest[0] - loc_l[0]) + math.fabs(nearest[1] - loc_l[1]) > math.fabs(
                        location.latitude - loc_l[0]) + math.fabs(location.longitude - loc_l[1]):
                    return [location.latitude, location.longitude]
                else:
                    return nearest
        if nearest is None:
            nearest = [location.latitude, location.longitude]
        else:
            if math.fabs(nearest[0] - loc_l[0]) + math.fabs(nearest[1] - loc_l[1]) > math.fabs(location.latitude - loc_l[0]) + math.fabs(location.longitude - loc_l[1]):
                nearest = [location.latitude, location.longitude]
        raise Exception
    except Exception:
        if new_name[-1] == '.' or new_name[-1] == ',':
            return find_coordinates_by_name(name[:-1], start, end - 1, nearest, new_name[0:len(new_name) - 1])
        strings = new_name.split()
        if len(strings) > 1:
            return find_coordinates_by_name(name, start, end - len(strings[-1]) - 1, nearest, ' '.join(strings[0:len(strings) - 1]))
        else:
            if strings[0] != name[-len(strings[0]):]:
                return find_coordinates_by_name(name, start + len(strings[0]) + 1, len(name), nearest, name[start + len(strings[0]) + 1:])
            else:
                return nearest


colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen',
         'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']


async def main():
    # url = input("Введите ссылку на канал или чат: ")
    url = 'https://t.me/kudapiter24'
    channel = await client.get_entity(url)
    info = await dump_all_messages(channel)
    our_map = folium.Map(location=loc_l, zoom_start=11)
    memory = []
    for i, id in info:
        if ("Где" in i or "Адрес" in i) and "Когда" not in i:
            name_for_coordinates = None
            where = i.find("Адрес")
            if where == -1:
                where = i.find("Где")
                end = i.find("\n", where)
                if end != -1:
                    name_for_coordinates = i[where + 5:end]
                else:
                    name_for_coordinates = i[where + 5:]
            else:
                end = i.find("\n", where)
                if end != -1:
                    name_for_coordinates = i[where + 7:end]
                else:
                    name_for_coordinates = i[where + 7:]
            main_name = i[:i.find("\n")]
            name_for_coordinates = ' '.join(name_for_coordinates.replace(',', ' ').split())
            if name_for_coordinates[-1] == '.':
                name_for_coordinates = name_for_coordinates[:-1]
            coords = find_coordinates_by_name(name_for_coordinates, 0, len(name_for_coordinates), new_name=name_for_coordinates)
            if coords is None:
                coords = loc_l
            while [round(coords[0], 4), round(coords[1], 4)] in memory:
                if random.randint(0, 1) == 1:
                    if random.randint(0, 1) == 1:
                        coords[0] += 0.0001
                    else:
                        coords[0] -= 0.0001
                else:
                    if random.randint(0, 1) == 1:
                        coords[1] += 0.0001
                    else:
                        coords[1] -= 0.0001
            memory.append([round(coords[0], 4), round(coords[1], 4)])
            folium.Marker(location=[coords[0], coords[1]], popup=f"{i} <a href={url}/{id} target=\"_blank\">ССЫЛКА</a>",
                          tooltip=f"{main_name}<br>{name_for_coordinates}",
                          icon=folium.Icon(color=colors[id % len(colors)], icon_color=colors[(id + int(len(colors) / 2)) % len(colors)])
                          ).add_to(our_map)
    our_map.save('map.html')


with client:
    client.loop.run_until_complete(main())