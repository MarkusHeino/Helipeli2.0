import random

def dice_game2():
    dice1 = random.randint(1, 6)
    dice2 = random.randint(1, 6)
    if dice1 == dice2:
        result = 'Won'
    else:
        result = 'Lost'
    return result


def coinflip2(guess):
    result = random.choice(["H", "T"])
    if guess == result:
        result = "Won"
    else:
        result = "Lost"
    return result