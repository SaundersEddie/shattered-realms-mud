# shattered_realms/game/colors.py

RESET = "\033[0m"

STYLES = {
    "room_name": "\033[1;36m",    # bright cyan
    "npc_name": "\033[1;33m",     # bright yellow
    "player_name": "\033[1;32m",  # bright green
    "system": "\033[0;32m",       # green
    "error": "\033[0;31m",        # red
    "banner": "\033[1;35m",       # bright magenta
}

def colorize(text: str, style: str, enabled: bool = True) -> str:
    if not enabled:
        return text

    code = STYLES.get(style)
    if not code:
        return text
    return f"{code}{text}{RESET}"
