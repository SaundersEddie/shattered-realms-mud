# shattered_realms/game/world.py

from pathlib import Path
import yaml

from .models import World, Room


def load_world() -> World:
    """
    Load the world from data/rooms.yml.
    """
    # .../shattered_realms/game/world.py -> .../shattered_realms/
    base_dir = Path(__file__).resolve().parent.parent
    rooms_path = base_dir / "data" / "rooms.yml"

    with rooms_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    world = World()

    for room_id, data in raw.get("rooms", {}).items():
        room = Room(
            id=room_id,
            name=data.get("name", room_id),
            description=data.get("description", ""),
            brief=data.get("brief", data.get("name", room_id)),
            exits=data.get("exits", {}) or {},
        )
        world.add_room(room)

    return world
