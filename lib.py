from bs4 import BeautifulSoup
import urllib
import hashlib
from base64 import b64encode
from urllib.parse import urlencode
import requests
import time
import json
import re
from datetime import datetime
from dateutil.parser import parse
import sqlite3
from tabulate import tabulate
from unidecode import unidecode

ALLOCINE_BASE_URL = "http://api.allocine.fr/rest/v3/"
# ALLOCINE_PARTNER_KEY = '100043982026'
ALLOCINE_PARTNER_KEY = '100ED1DA33EB'
ALLOCINE_SECRET_KEY = '1a1ed8c1bed24d60ae3472eed1da33eb'
ANDROID_USER_AGENT = "Mozilla/5.0 (Linux; U; Android $v; fr-fr; Nexus One Build/FRF91) AppleWebKit/5$b.$c (KHTML, like Gecko) Version/$a.$a Mobile Safari/5$b.$c"

PATH_DB = '/home/remy/Projects/MyCine/mycine.db'

def add_movie(movie, director=None):
    """Look for movie information and add them to the database if they are not already"""
    # Check if movie is already in database
    movie_infos = get_movie_infos(movie, director=director) # Get movie information from Allocine
    if movie_infos:
        if in_database(movie, director=director):
            print('Error : "'+movie_infos['title']+'" is already in database')
        else:
            conn = sqlite3.connect(PATH_DB) # Connect to database
            # Add row
            conn.execute('''INSERT INTO movies (actors, date_added, date, directors, duration, genres, original_title,
                                            poster_link, press_rating, spec_rating, synopsis, title)
                        VALUES (?, date(\'now\'),?,?,?,?,?,?,?,?,?,?)''',
                    (';'.join(movie_infos['actors']), 
                     movie_infos['date'], 
                     ';'.join(movie_infos['directors']),
                     int(movie_infos['duration'].total_seconds()//60),
                     ';'.join(movie_infos['genres']),
                     movie_infos['original_title'],
                     movie_infos['poster_link'],
                     movie_infos['ratings']['press'],
                     movie_infos['ratings']['spectators'],
                     movie_infos['synopsis'],
                     movie_infos['title']
                    ))
            conn.commit() # Commit
            print('Added "'+movie_infos['title']+'" to database')


def delete_movie(movie):
    """Check if movie is in database and delete it from table"""
    movie_title = get_movie_infos(movie)['title']
    if not in_database(movie):
        print('Error : "'+movie_title+'" is not in database')
    else:
        conn = sqlite3.connect(PATH_DB) # Connect to database
        conn.execute('DELETE FROM movies WHERE movies.title=?', (movie_title,))
        conn.commit()
        print('Deleted "'+movie_title+'" from database')


def display_info(movie, director=None):
    try:
        movie_infos = get_movie_infos(movie, director=director)
        ratings = movie_infos['ratings']['spectators'], movie_infos['ratings']['press']
        in_db = in_database(movie, director=director)

        print(movie_infos['title'].upper())
        print('\tDirected by : '+", ".join(movie_infos['directors']))
        print('\tOriginal title : '+movie_infos['original_title'])
        print('\tDate : '+movie_infos['date'].strftime('%d %B %Y'))
        print('\tDuration : '+str(movie_infos['duration']))
        print('\tActors : '+", ".join(movie_infos['actors']))
        print('\tGenres : '+", ".join(movie_infos['genres']))
        print('\tAllocine : '+movie_infos['page_link'])
        print('\nRATINGS')
        if ratings[0]: print('\tSpectators : {}'.format(ratings[0]))
        if ratings[1]: print('\tPress : {}'.format(ratings[1]))
        print('\nSYNOPSIS')
        print('\t'+movie_infos['synopsis'])
        print('\nIn database : '+ ('Yes' if in_db else 'No'))
        if in_db:
              print('Watched : '+ ('Yes ('+in_db['date_watched']+')' if in_db['watched'] else 'No'))
    except Exception as e:
        print('display_info : An error occurred with "{}" :'.format(movie), e)


def get_movie_infos(movieTitle, director=None):
    """
    Make a request for a movie title to Allocine.fr and returns the url of the movie page
    : param: movie, str, name of the movie
    : return: str, url of the movie page on Allocine.fr
    """
    try:
        # Get information from Allocine API
        movieTitle = unidecode(movieTitle)
        movieTitle = movieTitle.replace(' ', '+')
        sed = time.strftime("%Y%m%d")
        sha1 = hashlib.sha1()
        PARAMETER_STRING = "partner=" + ALLOCINE_PARTNER_KEY + "&q=" + movieTitle + "&format=json&sed="+sed
        SIG_STRING = bytes('search' + PARAMETER_STRING + ALLOCINE_SECRET_KEY, 'utf-8')
        sha1.update(SIG_STRING)
        SIG_SHA1 = sha1.digest()
        SIG_B64 = b64encode(SIG_SHA1).decode('utf-8')
        sig = urlencode({SIG_B64: ''})[:-1]
        URL = ALLOCINE_BASE_URL + 'search?' + PARAMETER_STRING + "&sig=" + sig
        headers = {'User-Agent': ANDROID_USER_AGENT}
        results = requests.get(URL, headers=headers).text
        movies = json.loads(results)["feed"]["movie"]
        if director:
            metaDico = [movie for movie in movies 
                              if "castingShort" in movie.keys() and "directors" in movie["castingShort"].keys()
                              and director.lower() in movie["castingShort"]["directors"].lower()][0]
        else:
            metaDico = movies[0]

        # Initialize output
        data = {
            "title":None,
            "original_title":None,
            "poster_link":None,
            "date":None,
            "duration":None,
            "genres":None,
            "directors":[],
            "actors":[],
            "ratings":{'press':None, 'spectators':None},
            "synopsis":None,
            "page_link":None
               }

        # Load html page
        url = metaDico['link'][0]['href']
        data["page_link"] = url
        page = urllib.request.urlopen(url)
        soup = BeautifulSoup(page, 'html.parser')

        # Title
        tag_title = soup.find(attrs={"class":"titlebar-title-lg"})
        data["title"] = tag_title.getText()
        data["original_title"] = metaDico['originalTitle']

        # Poster
        tag_poster = soup.find(attrs={"class":"thumbnail-img"})
        data["poster_link"] = tag_poster.attrs["src"]

        # Meta Infos
        tag_info = soup.find(attrs={"class":"meta-body-info"})
        text = tag_info.getText()
        text = text.replace('en VOD', '')
        text = text.replace('en DVD', '')
        text = text.replace('sur Netflix', '')
        text = text.replace('Disney+', '')
        p = re.compile('[^— \t\n\r\f\v]')
        infos = "".join(p.findall(text))
        date, duration, genres = infos.split('/')
        data['date'] = parse(replace_month(date)) # Date
        data['duration'] = datetime.strptime(duration, '%Hh%Mmin') - datetime.strptime('0','%H') # Duration
        data['genres'] = genres.split(',') # Genres

        # Directors
        tag_dirs = soup.find(attrs={"class":"meta-body-direction"})
        directors = tag_dirs.find_all(attrs={"class":"blue-link"})
        data["directors"] = [director.getText() for director in directors]

        # Actors
        tag_act = soup.find(attrs={"class":"meta-body-actor"})
        data["actors"] = [child.string for child in list(tag_act.children) if '\n' not in child.string][1:]

        # Ratings
        try:
            data["ratings"]["press"] = round(metaDico["statistics"]["pressRating"], 1)
        except: pass
        try:
            data["ratings"]["spectators"] = round(metaDico["statistics"]["userRating"], 1)
        except: pass

        # Synopsis
        tag_syn = soup.find(attrs={"id":"synopsis-details"})
        tag_syn = tag_syn.find(attrs={"class":"content-txt"})
        p = re.compile('[\s]{2,}')
        text = tag_syn.getText()
        for space in p.findall(text):
            text = text.replace(space, '')
        data["synopsis"] = text.replace('\n', '')
        return data
                    
    except Exception as e:
        print('get_movie_infos : An error occurred with "{}" :'.format(movieTitle), e)
                    
                    
def in_database(movie, director=None):
    movie_infos = get_movie_infos(movie, director=director) # Get movie information from Allocine
    conn = sqlite3.connect(PATH_DB) # Connect to database
    # Check if movie is already in database
    res = conn.execute("SELECT watched, date_watched FROM movies WHERE movies.title=?",
                       (movie_infos['title'],)).fetchall()
    if len(res):
        return {'watched':res[0][0], 'date_watched':res[0][1]}
    else:
        return False

    
def list_movies(watched=None, lmax=25):
    """List movies in the database. Set 'watched' parameter to True or False for filtering"""
    conn = sqlite3.connect(PATH_DB) # Connect to database
    
    # Process options
    condition = ''
    values = tuple()
    if watched is not None:
        condition = 'WHERE watched=?'
        values = (watched,)
        
    # Make request
    cursor = conn.execute('SELECT title, duration, press_rating, spec_rating, watched'+\
                          ' FROM movies '+condition+\
                          ' ORDER BY duration', values)
    rows = cursor.fetchall()
    columns = ['Title', 'Duration', 'Presse', 'Spec', 'Watched']
    
    for i, row in enumerate(rows):
        if len(row[0]) > lmax:
            rows[i] = (row[0][:lmax-3]+'...',)+row[1:]
    # Display
    print(tabulate(rows, headers=columns, numalign='center'))
    
    

def make_request(request, lmax=25):
    try:
        conn = sqlite3.connect(PATH_DB)
        cursor = conn.execute(request)
        rows = cursor.fetchall()
        columns = [desc[0].title() for desc in cursor.description]
        rows = [tuple([attr[:lmax-3]+'...'  if isinstance(attr, str) and len(attr)>lmax
                                            else attr for attr in row])
                for row in rows]
        print(tabulate(rows, headers=columns))
    except Exception as e:
        print('make_request : An error occurred :', e)
        
def replace_month(text):
    """Translates month from french to english"""
    dict_months = {
        'janvier':'january',
        'février':'february',
        'mars':'march',
        'avril':'april',
        'mai':'may',
        'juin':'june',
        'juillet':'july',
        'août':'august',
        'septembre':'september',
        'octobre':'october',
        'novembre':'november',
        'décembre':'december'
    }
    for month in dict_months.keys():
        if month in text:
            return text.replace(month, dict_months[month])


def reset_db():
    """Drops previous tables and creates new empty ones"""
    conn = sqlite3.connect(PATH_DB)
    conn.execute('DROP TABLE IF EXISTS MOVIES;')
    conn.execute('''CREATE TABLE MOVIES
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         actors TEXT,
         date DATE NOT NULL,
         date_added DATE,
         directors TEXT,
         duration INT,
         genres TEXT,
         original_title TEXT,
         poster_link TEXT,
         press_rating NUMERIC,
         spec_rating NUMERIC,
         synopsis TEXT,
         title TEXT NOT NULL,
         video_link TEXT,
         watched BOOLEAN DEFAULT 0
         )''')
    conn.commit()

def set_watched(movie, director=None, watched=1):
    try:
        movie_title = get_movie_infos(movie, director=director)['title']
        in_db = in_database(movie, director=director)
        if in_db:
            if watched and in_db['watched']:
                print('Error : "'+movie_title+'" has already been seen')
            else:
                conn = sqlite3.connect(PATH_DB)
                conn.execute('UPDATE movies SET watched=? WHERE title=?', (bool(watched), movie_title))
                if watched:
                    conn.execute('UPDATE movies SET date_watched=date(\'now\') WHERE title=?', (movie_title,))
                else:
                    conn.execute('UPDATE movies SET date_watched=NULL WHERE title=?', (movie_title,))
                conn.commit()
                print("'"+movie_title+"' has been set to '"+"not "*(not watched)+"watched'")
        else:
            print('Error : "'+movie_title+'" is not in database')
    except Exception as e:
        print('set_watched : An error occurred with "{}" :'.format(movie), e)

def set_video_link(movie, director=None, link=None):
    try:
        movie_title = get_movie_infos(movie, director=director)['title']
        in_db = in_database(movie, director=director)
        if in_db:
            conn = sqlite3.connect(PATH_DB)
            conn.execute('UPDATE movies SET video_link=? WHERE title=?', (link, movie_title))
            conn.commit()
        else:
            print('Error : "'+movie_title+'" is not in database')
    except Exception as e:
        print('set_video_link : An error occurred with "{}" :'.format(movie), e)





