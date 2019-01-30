# LinkMusicBot

[@LinkMusicBot](https://t.me/LinkMusicBot) is an inline Telegram
bot that converts between various music services. To use, type
@LinkMusicBot into a Telegram chat followed by the link to a song or album.
For example, `@LinkMusicBot https://open.spotify.com/track/1ysj4ThiNp8jQ8l7Y3Ef8c`.
Then tap the suggestion that comes up to send a message with links
to the song or album on different streaming platforms.

## Setup

```shell
python3 -m pip install pawt spotipy beautifulsoup4
cp config.py.example config.py
vim config.py
```

Enter your credentials for the Spotify, Telegram, and YouTube APIs into
`config.py`.

## Usage

```shell
python3 bot.py
```
