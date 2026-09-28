# Lesson 10: Your first game - Guess the Number!
#
# This uses EVERYTHING so far: variables, input, if, loops and random.
# Read it slowly, play it, then make it your own.

import random

secret = random.randint(1, 100)     # a random whole number from 1 to 100
tries = 0

print("I'm thinking of a number between 1 and 100.")

while True:
    guess = int(input("Your guess: "))
    tries = tries + 1

    if guess < secret:
        print("⬆️  Too low!")
    elif guess > secret:
        print("⬇️  Too high!")
    else:
        print("🎉 You got it in", tries, "tries!")
        break                       # break jumps out of the loop

# 🧩 CHALLENGE
# 1. Only allow 7 tries. If they run out, tell them the secret number.
# 2. Ask "Play again?" at the end and start over if they say yes.
# 3. Make it 1 to 1000. How many tries do you need now?
