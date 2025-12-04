from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Room:
    id: str
    name: str
    description: str
    brief: str
    exits: Dict[str, str] = field(default_factory=dict)
    sanctuary: bool = False  # rooms can be marked as safe zones


@dataclass
class Player:
    name: str
    room_id: str
    is_admin: bool = False  # future-proofing


@dataclass
class NPC:
    id: str
    name: str
    description: str
    room_id: str
    home_id: str
    tethered: bool = False
    wander_mode: str = "none"  # "none", "path", "global"
    wander_path: List[str] = field(default_factory=list)
    wander_index: int = 0
    aggro: int = 0  # 0–10: 0 = passive, 10 = murderhobo


class World:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        # key = lowercase name
        self.players: Dict[str, Player] = {}
        # active connections: key = lowercase player name, value = session object
        self.sessions: Dict[str, object] = {}
        # NPCs keyed by id
        self.npcs: Dict[str, NPC] = {}

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

    # ---- NPCs ----
    def add_npc(self, npc: NPC) -> None:
        self.npcs[npc.id] = npc

    def npcs_in_room(self, room_id: str) -> List[NPC]:
        return [n for n in self.npcs.values() if n.room_id == room_id]
