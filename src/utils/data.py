from attrs import define
from utils.muse import Player


@define(frozen=True)
class MusicData:
    players: dict[int, Player] = {}


music_data = MusicData()

__all__ = [
    'MusicData',
    'music_data'
]
