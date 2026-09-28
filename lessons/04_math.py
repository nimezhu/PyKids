# Lesson 4: Python is a super calculator
#
#   +  add        -  subtract
#   *  multiply   /  divide
#   ** power      %  remainder (what's left over)

print(3 + 4)
print(10 - 7)
print(6 * 7)
print(20 / 4)
print(2 ** 10)        # 2 x 2 x 2 ... ten times
print(17 % 5)         # 17 = 5 + 5 + 5 + 2, so the remainder is 2

# Numbers from input() come in as TEXT. Use int() to turn them into numbers.
a = int(input("Give me a number: "))
b = int(input("Give me another number: "))
print(a, "+", b, "=", a + b)
print(a, "x", b, "=", a * b)

# 🧩 CHALLENGE
# 1. How many seconds are in a day? Make Python work it out.
# 2. Ask for someone's age and print how many MONTHS old they are.
# 3. Remove int( ) around input and see what happens to  a + b.  Why?
