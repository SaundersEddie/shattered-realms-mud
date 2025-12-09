# shattered_realms/game/admincommands.py

from typing import Dict, Callable, List

from .colors import colorize

CommandHandler = Callable[[object, List[str]], object]


async def cmd_setrole(session, args: List[str]) -> None:
    """Admin command: setrole <player> <role>"""
    if not session.is_admin():
        msg = colorize("You lack the authority to reshape destiny.", "error", session.color_enabled)
        await session.send_line(msg)
        return

    if len(args) != 2:
        await session.send_line("Usage: setrole <name> <role>")
        return

    target_name, new_role = args
    new_role = new_role.lower()

    if new_role not in ("player", "wizard", "gm", "admin"):
        await session.send_line("Invalid role. Choose: player, wizard, gm, admin.")
        return

    key = target_name.lower()
    target = session.world.players.get(key)
    if not target:
        await session.send_line(f"No such player: {target_name}")
        return

    target.role = new_role
    await session.send_line(f"Role of {target_name} set to {new_role}.")


async def cmd_addxp(session, args: List[str]) -> None:
    """Admin: add XP to yourself. Usage: addxp <amount>"""
    from .levels import apply_level_up  # local import to avoid circular imports

    if not session.is_admin():
        await session.send_line(colorize("No.", "error", session.color_enabled))
        return

    if not args:
        await session.send_line("Usage: addxp <amount>")
        return

    try:
        amount = int(args[0])
    except ValueError:
        await session.send_line("XP must be a number.")
        return

    player = session.player
    player.xp += amount
    apply_level_up(player)

    msg = f"Gave {amount} XP. You are now level {player.level}."
    await session.send_line(colorize(msg, "system", session.color_enabled))


async def cmd_killnpc(session, args: List[str]) -> None:
    """
    Admin-only: remove an NPC from the world.
    Usage: killnpc <id-or-name-prefix>
    """
    if not session.is_admin():
        msg = colorize("Only a true Admin can rewrite legends.", "error", session.color_enabled)
        await session.send_line(msg)
        return

    if not args:
        await session.send_line("Usage: killnpc <id-or-name-prefix>")
        return

    target_arg = " ".join(args).lower()
    world = session.world
    target_npc = None

    # Try by id
    if target_arg in world.npcs:
        target_npc = world.npcs[target_arg]
    else:
        # Fallback: prefix match on name
        for npc in world.npcs.values():
            if npc.name.lower().startswith(target_arg):
                target_npc = npc
                break

    if not target_npc:
        await session.send_line(f"No NPC found matching '{target_arg}'.")
        return

    room_id = target_npc.room_id
    name_c = colorize(target_npc.name, "npc_name", session.color_enabled)

    for other in world.sessions_in_room(room_id):
        await other.send_line(f"{name_c} flickers and vanishes from the realm.")

    world.npcs.pop(target_npc.id, None)

    await session.send_line(f"{target_npc.name} has been removed from the Shattered Realms.")


ADMIN_COMMANDS: Dict[str, CommandHandler] = {
    "setrole": cmd_setrole,
    "addxp": cmd_addxp,
    "killnpc": cmd_killnpc,
}
