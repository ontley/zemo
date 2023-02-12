from attrs import define
from utils.muse import Player


__all__ = [
    'MusicData',
    'music_data'
]


@define(frozen=True)
class MusicData:
    players: dict[int, Player] = {}


music_data = MusicData()

