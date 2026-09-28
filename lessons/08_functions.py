# Lesson 8: Functions - make your own commands
#
# def creates a new command (a FUNCTION).
# The indented lines are the recipe. Nothing happens until you CALL it.

def say_hello():
    print("Hello!")
    print("How are you today?")

say_hello()
say_hello()

# Functions can take INPUTS (called parameters):
def greet(name):
    print("Hi", name + ", welcome to Python!")

greet("Will")
greet("Mum")

# Functions can give back an ANSWER with return:
def double(number):
    return number * 2

print(double(21))
big = double(double(double(1)))
print(big)

# 🧩 CHALLENGE
# 1. Write  def square(n):  that returns n * n. Print square(9).
# 2. Write  def shout(word):  that prints the word in CAPITALS 3 times.
#    Hint: "hello".upper() gives "HELLO"
