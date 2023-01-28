import asyncio
import threading
import pytube
import time
import enum
import discord
from attrs import define
from typing import Any, Callable, Optional, Self
from discord import FFmpegPCMAudio
from discord.opus import Encoder as OpusEncoder
from discord.enums import SpeakingState
from utils.queue import Queue
from utils import to_readable_time


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

    Song objects are returned from `find_video` instead of being created manually.

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
    def find_by_query(query: str) -> Self:
        """Find a Song object from a search query"""
        results = pytube.Search(query).results
        if not results:
            raise VideoNotFoundError(f'Couldn\'t find video from query {query}')
        video = results[0]
        url = video.streams.get_audio_only().url

        return Song(
            title=video.title,
            channel_name=video.author,
            thumbnail=video.thumbnail_url,
            page_url=video.watch_url,
            url=url,
            duration=video.length
        )

    @staticmethod
    def find_by_url(url: str) -> Self:
        """Find a Song object from a youtube url"""
        video = pytube.YouTube(url)
        url = video.streams.get_audio_only().url
        return Song(
            title=video.title,
            channel_name=video.author,
            thumbnail=video.thumbnail_url,
            page_url=video.watch_url,
            url=url,
            duration=video.length
        )


# Yes this is mostly stolen from the library itself
# I just wanted to make a version which can work with a loop
# and is a single thread instead of creating a thread per source
class Player(threading.Thread):
    """
    Wrapper class for controlling playback to a voice channel.

    Parameters
    ----------
    voice_client: `discord.VoiceClient`
        The client of the bot's connection to a voice channel
    queue: `Optional[Queue[T]]`
        An optional starting queue
    on_error: `Optional[Callable[[Optional[Exception]], Any]]`
        A function run when the player errors

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
        queue: Optional[Queue[Song]] = None,
        timeout: float = 15.0,
        on_error: Optional[Callable[[Optional[Exception]], Any]] = None
    ) -> None:
        threading.Thread.__init__(self)
        self.daemon = True
        self.voice_client = voice_client
        self.voice_client.encoder = OpusEncoder()
        self.queue = Queue() if queue is None else queue

        self.source = None

        self._active = threading.Event()
        self._active.set()

        self._timeout_delay = timeout
        self._timeouts: dict[DisconnectReason, threading.Timer] = {}

        self._end = threading.Event()
        self._source_set = threading.Event()
        self._resumed = threading.Event()
        self._resumed.set()
        self._connected = voice_client._connected

        self.on_error = on_error

    def _do_run(self):
        self.loops = 0
        self._start = time.perf_counter()
        self._speak(SpeakingState.voice)

        play = self.voice_client.send_audio_packet

        while self._connected.is_set():
            self._active.wait()
            for song in self.queue:
                self._source_set.set()
                self.source = FFmpegPCMAudio(song.url, **FFMPEG_SOURCE_OPTIONS)
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
                        self._end.set()
                        break

                    play(data, encode=not self.source.is_opus())
                    next_time = self._start + self.DELAY * self.loops
                    delay = max(0, self.DELAY + (next_time - time.perf_counter()))
                    time.sleep(delay)
            self.add_timeout(DisconnectReason.NOT_PLAYING)

    def _timeout(self):
        asyncio.run_coroutine_threadsafe(
            self.leave(),
            loop=self.voice_client.loop
        )

    def add_timeout(self, reason: DisconnectReason):
        if reason in self._timeouts:
            raise ValueError(f'Timer of type {reason} was already added')
        timer = threading.Timer(
            self._timeout_delay,
            self._timeout
        )
        timer.start()
        self._timeouts[reason] = timer

    def cancel_timeout(self, reason: DisconnectReason):
        timer = self._timeouts.pop(reason, None)
        if timer is not None:
            timer.cancel()

    def run(self):
        try:
            self._do_run()
        except Exception as e:
            if self.source is not None:
                self.source.cleanup()
                self._call_on_error(e)

    def play(self):
        self.cancel_timeout(DisconnectReason.NOT_PLAYING)
        if self.is_alive():
            self._active.set()
        else:
            self.start()

    def _call_on_error(self, e):
        if self.on_error is None:
            raise e
        try:
            self.on_error(e)
        except Exception as err:
            raise PlayerError('Player on_error raised exception') from err

    def stop(self, blocking: bool = True) -> None:
        '''
        Stop playing audio, automatically starts next song.

        If `blocking` is True and the player is playing,
        block until the next source is gathered from queue
        '''
        if blocking and self.is_playing():
            self._source_set.clear()
        self._end.set()
        self._resumed.set()
        self._speak(SpeakingState.none)
        self._source_set.wait()

    async def leave(self) -> None:
        await self.voice_client.disconnect()

    def pause(self, *, update_speaking: bool = True) -> None:
        self._resumed.clear()
        if update_speaking:
            self._speak(SpeakingState.none)

    def resume(self, *, update_speaking: bool = True) -> None:
        self.loops = 0
        self._start = time.perf_counter()
        self._resumed.set()
        if update_speaking:
            self._speak(SpeakingState.voice)

    def is_playing(self) -> bool:
        return self.source is not None and self._resumed.is_set() and not self._end.is_set()

    def is_paused(self) -> bool:
        return not self._end.is_set() and not self._resumed.is_set()

    def _speak(self, speaking: SpeakingState):
        asyncio.run_coroutine_threadsafe(
            self.voice_client.ws.speak(speaking), self.voice_client.loop)


