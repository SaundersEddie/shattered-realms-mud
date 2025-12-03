# shattered_realms/game/models.py

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Room:
    id: str
    name: str
    description: str
    brief: str
    exits: Dict[str, str] = field(default_factory=dict)


@dataclass
class Player:
    name: str
    room_id: str
    is_admin: bool = False  # future-proofing


class World:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        # key = lowercase name
        self.players: Dict[str, Player] = {}
        # active connections: key = lowercase player name, value = session object
        self.sessions: Dict[str, object] = {}

    # ---- Rooms ----
    def add_room(self, room: Room) -> None:
        self.rooms[room.id] = room

    def get_room(self, room_id: str) -> Room:
        if room_id not in self.rooms:
            raise KeyError(f"Unknown room id: {room_id}")
        return self.rooms[room_id]

    # ---- Players ----
    def add_player(self, player: Player) -> None:
        key = player.name.lower()
        self.players[key] = player

    def remove_player(self, name: str) -> None:
        key = name.lower()
        self.players.pop(key, None)

    def get_player(self, name: str) -> Player:
        key = name.lower()
        return self.players[key]

    def players_in_room(self, room_id: str) -> List[Player]:
        return [p for p in self.players.values() if p.room_id == room_id]

    # ---- Sessions ----
    def add_session(self, name: str, session: object) -> None:
        key = name.lower()
        self.sessions[key] = session

    def remove_session(self, name: str) -> None:
        key = name.lower()
        self.sessions.pop(key, None)

    def sessions_in_room(self, room_id: str) -> List[object]:
        return [
            s for s in self.sessions.values()
            if getattr(s, "room_id", None) == room_id
        ]
