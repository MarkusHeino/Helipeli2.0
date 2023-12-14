import config
import mysql.connector

yhteys = mysql.connector.connect(
         host='127.0.0.1',
         port= 3306,
         database='demo_game',
         user=config.user,
         password=config.pwd,
         autocommit=True
        )

def get_high_scores():
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute("SELECT * FROM high_score ORDER BY score DESC")
    tulos = kursori.fetchall()
    return tulos


def get_high_score(list_id):
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(f"SELECT screen_name, score, list_id  FROM high_score where list_id = '{list_id}' ORDER BY score DESC")
    tulos = kursori.fetchone()
    return tulos


#asetetaan pelaajan pisteet tulostaulukkoon
def update_highscore(p_info, list_id):
    sql = f"update high_score set screen_name = '{p_info['screen_name']}', score = '{p_info['score']}' where list_id = '{list_id}' "
    kursori = yhteys.cursor()
    kursori.execute(sql)


#näytetään tulostaulu
def return_highscores():
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute("SELECT * FROM high_score ORDER BY score DESC")
    tulos = kursori.fetchall()
    return tulos

def handle_high_score_update(name_and_score):
    high_scores = get_high_scores()
    for i, high_score in enumerate(high_scores):
        if high_score['score'] < name_and_score['score']:
            if i != len(high_scores)-1:
                for index in range(len(high_scores), i+1, -1):
                    prev_high_score = get_high_score(index-1)
                    update_highscore(prev_high_score, index)
            update_highscore(name_and_score, high_score['list_id'])
            break