# mycine
Extracts, stores and displays cinematographic data

## Installation

1. Clone the repository.
2. Set MYCINE_LOCATION environment variable: `export MYCINE_LOCATION=/path/to/mycine`.
3. Register mycine.sh to PATH

## Usage

_mycine_ lets you do the following:

- Have a glimpse at movie detais: `mycine -i "joker"`.
- Add movie to database: `mycine -a "joker"`.
- Remove movie to database: `mycine -d "joker"`.
- Set a movie as watched: `mycine -w "joker"`.

For all above, use `--dir "director name"` if the selected movie is not the one expected.

- Display your watchlist: `mycine -l`.
- Display your watchlist with watched/unwatched filter: `mycine -l -w 1` `mycine -l -w 0`.
- Display watched summary.

## Troubleshooting

Allocine API calls may fail when token expires.

```bash
$ mycine -i "django unchained"
get_movie_infos : An error occurred with "django unchained" : 'data'
display_info : An error occurred with "django unchained" : 'NoneType' object is not subscriptable
```

In that case, you can find a new available token by intercepting Allocine app requests with a proxy (e.g. mitmproxy).

Your proxy certificate will need to be trusted at system-level, which you can do on rooted devices only.
If you don't want rooting your own device, you can use emulated device with writable system.

Then inspect POST reqests to https://graph.allocine.fr/v1/mobile and get _authorization_ and _ac-auth-token_.
Finally, set the following environment variables:
`export MYCINE_AUTH=...`
`export MYCINE_AUTH_TOKEN=...`


