# Lesson 7: Lists - lots of things in one box
#
# A list goes in [square brackets], with commas between the items.
# Positions start counting at 0!

animals = ["cat", "dog", "panda", "shark"]

print(animals)
print("The first animal is", animals[0])
print("The last animal is", animals[-1])
print("I know", len(animals), "animals")

animals.append("dragon")          # add to the end
print(animals)

# Loop over every item in a list:
for animal in animals:
    print("I like the", animal)

# Pick something at random:
import random
print("Today's lucky animal is the", random.choice(animals))

# 🧩 CHALLENGE
# 1. Make a list of your 5 favourite games and print each one.
# 2. Make a "magic 8 ball": a list of answers, ask a question with input(),
#    then print a random answer.
