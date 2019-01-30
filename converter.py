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


class YouTube(ServiceHandler):
    _PLAYLIST_PATH = 'https://www.googleapis.com/youtube/v3/playlists'
    _SEARCH_PATH = 'https://www.googleapis.com/youtube/v3/search'

    @staticmethod
    def _format_album_query(item):
        """Format a query for an Album."""
        return '{} {} full album'.format(item.title, item.artist)

    @staticmethod
    def _format_song_query(item):
        """Format a query for a Song."""
        return '{} {} topic'.format(item.title, item.artist)

    @staticmethod
    def _link_to_id(link):
        """Take a YouTube link and return a playlist ID."""
        return parse_qs(urlparse(link).query)['list'][0]

    @staticmethod
    def _playlist_link(playlist_data):
        """Get a playlist link from a data payload."""
        return 'https://www.youtube.com/playlist?list={}'.format(playlist_data['id']['playlistId'])

    @staticmethod
    def _video_link(video_data):
        """Get a video link from a data payload"""
        return 'https://youtube.com/watch?v={}'.format(video_data['id']['videoId'])

    @staticmethod
    def service_name():
        """Return the name of YouTube."""
        return 'YouTube'

    def __init__(self):
        """Initialize the class."""
        self._yt_token = secrets.get('youtube_token')

    def _get(self, url, params=None):
        """Get a URL with certain parameters."""
        if params is None:
            params = {}

        key_set = False
        if 'key' not in params:
            params['key'] = self._yt_token
            key_set = True
        response = requests.get(url, params=params).json()
        if key_set:
            del params['key']
        return response

    def album_to_link(self, album):
        """Turn an Album into a YouTube link."""
        params = {'part': 'snippet',
                  'maxResults': 1,
                  'q': self._format_album_query(album),
                  'type': 'playlist'}
        response = self._get(self._SEARCH_PATH, params)

        if len(response['items']) < 1:
            raise ValueError("Couldn't find any album results for {!r}.".format(album))
        return self._playlist_link(response['items'][0])

    def can_handle_link(self, link):
        """Return True if and only if this is a YouTube link."""
        return urlparse(link).netloc.lower() in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be')

    def link_is_song(self, link):
        """Return True if a link is a song, and False if it's an album."""
        parsed_url = urlparse(link)
        if parsed_url.netloc.lower() in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
            return parsed_url.path == '/watch'
        return True  # youtu.be link

    def link_to_album(self, link):
        """Turn a YouTube link into an Album.

        Warning: This is super shaky, because it just takes a playlist and converts it. There will be plenty of
        unexpected behavior!
        """
        params = {'part': 'snippet',
                  'id': self._link_to_id(link)}
        response = self._get(self._PLAYLIST_PATH, params)
        if len(response['items']) < 1:
            raise ValueError('Not an album: {!r}'.format(link))

        return Album(response['items'][0]['snippet']['title'], '')  # empty artist because we really can't know

    def link_to_song(self, link):
        """Turn a YouTube link into a Song."""
        # Unfortunately, this info is NOT provided by the API, so... we're doing more webscraping!
        page = BeautifulSoup(requests.get(link).text, 'html.parser')
        title = artist = album = None
        for metadata in page.find_all('li', class_='watch-meta-item'):
            metadata_name = metadata.h4.string.strip()
            metadata_value = metadata.ul.li.string.strip()

            if metadata_name == 'Song':
                title = metadata_value
            elif metadata_name == 'Artist':
                artist = metadata_value
            elif metadata_name == 'Album':
                album = metadata_value

        if None in (title, artist):
            raise ValueError('Not a song: {!r}'.format(link))

        return Song(title, artist, album)

    def song_to_link(self, song):
        """Turn a Song into a YouTube link."""
        params = {'part': 'snippet',
                  'maxResults': 1,
                  'q': self._format_song_query(song),
                  'type': 'video'}
        response = self._get(self._SEARCH_PATH, params)

        if len(response['items']) < 1:
            raise ValueError("Couldn't find any song results for {!r}.".format(song))
        return self._video_link(response['items'][0])
