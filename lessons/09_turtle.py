# Lesson 9: Drawing with a turtle 🐢
#
# The turtle is a little pen that walks around a new window.
#   forward(100)  walk 100 steps     left(90) / right(90)  turn
#   color("red")  change pen colour  penup() / pendown()   lift or drop the pen

import turtle

t = turtle.Turtle()
t.shape("turtle")
t.speed(5)          # 1 = slow ... 10 = fast, 0 = super fast

# A square: 4 sides, turn 90 degrees each time
t.color("blue")
for side in range(4):
    t.forward(100)
    t.left(90)

# Move somewhere else without drawing
t.penup()
t.goto(-150, 0)
t.pendown()

# A colourful star
colours = ["red", "orange", "green", "purple", "gold"]
for i in range(5):
    t.color(colours[i])
    t.forward(120)
    t.right(144)

turtle.done()       # keep the window open (close it to finish)

# 🧩 CHALLENGE
# 1. Draw a triangle (3 sides, turn 120).
# 2. Draw a hexagon (6 sides - what angle?  360 / 6).
# 3. Put the square inside a loop that turns a little each time:
#       for i in range(36): ...square...  then  t.right(10)
