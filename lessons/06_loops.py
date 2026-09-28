# Lesson 6: Loops - doing things again and again
#
# for ... in range(N)  repeats the indented lines N times.
# The variable (here: i) counts 0, 1, 2, ... up to N-1.

for i in range(5):
    print("Hip hip hooray!", i)

print()   # an empty line

# range(start, stop) - stop is NOT included
for n in range(1, 11):
    print("7 x", n, "=", 7 * n)

print()

# while keeps going as long as something is True
countdown = 5
while countdown > 0:
    print(countdown, "...")
    countdown = countdown - 1
print("🚀 Blast off!")

# 🧩 CHALLENGE
# 1. Print the 12 times table.
# 2. Print a triangle of stars:   *   **   ***   ****  ...
#    Hint: "*" * 3  gives  "***"
# 3. Count down from 100 in steps of 10.
