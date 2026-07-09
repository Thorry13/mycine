# mycine
> \:computer\: A CLI tool to extract, store, and display cinematographic data from Allocine \:clapper\:.

## Prerequisites
- Python 3.8+

## Installation

1. Clone the repository.
```bash
git clone https://github.com/yourusername/mycine.git
```

2. Set the `MYCINE_LOCATION` environment variable:
```bash
export MYCINE_LOCATION=/path/to/mycine
```

3. Set the `MYCINE_AUTH` and `MYCINE_AUTH_TOKEN` environement variables.

```bash
export MYCINE_AUTH=...
export MYCINE_AUTH_TOKEN=...
```

> \:warning\: **Warning:** Retrieving Allocine tokens requires technical steps (proxy setup, rooted/emulated devices). See **Authentication** section for more details

4. Have mycine.sh executable and add it to the PATH. For instance:

```bash
chmod +x mycine.sh
sudo cp mycine.sh /usr/local/bin/mycine
```

5. Enjoy! \:popcorn\:

## Authentication
Allocine API calls will fail if token expires or is missing.

```bash
$ mycine -i "django unchained"
get_movie_infos : An error occurred with "django unchained" : 'data'
display_info : An error occurred with "django unchained" : 'NoneType' object is not subscriptable
```

To find a new available token, intercept Allocine app requests with a proxy:

1. Set your proxy server (e.g. mitmproxy).
2. Trust the certificate at system-level.
3. Configure proxy on your device
4. Run Allocine app
5. Intercept requests to https://graph.allocine.fr/v1/mobile
6. Extract _authorization_ and _ac-auth-token-_
7. Set the associated environment variables

Your proxy certificate will need to be trusted at system-level, which you can do on rooted devices only.
If you don't want rooting your own device, you can use emulated device with writable system.

Then inspect POST reqests to https://graph.allocine.fr/v1/mobile and read _authorization_ and _ac-auth-token_.
Finally, set the associated environment variablesi as shown above: MYCINE_AUTH and MYCINE_AUTH_TOKEN.

## Usage

### Commands
 | Command                     | Description                          |
 |-----------------------------|--------------------------------------|
 | `mycine -i "joker"`         | Display movie details                |
 | `mycine -a "joker"`         | Add movie to database                |
 | `mycine -d "joker"`         | Remove movie from database           |
 | `mycine -w "joker"`         | Mark movie as watched                |
 | `mycine -l`                 | Display watchlist                     |
 | `mycine -l -w 1`            | Display watched movies                |
 | `mycine -l -w 0`            | Display unwatched movies              |
 | `mycine -s`                 | Display watched summary              |
 | `mycine -s --dir`           | Display watched summary of director-related movies |

> **Note:** Use `--dir "director name"` if multiple movies match your query.

### Examples

```bash
$ mycine -i "fargo"
FARGO
        Directed by : Joel Coen, Ethan Coen
        Original title : Fargo
        Date : 23 July 2026
        Duration : None
        Actors : William H. Macy, Frances McDormand, Steve Buscemi
        Allocine : https://www.allocine.fr/film/fichefilm_gen_cfilm=14928.html

RATINGS
        Spectators : 4.2
        Press : 4.8

SYNOPSIS
        Un vendeur de voitures d’occasion endetté fait enlever sa femme par deux petites frappes afin de toucher la rançon qui sera versée par son richissime beau-père. Mais le plan ne va pas résister longtemps à l’épreuve des faits et au flair d’une policière enceinte…

In database : Yes
Watched : Yes (2020-06-04)
```

```bash
$ mycine -a inception
Added "Inception" to database
```

```bash
$ mycine -d inception
Deleted "Inception" from database
```

```bash
$ mycine -l
Title                       Duration    Presse    Spec    Watched
-------------------------  ----------  --------  ------  ---------
Au Poste!                      71        3.8      3.1        1
Polytechnique                  76                 3.8        1
L'Intruse                      77                 4.1        0
Le Daim                        80        3.8       3         1
Le Dîner de cons               80                 4.2        1
Les Triplettes de Bell...      80        4.5      3.4        0
Les Hirondelles de Kaboul      81        3.8       4         1
J'ai perdu mon corps           81        4.3      4.2        0
90's                           84        3.9      4.1        1
Le Géant de fer                85         4       4.1        0
Le Roi et l'oiseau             87        4.8      4.1        1
Mon voisin Totoro              87        4.4      4.3        1
.
.
.
```

```bash
$ mycine -s
  Watched    Count(*)
---------  ----------
        0         150
        1         121
```

```bash
$ mycine -s --dir bong
Title                        Watched
-------------------------  ---------
Memories of Murder                 1
Parasite                           1
Snowpiercer, Le Transp...          1
The Host                           0
Okja                               1
Mother                             1
```
