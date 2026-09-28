# Lesson 11: A real game - Hungry Turtle 🐢🍓
#
# Steer with the ARROW KEYS and eat the red food.
# Every bite makes you faster. Don't hit the walls!
#
# Two new tricks make games work:
#   screen.onkeypress(go_up, "Up")   when the Up key is pressed, run go_up
#   screen.ontimer(game_loop, 30)    in 30 milliseconds, run game_loop
# A function that sets a timer for ITSELF runs again and again, forever.
# That's a GAME LOOP.
# (No window? Play in the web page - on a phone it has arrow buttons.)

import random
import turtle

screen = turtle.Screen()
screen.bgcolor("honeydew")
screen.tracer(0)                # draw only when we say screen.update()

# The walls: a box around the edge
walls = turtle.Turtle()
walls.hideturtle()
walls.penup()
walls.goto(-380, -280)
walls.pendown()
walls.pensize(4)
for side in range(2):
    walls.forward(760)
    walls.left(90)
    walls.forward(560)
    walls.left(90)

player = turtle.Turtle(shape="turtle")
player.color("darkgreen")
player.penup()

food = turtle.Turtle(shape="circle")
food.color("red")
food.penup()

pen = turtle.Turtle()           # this one only writes words
pen.hideturtle()
pen.penup()

score = 0
speed = 3


def show_score():
    pen.clear()
    pen.goto(0, 240)
    pen.write("Score: " + str(score), align="center", font=("Arial", 20, "bold"))


def move_food():
    food.goto(random.randint(-350, 350), random.randint(-250, 200))


# One function per arrow key: turn the turtle that way
def go_up():
    player.setheading(90)

def go_down():
    player.setheading(270)

def go_left():
    player.setheading(180)

def go_right():
    player.setheading(0)

screen.onkeypress(go_up, "Up")
screen.onkeypress(go_down, "Down")
screen.onkeypress(go_left, "Left")
screen.onkeypress(go_right, "Right")
screen.listen()                 # start listening for keys (don't forget this!)


def game_loop():
    global score, speed         # we change these, so use the ones from up top
    player.forward(speed)

    if player.distance(food) < 20:          # close enough to eat it
        score = score + 1
        speed = speed + 1
        show_score()
        move_food()

    x = player.xcor()
    y = player.ycor()
    if x < -370 or x > 370 or y < -270 or y > 270:
        pen.goto(0, 0)
        pen.write("GAME OVER", align="center", font=("Arial", 36, "bold"))
        screen.update()
        return                  # no new timer, so the game loop stops

    screen.update()
    screen.ontimer(game_loop, 30)           # run me again in 30 ms


show_score()
move_food()
game_loop()
turtle.done()                   # keep going until you stop it (Ctrl-S plays again)

# 🧩 CHALLENGE
# 1. Also steer with the W A S D keys.  (Hint: the key name for W is "w")
# 2. It gets TOO fast! Only add 1 to speed while speed is less than 10.
# 3. Make the food jump somewhere new every 3 seconds, even if you
#    don't eat it. Use another function with its own ontimer.
# 4. Press space to play again after GAME OVER: set score and speed back,
#    move the player to (0, 0), and call game_loop() again.
