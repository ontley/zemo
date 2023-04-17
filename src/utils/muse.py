import asyncio
import threading
import innertube
import time
import enum
import discord
import pprint
import yt_dlp

from attrs import define

from discord import FFmpegPCMAudio

from discord.opus import Encoder as OpusEncoder

from discord.enums import SpeakingState

from .queue import Queue

from utils import to_readable_time


ytdl_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
}
ytdl_client = yt_dlp.YoutubeDL(ytdl_options)

__all__ = [
    'DisconnectReason',
    'Player',
    'PlayerError',
    'Song',
    'VideoNotFoundError',
]


FFMPEG_SOURCE_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}


class VideoNotFoundError(Exception):
    pass


class PlayerError(Exception):
    pass


class DisconnectReason(enum.Enum):
    NOT_PLAYING = 0
    ALONE_IN_CHANNEL = 1


@define(kw_only=True)
class Song:
    """
    Represents a song data type.

    Song objects are returned from static methods instead of being created manually.

    Attributes
    ----------
    title: `str`
        The title of the video
    channel_name: `str`
        The name of the video uploader
    thumbnail: `str`
        URL to the thumbnail image
    page_url: `str`
        URL to the `youtube.com/watch/` page
    url: `str`
        URL to the audio stream of the song
    duration: `int`
        Duration of the song in seconds
    """

    title: str
    channel_name: str
    thumbnail: str
    page_url: str
    url: str
    duration: int

    def __str__(self) -> str:
        return f'[{self.title}]({self.page_url})'

    def __repr__(self) -> str:
        return f'Song([{self.title}]({self.page_url}))'

    @property
    def embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f'{self.title}',
            description=f'by {self.channel_name} | {to_readable_time(self.duration)}',
            url=self.page_url
        ).set_thumbnail(url=self.thumbnail)
        return embed

    @staticmethod
    def get_audio_url(id: str) -> str:
        data = ytdl_client.extract_info(f'https://youtube.com/watch?v={id}', download=False)
        print(data['url'])
        return data['url']
        
    @classmethod
    def _extract_data(cls, data: dict):
        """Find a Song object from a search query"""

        thumbnail_url = data['thumbnails'][0]['url']
        title = data['title']
        channel = data['uploader']
        page_url = data['webpage_url']
        url = data['url']
        duration = data['duration']
        
        return cls(
            title=title,
            channel_name=channel,
            thumbnail=thumbnail_url,
            page_url=page_url,
            url=url,
            duration=duration,
        )

    @classmethod
    def find_by_query(cls, query: str):
        data = ytdl_client.extract_info(f'ytsearch: {query}', download=False)['entries'][0]
        return cls._extract_data(data)


class Player(discord.player.AudioPlayer):
    """
    Wrapper class for controlling playback to a voice channel.

    Parameters
    ----------
    voice_client: `discord.VoiceClient`
        The client of the bot's connection to a voice channel
    queue: `Optional[Queue[T]]`
        An optional starting queue
    timeout: `float` = 60.0
        The default delay before automatically disconnecting if not playing or if the bot is alone

    Attributes
    ----------
    source: `Optional[discord.AudioSource]`
        The currently playing source, None if the player hasn't been started
    """

    DELAY = OpusEncoder.FRAME_LENGTH / 1000.0

    def __init__(
        self,
        voice_client: discord.VoiceClient,
        *,
        queue: Queue[Song] | None = None,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(None, voice_client) # type: ignore
        voice_client.encoder = OpusEncoder()

        self.queue: Queue[Song] = Queue() if queue is None else queue

        self._timeout_delay: float = timeout
        # maybe make this a set with DisconnectReason having the timer as attr
        self._timeouts: dict[DisconnectReason, threading.Timer] = {}
        self._source_set: threading.Event = threading.Event()
        """Required for blocking in `stop` until the source is set again in `_do_run`"""

    def _do_run(self):
        # version of the default _do_run, featuring Queue for sources
        self.loops = 0
        self._start = time.perf_counter()

        play_audio = self.client.send_audio_packet
        self._speak(SpeakingState.voice)

        while True:
            self._connected.wait()
            for song in self.queue:
                self._set_source(FFmpegPCMAudio(song.url, **FFMPEG_SOURCE_OPTIONS))
                self._source_set.set()
                self._end.clear()
                while not self._end.is_set():
                    if not self._resumed.is_set():
                        self._resumed.wait()
                        continue

                    if not self._connected.is_set():
                        self._connected.wait()
                        self.loops = 0
                        self._start = time.perf_counter()

                    self.loops += 1

                    data = self.source.read()
                    if not data:
                        break

                    play_audio(data, encode=not self.source.is_opus())
                    next_time = self._start + self.DELAY * self.loops
                    delay = max(0, self.DELAY + (next_time - time.perf_counter()))
                    time.sleep(delay)
            self.add_timeout(DisconnectReason.NOT_PLAYING)

    def _timeout(self):
        asyncio.run_coroutine_threadsafe(
            self.leave(),
            loop=self.client.loop
        )

    def add_timeout(self, reason: DisconnectReason, timeout: float | None = None):
        """
        Add a timeout

        The timeout delay can be overriden with the `timeout` argument
        """
        # add system for checking which timeout will pass sooner
        # this also made me realise that this system should be rewritten
        # since it requires manual timeout cancelling which really
        # shouldn't be a thing except for the Alone reason
        if reason in self._timeouts:
            raise ValueError(f'Timer of type {reason} was already added')
        if timeout is None:
            timeout = self._timeout_delay
        timer = threading.Timer(
            timeout,
            self._timeout
        )
        timer.start()
        self._timeouts[reason] = timer

    def cancel_timeout(self, reason: DisconnectReason):
        """Cancel a timeout"""
        timer = self._timeouts.pop(reason, None)
        if timer is not None:
            timer.cancel()

    def play(self):
        """Start the player"""
        self.cancel_timeout(DisconnectReason.NOT_PLAYING)
        if not self.is_alive():
            self.start()

    def stop(self, blocking: bool = True) -> None:
        """
        Stop playing audio, automatically starts next song.

        If `blocking` is True and the player is playing,
        block until the next source is gathered from queue
        """
        if blocking and self.is_playing():
            self._source_set.clear()
        self._end.set()
        self._resumed.set()
        self._speak(SpeakingState.none)
        self._source_set.wait()

    async def leave(self) -> None:
        await self.client.disconnect()
        self.client = None
