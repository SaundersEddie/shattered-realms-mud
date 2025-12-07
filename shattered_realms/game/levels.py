# XP required to *reach* that level.
# Level 1 = starting point (0 XP).
LEVEL_XP = {
    1: 0,
    2: 100,
    3: 250,
    4: 450,
    5: 700,
    6: 1000,
    7: 1400,
    8: 1850,
    9: 2350,
    10: 2900,
    11: 3500,
    12: 4150,
    13: 4850,
    14: 5600,
    15: 6400,
    16: 7250,
    17: 8150,
    18: 9100,
    19: 10100,
    20: 11200,
    21: 12400,
    22: 13700,
    23: 15100,
    24: 16600,
    25: 18200,
    26: 19900,
    27: 21700,
    28: 23600,
    29: 25600,
    30: 27700,
}

MAX_LEVEL = 30


def can_level_up(player) -> bool:
    """
    Returns True if the player's XP qualifies them for a level-up.
    """
    if player.level >= MAX_LEVEL:
        return False
    next_level = player.level + 1
    return player.xp >= LEVEL_XP[next_level]


def apply_level_up(player):
    """
    Actually increases player level and upgrades stats.
    Called repeatedly until the player reaches appropriate level.
    """
    while can_level_up(player):
        player.level += 1

        # Stat growth curve — tweak as needed
        player.max_hp += 5
        player.hp = player.max_hp  # heal on level-up

        player.max_stamina += 2
        player.stamina = player.max_stamina

        # Narrative puff
        print(f"{player.name} has advanced to level {player.level}!")
