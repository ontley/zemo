import os
import json
from attrs import define
from utils.muse import Player


__all__ = [
    'MusicData',
    'music_data'
]


@define(frozen=True)
class MusicData:
    players: dict[int, Player] = {}
    """Mapping of voice channel ids to Player objects"""

    @property
    def user_themes(self) -> dict[str, str]:
        """Mapping of user ids to their theme url"""
        with open(f'{os.getcwd()}/data/user_themes.json', 'r') as f:
            return json.load(f)

    def set_theme(self, user_id: int | str, url: str):
        """Set the theme for a user"""
        themes = self.user_themes
        with open(f'{os.getcwd()}/data/user_themes.json', 'w') as f:
            themes[str(user_id)] = url
            json.dump(themes, f)
 
    def clear_theme(self, user_id: int | str):
        """Clear (delete) a user's theme"""
        themes = self.user_themes
        with open(f'{os.getcwd()}/data/user_themes.json', 'w') as f:
            del themes[str(user_id)]
            json.dump(themes, f)
 

music_data = MusicData()

