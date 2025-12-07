# shattered_realms/game/npcs.py

import random
from pathlib import Path
from typing import Dict

import yaml

from .models import World, NPC
from .colors import colorize

def load_npcs(world: World) -> None:
    """
    Load NPC definitions from data/npcs.yml into the world.
    """
    base_dir = Path(__file__).resolve().parent.parent
    npc_path = base_dir / "data" / "npcs.yml"

    if not npc_path.exists():
        # No NPCs defined yet; that's fine.
        return

    with npc_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    for npc_id, data in raw.get("npcs", {}).items():
        room_id = data.get("room")
        if not room_id:
            continue  # must have a starting room

        npc = NPC(
            id=npc_id,
            name=data.get("name", npc_id),
            description=data.get("description", ""),
            room_id=room_id,
            home_id=data.get("home", room_id),
            tethered=bool(data.get("tethered", False)),
            wander_mode=data.get("wander_mode", "none"),
            wander_path=data.get("wander_path", []) or [],
            aggro=int(data.get("aggro", 0)),
        )
        world.add_npc(npc)


async def npc_tick(world: World) -> None:
    """
    Advance NPC behavior one 'tick':
    - Move roaming NPCs (path / global).
    """
    from .models import Room  # avoid circular hints

    # Work on a snapshot so we don't break if the dict changes mid-loop
    npcs: Dict[str, NPC] = dict(world.npcs)

    for npc in npcs.values():
        # Tethered NPCs don't move
        if npc.tethered:
            continue

        # No wander behavior
        mode = (npc.wander_mode or "none").lower()
        if mode == "none":
            continue

        if mode == "path":
            await _npc_move_along_path(world, npc)
        elif mode == "global":
            await _npc_move_global(world, npc)
        # other modes (radius, faction) can be added later


async def _npc_move_along_path(world: World, npc: NPC) -> None:
    if not npc.wander_path:
        return

    # Ensure index is valid
    if npc.wander_index >= len(npc.wander_path):
        npc.wander_index = 0

    dest_id = npc.wander_path[npc.wander_index]
    npc.wander_index = (npc.wander_index + 1) % len(npc.wander_path)

    await _move_npc_to(world, npc, dest_id)


async def _npc_move_global(world: World, npc: NPC) -> None:
    try:
        room = world.get_room(npc.room_id)
    except KeyError:
        return

    if not room.exits:
        return

    dest_id = random.choice(list(room.exits.values()))
    await _move_npc_to(world, npc, dest_id)


async def _move_npc_to(world: World, npc: NPC, dest_id: str) -> None:
    if dest_id == npc.room_id:
        return

    # Verify destination exists
    try:
        world.get_room(dest_id)
    except KeyError:
        return

    old_room_id = npc.room_id
    name = npc.name

    # Notify old room sessions
    for session in world.sessions_in_room(old_room_id):
        colored_name = colorize(name, "npc_name", session.color_enabled)
        await session.send_line(f"{colored_name} leaves the room.")

    npc.room_id = dest_id

    # Notify new room sessions
    for session in world.sessions_in_room(npc.room_id):
        colored_name = colorize(name, "npc_name", session.color_enabled)
        await session.send_line(f"{colored_name} enters the room.")

