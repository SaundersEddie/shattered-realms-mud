# shattered_realms/mud/server.py

import asyncio
import textwrap
from typing import Optional

from ..game.world import load_world
from ..game.commands import handle_command, cmd_quicklook
from ..game.models import Player
from ..game.npcs import npc_tick
from ..game.colors import colorize   # NEW


WELCOME_BANNER = r"""
========================================
   Shattered Realms MUD  (v0.1.0)
========================================
"""


class ClientSession:
    """
    Represents a single connected client.
    Knows its Player and current room (via Player.room_id).
    """

    # --- Output helpers ---

    def _sanitize(self, text: str) -> str:
        """
        Replace fancy Unicode punctuation with plain ASCII so Windows / old
        telnet clients don't puke out ΓÇö and friends.
        """
        replacements = {
            "—": "--",
            "–": "-",
            "…": "...",
            "’": "'",
            "‘": "'",
            "“": '"',
            "”": '"',
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)
        return text

    def _wrap(self, text: str, width: int = 78) -> str:
        """
        Hard-wrap text to a fixed width, preserving explicit newlines.
        Each input line may turn into multiple output lines.
        """
        lines_out: list[str] = []
        # Preserve explicit line breaks coming from descriptions, etc.
        for raw_line in text.splitlines() or [""]:
            line = raw_line.rstrip("\r")
            if not line:
                lines_out.append("")
                continue
            wrapped = textwrap.wrap(line, width=width)
            if wrapped:
                lines_out.extend(wrapped)
            else:
                lines_out.append("")
        return "\n".join(lines_out)


    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, world):
        self.reader = reader
        self.writer = writer
        self.world = world
        self.player: Optional[Player] = None
        self.color_enabled: bool = True  # NEW

        peer = writer.get_extra_info("peername")
        self.addr: Optional[str] = f"{peer[0]}:{peer[1]}" if peer else "unknown"

    # expose room_id like before so commands don't need to change
    @property
    def room_id(self) -> str:
        if self.player is None:
            return "lobby"
        return self.player.room_id

    @room_id.setter
    def room_id(self, value: str) -> None:
        if self.player is not None:
            self.player.room_id = value

        # --- Role Helpers ---
    def is_admin(self) -> bool:
        return self.player and self.player.role == "admin"

    def is_gm(self) -> bool:
        return self.player and self.player.role in ("gm", "admin")

    def is_wizard(self) -> bool:
        return self.player and self.player.role in ("wizard", "gm", "admin")

    async def send_line(self, text: str = "") -> None:
        """
        Send one logical line (which may be wrapped into several physical lines)
        to the client, with CRLF line endings.
        """
        if text is None:
            text = ""

        # Normalize punctuation and wrap for safer display on Windows terminals.
        safe = self._sanitize(text)
        wrapped = self._wrap(safe)

        # wrapped may contain internal newlines; send each as its own CRLF line.
        for line in wrapped.splitlines() or [""]:
            self.writer.write((line + "\r\n").encode("utf-8", errors="ignore"))

        await self.writer.drain()


    async def _ask_name(self) -> str:
        """
        Ask the player for a name and ensure it's non-empty
        and not already in use.
        """
        while True:
            await self.send_line("By what name are you known in the Shattered Realms?")
            await self.send_line("> ",)  # simple prompt
            line = await self.reader.readline()
            if not line:
                return "Wanderer"

            raw = line.decode("utf-8", errors="ignore").strip()
            # sanitize: keep it simple for now
            name = "".join(ch for ch in raw if ch.isalnum())[:16]

            if not name:
                await self.send_line("That name rings hollow. Try something else.")
                continue

            key = name.lower()
            if key in self.world.players:
                await self.send_line("That name is already in use. Choose another.")
                continue

            return name

    async def handle(self) -> None:
        try:
            # Banner
            await self.send_line(colorize(WELCOME_BANNER.strip("\n"), "banner", self.color_enabled))
            await self.send_line(colorize("You feel a cold wind as the void takes shape around you.", "system", self.color_enabled))
            await self.send_line("")

            # Ask for a name and create Player
            name = await self._ask_name()
            player = Player(name=name, room_id="lobby")
            # Temporary: assign Admin powers to Eddie only
            if name.lower() in ("eddie", "mr_yt", "mryt"):   # choose the ones you want
                player.role = "admin"
            self.player = player
            self.world.add_player(player)
            self.world.add_session(player.name, self)

            name = player.name

            # Notify others already in this room (lobby on login)
            for other in self.world.sessions_in_room(self.room_id):
                if other is self:
                    continue
                colored_name = colorize(name, "player_name", other.color_enabled)
                await other.send_line(f"{colored_name} enters the room.")


            # Now talk to this player
            await self.send_line(f"Welcome, {player.name}.")
            await self.send_line("Type 'look' for full description, 'ql' for brief, 'quit' to leave.")
            await self.send_line("")

            # Initial quick look at current room
            await cmd_quicklook(self, [])

            # Main loop
            while True:
                line = await self.reader.readline()
                if not line:
                    break

                text = line.decode("utf-8", errors="ignore")
                keep_going = await handle_command(self, text)
                if not keep_going:
                    break
        finally:
            # Clean up player on disconnect
            if self.player is not None:
                name = self.player.name

                # Notify others in the same room
                for other in self.world.sessions_in_room(self.room_id):
                    if other is self:
                        continue
                    colored_name = colorize(name, "player_name", other.color_enabled)
                    await other.send_line(f"{colored_name} leaves the room.")


                print(f"{self.player.name} disconnecting from {self.addr}")
                self.world.remove_session(self.player.name)
                self.world.remove_player(self.player.name)

            self.writer.close()
            await self.writer.wait_closed()
            
        def is_admin(self) -> bool:
            return self.player and self.player.role == "admin"

        def is_gm(self) -> bool:
            return self.player and self.player.role in ("gm", "admin")

        def is_wizard(self) -> bool:
            return self.player and self.player.role in ("wizard", "gm", "admin")


async def run_server(host: str = "0.0.0.0", port: int = 4000) -> None:
    world = load_world()

    async def _client_connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        session = ClientSession(reader, writer, world)
        await session.handle()

    # Background NPC loop
    async def _npc_loop():
        while True:
            try:
                await npc_tick(world)
            except Exception as e:
                print(f"[NPC LOOP ERROR]: {e}")
            await asyncio.sleep(10)  # move every 10s for now

    asyncio.create_task(_npc_loop())

    server = await asyncio.start_server(_client_connected, host, port)

    sockets = ", ".join(str(sock.getsockname()) for sock in (server.sockets or []))
    print(f"Shattered Realms listening on {sockets} (connect via nc/telnet)")


    async with server:
        await server.serve_forever()

