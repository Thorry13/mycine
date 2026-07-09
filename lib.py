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
import os

ALLOCINE_API_URL = "https://graph.allocine.fr/v1/mobile"
ALLOCINE_AUTOCOMPLETE_URL = "https://www.allocine.fr/_/autocomplete/mobile/movie/"
MOVIE_BASE_URL = "https://www.allocine.fr/film/fichefilm_gen_cfilm="
ANDROID_USER_AGENT = 'androidapp/0.0.1'

AC_AUTH_VAR = os.getenv("MYCINE_AUTH")
AC_AUTH_TOKEN_VAR = os.getenv("MYCINE_AUTH_TOKEN")

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
        if movie_infos['date'] is not None:
            print('\tDate : '+movie_infos['date'].strftime('%d %B %Y'))
        print('\tDuration : '+str(movie_infos['duration']))
        print('\tActors : '+", ".join(movie_infos['actors']))
        if movie_infos['genres']:
            print('\tGenres : '+", ".join(movie_infos['genres']))
        print('\tAllocine : '+movie_infos['page_link'])
        print('\nRATINGS')
        if ratings[0]: print('\tSpectators : {}'.format(ratings[0]))
        if ratings[1]: print('\tPress : {}'.format(ratings[1]))
        print('\nSYNOPSIS\n\t', end='')
        print(movie_infos['synopsis'])
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
        GET_URL = ALLOCINE_AUTOCOMPLETE_URL + movieTitle.replace(' ', '+')
        headers = {'User-Agent': ANDROID_USER_AGENT,
           'Content-Type' : 'application/json',
           'Authorization' : AC_AUTH_VAR,
           'AC-Auth-Token' : AC_AUTH_TOKEN_VAR
          }
        get_response = requests.get(GET_URL, headers=headers).text
        get_results = json.loads(get_response)['results']
        if director:
            director_presence_check = lambda director_i : director.lower() in director_i.lower()
            get_results = [movie for movie in get_results
                                if 'data' in movie.keys()
                                    and 'director_name' in movie['data'].keys()
                                    and True in list(map(director_presence_check, movie['data']['director_name']))]
        movie_id0 = get_results[0]['entity_id']
        movie_id = b64encode(bytes('Movie:'+movie_id0, 'utf-8')).decode('utf-8')
        query = "query MovieQuery($id: String, $longSynopsis: Boolean, $country: CountryCode) { movie(id: $id) { __typename ...MovieFragment } } fragment MovieFragment on Movie  { __typename id internalId title originalTitle genres type poster { __typename id internalId url } synopsis(long: $longSynopsis) cast(first: 3)  { __typename edges  { __typename node { __typename role actor { __typename id internalId firstName lastName } voiceActor { __typename id internalId firstName lastName } originalVoiceActor { __typename id internalId firstName lastName } } } }stats { __typename userRating { __typename score(base: 5) } pressReview { __typename score(base: 5) } }credits(department: DIRECTION, first: 5) { __typename edges{ __typename node{ __typename person{ __typename id firstName lastName } position { __typename name } } } } releases(type: [RELEASED], country: $country) { __typename releaseDate { __typename date precision } } data { __typename productionYear } }"
        variables = {"id":movie_id, "longSynopsis":True, "country":"FRANCE"}

        post_response = requests.post(ALLOCINE_API_URL, headers=headers, json = {'query':query, 'variables':variables}).text
        post_results = json.loads(post_response)['data']['movie']

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
        movie_url = MOVIE_BASE_URL + movie_id0 + '.html'
        req = urllib.request.Request(url=movie_url, headers=headers)
        page = urllib.request.urlopen(req).read()
        soup = BeautifulSoup(page, 'html.parser')
        data["page_link"] = movie_url

        # Title
        data["title"] = post_results['title']
        data["original_title"] = post_results['originalTitle']

        # Poster
        data["poster_link"] = post_results['poster']['url']

        # Genres/Duration
        try:
            tag_info = soup.find(attrs={"class":"meta-body-info"})
            text = tag_info.getText()
            text = text.replace('en VOD', '').replace('en DVD', '').replace('sur Netflix', '').replace('Disney+', '')
            p = re.compile('[^— \t\n\r\f\v]')
            infos = "".join(p.findall(text))
            _, duration, genres = infos.split('/')
            data['duration'] = datetime.strptime(duration, '%Hh%Mmin') - datetime.strptime('0','%H') # Duration
            data['genres'] = genres.split(',') # Genres
        except: pass

        # Release date
        if 'releases' in post_results.keys() and post_results['releases']:
            data['date'] = parse(post_results['releases'][0]['releaseDate']['date'])

        # Directors
        data['directors'] = ['{}'.format(person['node']['person']['firstName'] + ' '
                         if person['node']['person']['firstName'] 
                         else '') +
             person['node']['person']['lastName'] 
             for person in post_results['credits']['edges']]

        # Actors
        if post_results['cast']['edges'][0]['node']['actor'] :
            actor_var = 'actor'
        else :
            actor_var = 'voiceActor'
        data['actors'] = ['{}'.format(person['node'][actor_var]['firstName'] + ' ' 
                      if person['node'][actor_var]['firstName'] 
                      else '') +
          person['node'][actor_var]['lastName'] 
             for person in post_results['cast']['edges']]

        # Ratings
        try:
            data["ratings"]["press"] = round(post_results['stats']['pressReview']['score'], 1)
        except: pass
        try:
            data["ratings"]["spectators"] = round(post_results['stats']['userRating']['score'], 1)
        except: pass

        # Synopsis
        if post_results['synopsis']:
            html = post_results['synopsis']
            synopsis = BeautifulSoup(html, 'html.parser').text
            data["synopsis"] = synopsis.replace('\n', '')

        # Return results
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

if __name__ == "__main__":
    print('main...')
    get_movie_infos('iron')
    




