import re
from html import unescape
from json import loads
from urllib.parse import parse_qs, urlparse

import requests
import spotipy
from bs4 import BeautifulSoup
from spotipy.oauth2 import SpotifyClientCredentials

from config import secrets


class Album:
    """Class to represent an album."""

    def __init__(self, title, artist):
        """Initialize the album."""
        self.title = title
        self.artist = artist

    def __repr__(self):
        return 'Album({!r}, {!r})'.format(self.title, self.artist)

    def __str__(self):
        return '{} by {}'.format(self.title, self.artist)


class Song:
    """Class to represent a song."""

    def __init__(self, title, artist, album):
        """Initialize the song."""
        self.title = title
        self.artist = artist
        self.album = album

    def __repr__(self):
        return 'Song({!r}, {!r}, {!r})'.format(self.title, self.artist, self.album)

    def __str__(self):
        return '{} — {}'.format(self.artist, self.title)


class ServiceHandler:
    """Parent class for processing and returning links of various services."""

    @staticmethod
    def service_name():
        """Get the name of the service."""
        raise NotImplementedError()

    def album_to_link(self, album):
        """Take an Album and return a link."""
        raise NotImplementedError()

    def can_handle_link(self, link):
        """Returns True if and only if the class can handle the provided link."""
        raise NotImplementedError()

    def link_is_song(self, link):
        """Returns True if the link is a song, False if it is an album."""
        raise NotImplementedError()

    def link_to_album(self, link):
        """Take a link and return an Album."""
        raise NotImplementedError()

    def link_to_song(self, link):
        """Take a link and return a Song."""
        raise NotImplementedError()

    def song_to_link(self, song):
        """Take a Song and return a link."""
        raise NotImplementedError()


class AppleMusic(ServiceHandler):
    """ServiceHandler for Apple Music."""

    _BASE_SEARCH_URL = 'https://itunes.apple.com/search'

    @staticmethod
    def _format_query(item):
        """Format a search query."""
        return '{} {}'.format(item.title, item.artist)

    @staticmethod
    def service_name():
        """Name Apple Music."""
        return 'Apple Music'

    def _search(self, term, country='US', media=None, entity=None, attribute=None, limit=50, lang='en_us', version=2,
                explicit=None):
        """Search iTunes."""
        query = {'term': term, 'country': country, 'limit': limit, 'lang': lang, 'version': version}
        if explicit is not None:
            query['explicit'] = 'Yes' if explicit else 'No'
        for name, value in (('media', media), ('entity', entity), ('attribute', attribute)):
            if value is not None:
                query[name] = value
        results = requests.get(self._BASE_SEARCH_URL, params=query)

        return results.json()

    def album_to_link(self, album):
        """Turn an Album into an Apple Music link."""
        search = self._search(self._format_query(album), media='music', entity='album', explicit=True)
        if search['resultCount'] < 1:
            raise ValueError("Couldn't find any album results for {!r}.".format(album))
        return search['results'][0]['collectionViewUrl']

    def can_handle_link(self, link):
        """Return True if and only if this is an Apple Music link."""
        return urlparse(link).netloc.lower() == 'itunes.apple.com'

    def link_is_song(self, link):
        """Return True if the link is a song, or False if it's an album."""
        queries = parse_qs(urlparse(link).query)
        return 'i' in queries

    def link_to_album(self, link):
        """Turn an Apple Music link into an Album."""
        page = BeautifulSoup(requests.get(link).text, 'html.parser')

        album_schema = page.find('script', type='application/ld+json')
        page_info = loads(album_schema.contents[0])
        return Album(unescape(page_info['name']), unescape(page_info['byArtist']['name']))

    def link_to_song(self, link):
        """Turn an Apple Music link into a Song."""
        page = BeautifulSoup(requests.get(link).text, 'html.parser')

        track_name = page.find(class_='is-deep-linked').find(class_='table__row__headline').text.strip()

        album_schema = page.find('script', type='application/ld+json')
        page_info = loads(album_schema.contents[0])
        return Song(unescape(track_name), unescape(page_info['byArtist']['name']), unescape(page_info['name']))

    def song_to_link(self, song):
        """Turn a Song into an Apple Music link."""
        search = self._search(self._format_query(song), media='music', entity='song', explicit=True)
        if search['resultCount'] < 1:
            raise ValueError("Couldn't find any song results for {!r}.".format(song))
        return search['results'][0]['trackViewUrl']


class Spotify(ServiceHandler):
    """ServiceHandler for Spotify."""
    _PARENS_PATTERN = re.compile(r'\([^(]*\)')

    @staticmethod
    def _format_query(item):
        """Format a query from an item."""
        query = 'artist:"{}"'.format(item.artist)
        if isinstance(item, Song):
            query += ' track:"{}"'.format(item.title)
        elif isinstance(item, Album):
            query += ' album:"{}"'.format(item.title)
        return query

    @staticmethod
    def service_name():
        """Name Spotify."""
        return 'Spotify'

    def __init__(self):
        """Initialize the Spotify instance."""
        self._spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=secrets.get(
            'spotify_client_id'), client_secret=secrets.get('spotify_client_secret')))

    def _naive_query(self, item):
        """Format a less accurate but more forgiving query for an item."""
        return '{} {}'.format(re.sub(self._PARENS_PATTERN, '', item.title),
                              item.artist)

    def album_to_link(self, album):
        """Convert an Album into a Spotify link."""
        search = self._spotify.search(self._format_query(album), type='album')
        if search['albums']['total'] < 1:
            search = self._spotify.search(self._naive_query(album), type='album')
            if search['albums']['total'] < 1:
                raise ValueError("Couldn't find any album results for {!r}.".format(album))
        return search['albums']['items'][0]['external_urls']['spotify']

    def can_handle_link(self, link):
        """Return True if and only if this is a Spotify link."""
        return urlparse(link).netloc.lower() == 'open.spotify.com'

    def link_is_song(self, link):
        """Return True if the Spotify link is a song, and False if it is an album"""
        return 'track' in link

    def link_to_album(self, link):
        """Convert a Spotify link into an Album."""
        album = self._spotify.album(link)
        return Album(album['name'], album['artists'][0]['name'])

    def link_to_song(self, link):
        """Convert a Spotify link into a Song."""
        song = self._spotify.track(link)
        return Song(song['name'], song['artists'][0]['name'], song['album']['name'])

    def song_to_link(self, song):
        """Convert a Song into a Spotify link."""
        search = self._spotify.search(self._format_query(song))
        if search['tracks']['total'] < 1:
            search = self._spotify.search(self._naive_query(song))
            if search['tracks']['total'] < 1:
                raise ValueError("Couldn't find any song results for {!r}.".format(song))
        return search['tracks']['items'][0]['external_urls']['spotify']
