# shattered_realms/game/wizcommands.py

from typing import Dict, Callable, List

from .colors import colorize

CommandHandler = Callable[[object, List[str]], object]

# Wizard-only commands will go here (home, summon, etc.).
# For now we keep the dict empty so wiring is easy.

WIZ_COMMANDS: Dict[str, CommandHandler] = {
    # "home": cmd_home,
}
