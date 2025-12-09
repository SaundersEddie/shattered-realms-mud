# shattered_realms/game/commands.py

from typing import Dict, Callable, List

from .models import World, Room
from .colors import colorize
from .admincommands import ADMIN_COMMANDS
from .wizcommands import WIZ_COMMANDS

CommandHandler = Callable[[object, List[str]], object]

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

# Player Commands

async def cmd_look(session, args: List[str]) -> None:
    """Full room description or 'look <target>'."""
    # If there's a target, delegate to _look_target
    if args:
        target = " ".join(args)
        await _look_target(session, target)
        return

    # Normal room look
    room = _current_room(session)

    room_name = colorize(room.name, "room_name", session.color_enabled)
    await session.send_line(room_name)
    await session.send_line(room.description.rstrip())

    await _show_room_occupants(session)

    # Pretty exit formatting
    for line in format_exits(session, room):
        await session.send_line(line)

async def cmd_quicklook(session, args: List[str]) -> None:
    """Brief room description (`ql`)."""
    room = _current_room(session)

    room_name = colorize(room.name, "room_name", session.color_enabled)
    await session.send_line(room_name)
    await session.send_line(room.brief.rstrip())

    await _show_room_occupants(session)

    # Pretty exit formatting
    for line in format_exits(session, room):
        await session.send_line(line)

async def cmd_move(session, args: List[str], direction: str) -> None:
    """Move the player in a direction, if possible."""
    room = _current_room(session)
    exits = room.exits or {}

    if direction not in exits:
        msg = colorize("You can't go that way.", "error", session.color_enabled)
        await session.send_line(msg)
        return

    dest_id = exits[direction]

    # Make sure the destination room actually exists.
    try:
        session.world.get_room(dest_id)
    except KeyError:
        msg = colorize(
            "You feel resistance, as if reality hasn't fully formed that way.",
            "error",
            session.color_enabled,
        )
        await session.send_line(msg)
        return

    name = session.player.name if session.player else "Someone"

    # Notify old room
    for other in session.world.sessions_in_room(session.room_id):
        if other is session:
            continue
        colored_name = colorize(name, "player_name", other.color_enabled)
        await other.send_line(f"{colored_name} leaves the room.")

    # Actually move
    session.room_id = dest_id

    # Notify new room
    for other in session.world.sessions_in_room(session.room_id):
        if other is session:
            continue
        colored_name = colorize(name, "player_name", other.color_enabled)
        await other.send_line(f"{colored_name} enters the room.")

    move_text = colorize(f"You go {direction}.", "system", session.color_enabled)
    await session.send_line(move_text)
    await cmd_quicklook(session, [])

async def cmd_quit(session, args: List[str]) -> bool:
    """Quit the game. Returns False to signal disconnect."""
    msg = colorize("The world fades to black as you step away...", "system", session.color_enabled)
    await session.send_line(msg)
    return False

        
async def cmd_say(session, args: List[str]) -> None:
    """Speak to everyone in the same room."""
    if not args:
        msg = colorize("Say what?", "error", session.color_enabled)
        await session.send_line(msg)
        return

    msg_text = " ".join(args)
    name = session.player.name if session.player else "Someone"

    for other in session.world.sessions_in_room(session.room_id):
        if other is session:
            you_line = colorize("You say:", "system", session.color_enabled)
            await other.send_line(f"{you_line} {msg_text}")
        else:
            colored_name = colorize(name, "player_name", other.color_enabled)
            await other.send_line(f"{colored_name} says: {msg_text}")

async def cmd_who(session, args: List[str]) -> None:
    """Show who is online."""
    players = list(session.world.players.values())
    if not players:
        msg = colorize("You seem to be alone in these realms.", "system", session.color_enabled)
        await session.send_line(msg)
        return

    header = colorize("Players currently wandering the Shattered Realms:", "system", session.color_enabled)
    await session.send_line(header)
    for p in players:
        pname = colorize(p.name, "player_name", session.color_enabled)
        await session.send_line(f"  {pname}")

async def cmd_color(session, args: List[str]) -> None:
    # No args: just show current status
    if not args:
        status = "on" if session.color_enabled else "off"
        msg = f"Color is currently {status}."
        msg = colorize(msg, "system", session.color_enabled)
        await session.send_line(msg)
        return

    choice = args[0].lower()

    if choice in ("on", "yes", "true"):
        session.color_enabled = True
        # Use the *new* state when colorizing
        msg = colorize("Color has been turned on.", "system", session.color_enabled)
        await session.send_line(msg)
    elif choice in ("off", "no", "false"):
        # Turn it off first, then send plain confirmation
        session.color_enabled = False
        # Don't color this, since color is now off
        await session.send_line("Color has been turned off.")
    else:
        # Invalid usage
        msg = colorize("Usage: color [on|off]", "error", session.color_enabled)
        await session.send_line(msg)

async def cmd_stats(session, args):
    """Show your HP, stamina, level, and XP."""
    p = session.player
    lines = [
        f"Name: {p.name}",
        f"Level: {p.level}",
        f"XP: {p.xp} / {LEVEL_XP.get(p.level+1, 'MAX')}",
        f"Health: {p.hp} / {p.max_hp}",
        f"Stamina: {p.stamina} / {p.max_stamina}",
    ]
    for line in lines:
        await session.send_line(colorize(line, "system", session.color_enabled))

async def cmd_role(session, args: List[str]) -> None:
    """Show your current role."""
    role = session.player.role if session.player else "unknown"
    msg = colorize(f"Your role is: {role}", "system", session.color_enabled)
    await session.send_line(msg)

# End Player Commands

# Helper Functions

def _current_room(session) -> Room:
    return session.world.get_room(session.room_id)

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
        colored = [
            colorize(name, "player_name", session.color_enabled)
            for name in other_players
        ]
        names = ", ".join(colored)
        await session.send_line(f"Also here: {names}")

    # NPCs
    npcs = session.world.npcs_in_room(session.room_id)
    if npcs:
        await session.send_line(colorize("You notice:", "system", session.color_enabled))
        for npc in npcs:
            name_c = colorize(npc.name, "npc_name", session.color_enabled)
            if getattr(npc, "description", None):
                await session.send_line(f"  {name_c}, {npc.description}")
            else:
                await session.send_line(f"  {name_c}")

async def _look_target(session, target: str) -> None:
    """
    Handle 'look <target>' for NPCs and players in the current room.
    """
    target_l = target.lower().strip()
    if not target_l:
        await cmd_look(session, [])
        return

    room_id = session.room_id

    # 1) Check NPCs in the room
    npcs = session.world.npcs_in_room(room_id)
    for npc in npcs:
        if npc.name.lower().startswith(target_l):
            name_c = colorize(npc.name, "npc_name", session.color_enabled)
            await session.send_line(name_c)
            if getattr(npc, "description", None):
                await session.send_line(npc.description)
            # Optional: show basic stats if present
            if hasattr(npc, "level") or hasattr(npc, "hp"):
                parts = []
                if hasattr(npc, "level"):
                    parts.append(f"Level {getattr(npc, 'level')}")
                if hasattr(npc, "hp") and hasattr(npc, "max_hp"):
                    parts.append(f"Health: {npc.hp}/{npc.max_hp}")
                if parts:
                    await session.send_line(colorize("  " + " | ".join(parts), "system", session.color_enabled))
            return

    # 2) Check other players in the room
    for other in session.world.sessions_in_room(room_id):
        if other is session:
            continue
        if not other.player:
            continue
        if other.player.name.lower().startswith(target_l):
            pname_c = colorize(other.player.name, "player_name", session.color_enabled)
            await session.send_line(pname_c)
            # Simple player info for now
            p = other.player
            line = f"Level {p.level} {p.role}"
            await session.send_line(colorize(line, "system", session.color_enabled))
            return

    # If nothing matched
    msg = colorize("You don't see that here.", "error", session.color_enabled)
    await session.send_line(msg)

def format_exits(session, room: Room) -> List[str]:
    """
    Returns a list of lines showing exits in a nice formatted way:
        Exits:
          East -> Dusty Antechamber
    """
    if not room.exits:
        return [colorize("Exits: none", "system", session.color_enabled)]

    lines = [colorize("Exits:", "system", session.color_enabled)]

    for direction in sorted(room.exits.keys()):
        dest_id = room.exits[direction]
        try:
            dest_room = session.world.get_room(dest_id)
            dest_name = dest_room.name
        except KeyError:
            dest_name = "(unknown)"

        dir_c = colorize(direction.capitalize(), "player_name", session.color_enabled)
        name_c = colorize(dest_name, "room_name", session.color_enabled)

        lines.append(f"  {dir_c} -> {name_c}")

    return lines

# End Helper Functions

# Command dispatch table
# Handlers return:
#   - True / None  => keep connection open
#   - False        => server will close connection
CommandHandler = Callable[[object, List[str]], object]

BASE_COMMANDS: Dict[str, CommandHandler] = {
    "look": cmd_look,
    "ql": cmd_quicklook,
    "quit": cmd_quit,
    "exit": cmd_quit,
    "say": cmd_say,
    "who": cmd_who,
    "color": cmd_color,
    "stats": cmd_stats,
    "role": cmd_role,
}
COMMANDS: Dict[str, CommandHandler] = {
    **BASE_COMMANDS,
    **WIZ_COMMANDS,
    **ADMIN_COMMANDS,
}


async def handle_command(session, line: str) -> bool:
    """
    Parse and execute a command line for a given session.

    Returns False if the caller should close the connection.
    """
    text = line.strip()

    # Empty line: treat as quick look
    if not text:
        await cmd_quicklook(session, [])
        return True

    parts = text.split()
    if not parts:
        await cmd_quicklook(session, [])
        return True

    verb = parts[0].lower()
    args = parts[1:]

    # Direction shortcuts (n/s/e/w/u/d)
    if verb in DIRECTION_ALIASES:
        verb = DIRECTION_ALIASES[verb]

    # Cardinal directions as movement commands
    if verb in VALID_DIRECTIONS:
        await cmd_move(session, args, verb)
        return True

    # Normal command lookup
    handler = COMMANDS.get(verb)
    if handler is None:
        msg = colorize("You mutter something unintelligible.", "error", session.color_enabled)
        await session.send_line(msg)
        return True

    result = await handler(session, args)
    if isinstance(result, bool):
        return result

    return True
