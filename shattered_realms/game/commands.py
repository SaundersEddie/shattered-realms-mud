# shattered_realms/game/commands.py

from typing import Dict, Callable, List

from .models import World, Room, NPC

# Directions & aliases
DIRECTION_ALIASES = {
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
    "u": "up",
    "d": "down",
}

VALID_DIRECTIONS = {"north", "south", "east", "west", "up", "down"}


# Session is anything with: world, room_id, send_line(str)
def _current_room(session) -> Room:
    return session.world.get_room(session.room_id)


async def cmd_look(session, args: List[str]) -> None:
    """Full room description."""
    room = _current_room(session)

    await session.send_line(room.name)
    await session.send_line(room.description.rstrip())

    # NEW: show other players
    await _show_room_occupants(session)

    exits = ", ".join(sorted(room.exits.keys())) if room.exits else "none"
    await session.send_line(f"Exits: {exits}")

async def _show_room_occupants(session) -> None:
    """
    Show other players and NPCs in the same room.
    """
    # Players (other than you)
    other_players = []
    for other in session.world.sessions_in_room(session.room_id):
        if other is session:
            continue
        if other.player is None:
            continue
        other_players.append(other.player.name)

    if other_players:
        names = ", ".join(other_players)
        await session.send_line(f"Also here: {names}")

    # NPCs
    npcs = [n.name for n in session.world.npcs_in_room(session.room_id)]
    if npcs:
        names = ", ".join(npcs)
        await session.send_line(f"You notice: {names}")

async def cmd_quicklook(session, args: List[str]) -> None:
    """Brief room description (`ql`)."""
    room = _current_room(session)

    await session.send_line(room.name)
    await session.send_line(room.brief.rstrip())

    # NEW: show other players
    await _show_room_occupants(session)

    exits = ", ".join(sorted(room.exits.keys())) if room.exits else "none"
    await session.send_line(f"Exits: {exits}")

async def cmd_move(session, args: List[str], direction: str) -> None:
    """Move the player in a direction, if possible."""
    room = _current_room(session)
    exits = room.exits

    if direction not in exits:
        await session.send_line("You can't go that way.")
        return

    dest_id = exits[direction]

    # Make sure destination room actually exists
    try:
        session.world.get_room(dest_id)
    except KeyError:
        await session.send_line("You feel resistance, as if reality hasn't fully formed that way.")
        return

    name = session.player.name if session.player else "Someone"

    # Notify old room
    for other in session.world.sessions_in_room(session.room_id):
        if other is session:
            continue
        await other.send_line(f"{name} leaves the room.")

    # Move
    session.room_id = dest_id

    # Notify new room
    for other in session.world.sessions_in_room(session.room_id):
        if other is session:
            continue
        await other.send_line(f"{name} enters the room.")

    await session.send_line(f"You go {direction}.")
    await cmd_quicklook(session, [])



async def cmd_quit(session, args: List[str]) -> bool:
    """Quit the game. Returns False to signal disconnect."""
    await session.send_line("The world fades to black as you step away...")
    return False

async def cmd_who(session, args: List[str]) -> None:
    """Show who is online."""
    players = list(session.world.players.values())
    if not players:
        await session.send_line("You seem to be alone in these realms.")
        return

    await session.send_line("Players currently wandering the Shattered Realms:")
    for p in players:
        await session.send_line(f"  {p.name}")
        
async def cmd_say(session, args: List[str]) -> None:
    """Speak to everyone in the same room."""
    if not args:
        await session.send_line("Say what?")
        return

    msg = " ".join(args)
    name = session.player.name if session.player else "Someone"

    # Send to everyone in the same room
    for other in session.world.sessions_in_room(session.room_id):
        if other is session:
            await other.send_line(f"You say: {msg}")
        else:
            await other.send_line(f"{name} says: {msg}")
            
# Command dispatch table
# Handlers return:
#   - True / None  => keep connection open
#   - False        => server will close connection
CommandHandler = Callable[[object, List[str]], object]

COMMANDS: Dict[str, CommandHandler] = {
    "look": cmd_look,
    "ql": cmd_quicklook,
    "quit": cmd_quit,
    "exit": cmd_quit,
    "say": cmd_say,
    "who": cmd_who,
}

async def handle_command(session, line: str) -> bool:
    """
    Parse and execute a command line for a given session.

    Returns False if the caller should close the connection.
    """
    text = line.strip()
    if not text:
        # treat empty as quick look
        await cmd_quicklook(session, [])
        return True

    parts = text.split()
    verb = parts[0].lower()
    args = parts[1:]

    # Direction shortcuts
    if verb in DIRECTION_ALIASES:
        verb = DIRECTION_ALIASES[verb]

    if verb in VALID_DIRECTIONS:
        await cmd_move(session, args, verb)
        return True

    handler = COMMANDS.get(verb)
    if not handler:
        await session.send_line("You mutter something unintelligible.")
        return True

    result = await handler(session, args)
    if isinstance(result, bool):
        return result
    return True



