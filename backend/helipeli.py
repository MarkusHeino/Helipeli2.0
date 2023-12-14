import config
import mysql.connector
from high_scores import handle_high_score_update, return_highscores
from geopy import distance
import random

# helipeli 2.0 importit
from flask import Flask, Response
import json

from flask_cors import CORS
from games import dice_game2
from games import coinflip2

#jos halutaan käyttää region_codea pelissä country_code:n sijasta, asetetaan tämä päälle//ei toimi tällä hetkellä tässä projektissa
region_ON = False #ei kuulu tällä hetkellä helipeliin 2.0, voidaan käyttää valitsemaan region:in perusteella kentät
#jos halutaan kääntää kartta, kun kenttien pituuskoordinaattipisteet ovat erimerkkisia(-,+) ja molempien on itseisarvo yli 90 astetta
invert_map = True #ei helipeliin 2.0
country_code = 'GB' # ISO-maakoodi, jota voidaan käyttää eri maiden valitsemiseen, toimii helipeli 2.0. Oletusarvoiksi sopivia: GB80,'ES, 250 # 'DE', 75km
region_code = "US-AL" # 'us-al'-50km-62kpl 'US-VA'-75KM-71kpl, US-NJ 100, 20 region "us-sc-100/150-29 150, region 'US-WI'-80-47
MAX_RANGE = 60 #pelaajan max. etäisyys kentistä

map_width = 58
map_height = 17
margin_lon = 0.1#2
margin_lat = 0.1#2
# 1. Lataa lisäosat geopy sekä sql-connector-python, Flask, Flask-CORS
# valikon kautta View->Tool Windows->Python Packages
# 2. Aseta config.py-tiedostoon tietokannan käyttäjänimi(user) ja salasana(pwd)
# 3. Käytä tietokantana lp_copy_demogame.sql-tiedostoa, jonka nimi on game2

yhteys = mysql.connector.connect(
         host='127.0.0.1',
         port= 3306,
         database='game2',
         user=config.user,
         password=config.pwd,
         autocommit=True
        )

#asettaa pelaajan aloituspaikan tietokantaan sekä päivittää tiedot vierailtujen kenttien joukkoon
def start_new_game(connected_heliports, ICAO, player='Pelaaja', fly_range=MAX_RANGE, iso_country = country_code, iso_region =region_code, gas= 400):
    sql = "insert into game "
    sql += f" (location, screen_name, fly_range, country_code, region_code, gas_left, gas_consumed) "
    sql += f" VALUES('{ICAO}', '{player}', '{fly_range}', '{iso_country}', '{iso_region}',  '{gas}', '{0}');"
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(sql)
    g_id = kursori.lastrowid

    sql = f"insert into heliports_visited (game_id, location) "
    sql += f" values('{g_id}','{ICAO}')"
    kursori = yhteys.cursor()
    kursori.execute(sql)

    goals = get_goals()
    goal_list = []
    for goal in goals:
        for i in range(0, goal['probability'], 1):
            goal_list.append(goal['id'])

    # exclude starting airport
    goal_ports = connected_heliports[1:].copy()
    random.shuffle(goal_ports)

    for i, goal_id in enumerate(goal_list):
        sql = "INSERT INTO goal_ports (game, location, goal) VALUES (%s, %s, %s);"
        cursor = yhteys.cursor(dictionary=True)
        cursor.execute(sql, (g_id, goal_ports[i]['ident'], goal_id))

    return g_id

#hakee iso_country-koodilla valitun valtion helikopterikenttien tiedot tietokannasta
def get_heliports_by_region(iso_region=region_code, type ='heliport'):
    sql = (f'select ident, longitude_deg, latitude_deg, name from airport ')
    sql +=   (f' where iso_region = "{iso_region}" and airport.type = "{type}"') ##iso_country
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(sql)
    heliports_info = kursori.fetchall()
    for info in heliports_info:
        info['connected'] = False
    return heliports_info

#hakee iso_country-koodilla valitun valtion helikopterikenttien tiedot tietokannasta
def get_heliports_by_country(iso_country=country_code, type = 'heliport'):
    sql = (f'select ident, longitude_deg, latitude_deg, name from airport ')
    sql +=   (f' where iso_country = "{iso_country}" and airport.type = "{type}"')
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(sql)
    heliports_info = kursori.fetchall()
    for info in heliports_info:
        info['connected'] = False
    return heliports_info



#   palauttaa kenttien tiedot jotka ovat yhteyksissä max_range-etäisyyden mukaan
def get_connected_heliports(heliports_info):
    connected_heliports = []
    #haetaan korkeimmat ja alimmat koordinaattipisteet
    lon_lat = get_minmax_lon_lat(heliports_info)
    #haetaan itseisarvoltaan suurempi koordinaattipiste
    minmaxlonlat = get_abs_minmaxlonlat(lon_lat)
    max_lat = minmaxlonlat['max_lat']
    max_lon = minmaxlonlat['max_lon']


    # lasketaan napaa lähimmän pisteen avulla suurin koordinaattiarvo, joka
    # kenttien/pisteiden välillä voi olla minimi- ja maksimietäisyydellä
    # Käytetään esiseulontaan/suorituksen optimointiin
    MAX_LON_DIFF = abs(MAX_RANGE/distance.distance((max_lat, 0),(max_lat, 1)).km)

    MAX_LAT_DIFF = abs(MAX_RANGE/distance.distance((0, max_lon),(1, max_lon)).km)
    # lisää ensimmäisen kentän listaan, pelaajan aloituspaikka. Alempana tarkistetaan mitkä kentät ovat
    # saavutettavissa kun aloitetaan tältä kentältä
    heliports_info[0]['connected'] = True
    connected_heliports.append(heliports_info[0])
    print("Amount of heliports: ", len(heliports_info))
    for heliport in heliports_info:
        for heliport_to_compare in heliports_info:
            #lasketaan leveys-ja pituuspisteiden väliset etäisyydet koordinaatteina, esiseulonta
            lat_dist = abs(heliport['latitude_deg'] - heliport_to_compare['latitude_deg'])
            lon_dist = abs(heliport['longitude_deg'] - heliport_to_compare['longitude_deg'])
            # jos pituuskoordinaattipisteiden etäisyys on yli puolet pallosta, niin pisteiden etäisyys toisistaan
            # on laskettava eri pituuspuolelta mitattuna. Toinen koordinaateista on tällöin ollut
            # negatiivinen ja toinen positiivinen sekä molemmat ovat itseisarvoltaan yli 90 astetta
            if lon_dist > 180:
                lon_dist = 360-lon_dist
            # esiseulotaan kenttiä koordinaattien perusteella, koska jos pisteet ovat kaukana toisistaan
            # niin on turha laskea tarkempaa etäisyyttä. Loopin suoritusaika ilman tätä huomattavasti on pidempi
            if lat_dist < MAX_LAT_DIFF and lon_dist < MAX_LON_DIFF:
                    distance_between = (distance.distance((heliport['latitude_deg'], heliport['longitude_deg']), (heliport_to_compare['latitude_deg'],heliport_to_compare['longitude_deg'])).km)#.__str__()[0:5])
                    #jos kenttien välinen etäisyysy sallitun rajoissa
                    if distance_between < MAX_RANGE:
                    #suoritaan vain, jos jompikumpi on jo listassa. Ohita, jos molemmat ovat jo listassa
                        if heliport_to_compare['connected'] and not(heliport['connected']):
                            heliport['connected'] = True
                            connected_heliports.append(heliport)
                        elif heliport['connected'] and not (heliport_to_compare['connected']):
                            heliport_to_compare['connected'] = True
                            connected_heliports.append(heliport_to_compare)
    for info in connected_heliports:
        info['connected'] = False
    print("Amount of connected heliports", len(connected_heliports))

    return connected_heliports

def get_abs_minmaxlonlat(lon_lat):
    max_lat = 0
    #tarkastetaan kumpi leveyspiirikoordinaateista on itsearvoltaan suurempi
    if abs(lon_lat['min_lat']) < abs(lon_lat['max_lat']):
        max_lat = abs(lon_lat['max_lat'])
    elif abs(lon_lat['min_lat']) > abs(lon_lat['max_lat']):
        max_lat = abs(lon_lat['min_lat'])
    max_lon = 0
    #tarkastetaan kumpi pituuspiirikoordinaateista on itsearvoltaan suurempi
    if abs(lon_lat['min_lon']) < abs(lon_lat['max_lon']):
        max_lon = abs(lon_lat['max_lon'])
    elif abs(lon_lat['min_lon']) > abs(lon_lat['max_lon']):
        max_lon = abs(lon_lat['min_lon'])
    abs_minmaxlonlat= {'max_lat': max_lat, 'max_lon': max_lon}
    return abs_minmaxlonlat

def get_player_coordinates(g_id):
    sql = f"select latitude_deg, longitude_deg from airport where ident in (select location from game where id = '{g_id}');"
    kursori = yhteys.cursor()
    kursori.execute(sql)
    tulos = kursori.fetchone()
    return tulos


def heliports_visited(g_id):
    sql = "select location from heliports_visited "
    sql += f"where game_id = '{g_id}' "
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(sql)
    tulos = kursori.fetchall()
    return tulos


#palauttaa pelaajaa lähimmät kentät listana, lisää heliports_info:on etäisyyden pelaajasta
# 'distance_from_player'-muuttujan sisälle sekä järjestää ne lähimmästä kauimpaan
# sekä
def get_heliports_in_range(map_info, g_id):
    player_coordinate = get_player_coordinates(g_id)
    heliports_in_range = []
    for info in map_info:
        if player_coordinate != (info['latitude_deg'],info['longitude_deg']):
            distance_between = distance.distance((info['latitude_deg'],info['longitude_deg']), player_coordinate).km
            info['distance_from_player'] = distance_between
            if distance_between <= get_max_range(g_id):# and distance_between !=0:
                heliports_in_range.append(info)
    heliports_in_range = sort_heliports_by_distance(heliports_in_range)
    return heliports_in_range

# palauttaa kentät järjestettynä lähimmästä kauimpaan pelaajasta nähden.
# Lisää järjestysluvun('range_index') palautettavaan listaan,joka näytetään kartalla, jotta pelaaja
# voi valita mihin liikkuu
def sort_heliports_by_distance(heliports_info):
    sorted_heliports_info = heliports_info
    for h in range(len(sorted_heliports_info)):
        min_idx = h
        for p in range(h + 1, len(heliports_info)):
            if sorted_heliports_info[p]['distance_from_player'] < sorted_heliports_info[min_idx]['distance_from_player']:
                min_idx = p
        sorted_heliports_info[h], sorted_heliports_info[min_idx] = sorted_heliports_info[min_idx], sorted_heliports_info[h]
    map_index = 0
    alphabet = '0ABCDEFGHIJKLMNOPQRSTUXYZ'
    for info in sorted_heliports_info:
        info['range_index'] = map_index
        map_index += 1
    return sorted_heliports_info


def get_gas_left(g_id):
    sql = f"select gas_left from game where id = '{g_id}' "
    kursori = yhteys.cursor()
    kursori.execute(sql)
    tulos = kursori.fetchone()
    return tulos[0]

def get_max_range(g_id):
    sql = f"select fly_range from game where id = '{g_id}' "
    kursori = yhteys.cursor()
    kursori.execute(sql)
    tulos = kursori.fetchone()
    return tulos[0]


def update_max_range(g_id):
    gas_left = get_gas_left(g_id)
    current_max_range = get_max_range(g_id)
    if gas_left < current_max_range:
        sql = "update game "
        sql += f"set fly_range = gas_left "
        sql += f"where id = '{g_id}' "
        kursori = yhteys.cursor()
        kursori.execute(sql)

    elif gas_left > MAX_RANGE and current_max_range < MAX_RANGE:
        sql = "update game "
        sql += f"set fly_range = '{MAX_RANGE}' "
        sql += f"where id = '{g_id}' "
        kursori = yhteys.cursor()
        kursori.execute(sql)


#päivittää tietokantaan pelaajan sijainnin sekä muut tarvittavat arvot
def update_player_move(distance_moved, g_id, ICAO):
    sql = "update game "
    sql += f"set gas_consumed = (gas_consumed)+'{distance_moved}' "
    sql += f",gas_left = gas_left-'{distance_moved}' "
    sql += f", location = '{ICAO}' "
    sql += f", turns = (turns) + '{1}' "
    sql += f" where id = '{g_id}' ;"
    kursori = yhteys.cursor()
    kursori.execute(sql)

    update_max_range(g_id)
    update_visited(g_id, ICAO)

def update_visited(g_id, ICAO):
    kursori = yhteys.cursor()
    sql = "select game_id, location from heliports_visited"
    kursori.execute(sql)
    tulos = kursori.fetchall()
    #tarkastaa ettei jo vierailtua kenttää lisätä listaan toiseen kertaan, tuple, g_id tulee js:stä string-muodossa, joten muuta int
    if (int(g_id), ICAO) not in tulos:
        sql = f"insert into heliports_visited(game_id, location) "
        sql += f" values('{g_id}','{ICAO}')"
        kursori.execute(sql)

#FRONT
#käytetään arvon tarkistamaan että pelaaja antaa käyttökelpoisen syötteen, kesken
def ask_location_num(number_of_heliports):
    in_list = False
    while not in_list:
        chosen_heliport_letter = (input("Give heliport number you want to travel to: "))
        for i, heliport in enumerate(number_of_heliports):
            if chosen_heliport_letter == heliport['range_index']:
                in_list = True
                chosen_heliport_num = i
                break
    return chosen_heliport_num


def get_disconnected_heliports(connected_heliports):
    #connected_heliports = get_connected_heliports(heliports_info)
    disconnected_heliports = []
    for heliport in heliports_info:
        if (heliport not in connected_heliports):
            disconnected_heliports.append(heliport)
    return disconnected_heliports


def get_minmax_lon_lat(connected_heliports):

    min_lat_index = 0
    for h in range(0,len(connected_heliports)):
        if connected_heliports[min_lat_index]['latitude_deg'] > connected_heliports[h]['latitude_deg']:
            min_lat_index = h

    max_lat_index = 0
    for h in range(0, len(connected_heliports)):
        if connected_heliports[max_lat_index]['latitude_deg'] < connected_heliports[h]['latitude_deg']:
            max_lat_index = h

    min_lon_index = 0
    for h in range(0,len(connected_heliports)):
        if connected_heliports[min_lon_index]['longitude_deg'] > connected_heliports[h]['longitude_deg']:
            min_lon_index = h

    max_lon_index = 0
    for h in range(0, len(connected_heliports)):
        if connected_heliports[max_lon_index]['longitude_deg'] < connected_heliports[h]['longitude_deg']:
            max_lon_index = h

    lon_lat = {'min_lon':connected_heliports[min_lon_index]['longitude_deg'], \
    'max_lon': connected_heliports[max_lon_index]['longitude_deg'],\
    'min_lat': connected_heliports[min_lat_index]['latitude_deg'],\
    'max_lat': connected_heliports[max_lat_index]['latitude_deg']}
    return lon_lat

def get_game_ids(iso_code):
    if region_ON:
        sql = f"select id, screen_name from game where region_code = '{iso_code}';"
    elif not region_ON:
        sql = f"select id, screen_name from game where country_code = '{iso_code}';"
    kursori = yhteys.cursor(dictionary =True)
    kursori.execute(sql)
    tulos = kursori.fetchall()
    return tulos

# get all goals
def get_goals():
    sql = "SELECT * FROM goal;"
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(sql)
    result = kursori.fetchall()
    return result

def update_player_gas(g_id, gas_gained):
    sql = "update game "
    sql += f" set gas_left = gas_left+'{gas_gained}' "
    sql += f" where id = '{g_id}'"
    kursori = yhteys.cursor()
    kursori.execute(sql)
    update_max_range(g_id)

def check_goal(g_id, cur_airport):
    sql = f'''SELECT goal_ports.id, goal, goal.id as goal_id, name, target_value, opened 
    FROM goal_ports 
    JOIN goal ON goal.id = goal_ports.goal 
    WHERE game = %s 
    AND location = %s'''
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(sql, (g_id, cur_airport))
    result = kursori.fetchone()
    if result is None:
        return False
    elif result['opened'] == 1:
        return False
    else:
        result['opened'] == 1
        set_goal_opened(result['id'])
        update_player_gas(g_id, result['target_value'])
    return result

def set_goal_opened(id):
    sql = "update goal_ports "
    sql += "set opened = '1' "
    sql += f"where id = '{id}' "
    kursori = yhteys.cursor()
    kursori.execute(sql)

def is_int(x):
    try:
        int(x)
        return True
    except:
        return False


def get_name_and_score(g_id):
    sql = f"SELECT screen_name, gas_left, gas_consumed FROM game where id = '{g_id}' "
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(sql)
    tulos = kursori.fetchone()
    result = {'screen_name': tulos['screen_name'], 'score': tulos['gas_left']-int(tulos['gas_consumed']/5) }
    return result

def get_gas_consumed(g_id):
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(f"SELECT gas_consumed FROM game where '{g_id}' ")
    tulos = kursori.fetchone()
    return tulos

def get_stats(g_id):
        sql = f"SELECT screen_name, gas_left, gas_consumed, turns, location, fly_range FROM game where id = '{g_id}' "
        kursori = yhteys.cursor(dictionary=True)
        kursori.execute(sql)
        tulos = kursori.fetchone()
        tulos['score'] = get_name_and_score(g_id)['score']
        return tulos

print("Fetching heliports")
if region_ON:
    heliports_info = get_heliports_by_region(region_code)
else:
    heliports_info = get_heliports_by_country(country_code)

print("Checking connected heliports")

connected_heliports = get_connected_heliports(heliports_info)

if region_ON:
    pass
    #game_id = get_game_id(connected_heliports, region_code)
else:
    pass
    #game_id = get_game_id(connected_heliports, country_code)



app = Flask(__name__)
#tarvitaan jotta toimisi
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


@app.route("/update_highscores/<g_id>")
def update_highscores(g_id):
    handle_high_score_update(get_name_and_score(g_id))
    high_scores = json.dumps(return_highscores())
    return Response(response=high_scores, status=200, mimetype="/application/json")

@app.route("/get_highscores/")
def get_highscores():
    high_scores = json.dumps(return_highscores())
    return Response(response=high_scores, status=200, mimetype="/application/json")

@app.route("/get_games")
def get_games():
    ids = get_game_ids(country_code)
    ids_json = json.dumps(ids)
    return Response(response=ids_json, status=200, mimetype="/application/json")



@app.route("/startGame/<game_id>/<screen_name>")
def startGame(game_id, screen_name="NONAME"):
    if int(game_id) == 0:
        start_location = connected_heliports[0]
        g_id = start_new_game(connected_heliports, start_location['ident'], screen_name)
    else:
        g_id = game_id
    stats = get_stats(g_id)
    heliports_in_range = get_heliports_in_range(connected_heliports, g_id)
    visited_heliports = heliports_visited(g_id)

    info = {
        'g_id': g_id,
        'goal': False,
        'stats': stats,
        'heliports_in_range': heliports_in_range,
        'visited_heliports': visited_heliports,

        'connected_heliports': connected_heliports,
    }

    json_info = json.dumps(info)
    return Response(response=json_info, status=200, mimetype="application/json")


@app.route("/moveTo/<g_id>/<chosen_heliport_num>")
def moveTo(g_id, chosen_heliport_num):
    heliports_in_range = get_heliports_in_range(connected_heliports, g_id)
    if len(heliports_in_range) != 0:
        update_player_move((heliports_in_range[int(chosen_heliport_num)]['distance_from_player']), g_id,  heliports_in_range[int(chosen_heliport_num)]['ident']) #
        goal = check_goal(g_id, heliports_in_range[int(chosen_heliport_num)]['ident'])
    else:
        goal = False
    heliports_in_range = get_heliports_in_range(connected_heliports, g_id)
    stats = get_stats(g_id)
    visited_heliports = heliports_visited(g_id)
    # tee javascriptin puolella tarkistus mikä goal on löydetty ja näytä
    # sen tiedot pelaajalle. Jos goal on peli, kysy haluaako pelaaja pelata;
    # jos haluaa, kysy panos ja pelin vaatima mahdollinen vastaus, lähetä sen jälkeen pelikomento
    # Katso myös onko pelaajan etäisyydellä yhtään kenttää(jos ei ole
    # goal on tällöin ollut breakdown ja pelaajan polttoaine on loppu=peli loppu)
    info = {
        'goal': goal,
        'heliports_in_range': heliports_in_range,
        'stats': stats,
        'visited_heliports': visited_heliports,
    }
    jsongoal = json.dumps(info)
    return Response(response=jsongoal, status=200, mimetype="application/json")


@app.route("/play_dice/<g_id>/<bet>")
def play_dice(g_id, bet):

    result = dice_game2()
    if result == 'Won':
        winnings = int(bet) * 3
    if result == 'Lost':
        winnings = -int(bet)
    update_player_gas(g_id, winnings)

    heliports_in_range = get_heliports_in_range(connected_heliports, g_id)
    stats = get_stats(g_id)
    # päivitä heliports_in_range ja statsit, sekä näytä voittiko pelaaja(result)
    info = {
        'goal': False,
        'result': result,
        'visited_heliports' : heliports_visited(g_id),
        'heliports_in_range': heliports_in_range,
        'stats': stats,
    }
    json_info = json.dumps(info)
    return Response(response=json_info, status=200, mimetype="application/json")




@app.route("/play_coinflip/<g_id>/<bet>/<guess>")
def play_coinflip(g_id, bet, guess):
    result = coinflip2(guess)
    if result == 'Won':
        winnings = int(bet)
    if result == 'Lost':
        winnings = -int(bet)
    update_player_gas(g_id, winnings)

    heliports_in_range = get_heliports_in_range(connected_heliports, g_id)
    stats = get_stats(g_id)
    info = {
        'goal': False,

        'result': result,
        'visited_heliports' : heliports_visited(g_id),
        'heliports_in_range': heliports_in_range,
        'stats': stats,
    }
    json_info = json.dumps(info)
    return Response(response=json_info, status=200, mimetype="application/json")

print("server running")




if __name__ == "__main__":
    app.run(use_reloader=True, host="localhost", port=3000)