# Lesson 5: Making decisions with if
#
# if checks whether something is True.
# The lines UNDER it are pushed in by 4 spaces - they only run if it's True.
# Don't forget the colon  :  at the end of the if line!
#
#   ==  equal to        !=  not equal to
#   <   less than       >   greater than
#   <=  less or equal   >=  greater or equal

age = int(input("How old are you? "))

if age >= 13:
    print("You're a teenager (or older)!")
elif age >= 10:
    print("Double digits! Nice.")
else:
    print("Still single digits. Cool!")

answer = input("What is 7 x 8? ")
if answer == "56":
    print("✅ Correct! You're a maths star.")
else:
    print("❌ Not quite. It's 56.")

# 🧩 CHALLENGE
# 1. Ask "Do you like pizza?" and answer differently for "yes" and "no".
# 2. Make a password checker: only print "Welcome!" if the password is right.
