import random

WORDS = (
    "tiger", "lamp", "cloud", "brick", "river", "frog", "pencil", "drum",
    "apple", "bridge", "candle", "arrow", "barrel", "garden", "hammer",
    "island", "jacket", "kettle", "ladder", "marble", "needle", "orange",
    "pillow", "quilt", "rocket", "saddle", "table", "umbrella", "violin",
    "wagon", "anchor", "basket", "castle", "desert", "engine", "forest",
    "gravel", "harbor", "igloo", "jungle", "kite", "lemon", "mirror",
    "ocean", "pebble", "rabbit", "stone", "turtle", "valley", "window",
    "copper", "diamond", "falcon", "glacier", "honey", "insect", "jewel",
    "kitten", "lantern", "magnet", "napkin", "oyster", "parrot", "quartz",
    "ripple", "signal", "timber", "vapor", "walnut", "almond", "bamboo",
    "canvas", "donkey", "eagle", "feather", "helmet", "jasper", "lotus",
    "mango", "olive", "panther", "robin", "salmon", "tulip", "urchin",
    "viper", "willow", "yarn", "banana", "cobalt", "dagger", "ember",
    "ferret", "goblin", "heron", "inkpot", "jigsaw", "kernel", "lizard",
    "mosaic", "noodle", "pepper",
)


def mint_password() -> str:
    w1 = random.choice(WORDS)
    w2 = random.choice(WORDS)
    nn = random.randint(10, 99)
    return f"{w1}-{w2}-{nn}"
