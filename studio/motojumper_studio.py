#!/usr/bin/env python3
"""
Motojumper Studio: macht aus einem Drehbuch eine fertige Kinder-Folge (Short, 1080x1920).

Anders als der alte Zufalls-Worker hat hier JEDE Folge ein eigenes, von Hand geschriebenes
Drehbuch: feste Figuren mit eigenen Stimmen, eine kleine Geschichte (Anfang - Mitte - Schluss)
und ein klares Lernziel. Das ist wichtig, damit der Kanal nicht als "Massenware" gilt.

Nutzung:
    python3 motojumper_studio.py --liste          # alle Folgen anzeigen
    python3 motojumper_studio.py apples           # eine Folge rendern
    python3 motojumper_studio.py --alle           # alle Folgen rendern

Neue Folge = neuer Eintrag in EPISODEN (siehe unten). Braucht kids_worker.py im gleichen Ordner.
"""
import argparse, math, os, random, subprocess, wave
import cairo
import numpy as np
import kids_worker as kw
from kids_worker import B, H, FPS, SR, COLORS, REGENBOGEN, rgb, ellipse, fuell

GY = 1490  # Bodenhoehe (Fuesse der Figuren)

# ---------------- Feste Figuren des Kanals ----------------
# name: (Tierart, Stimme, Tonhoehe)
FIGUREN = {
    "sunny": (None, "af_heart", 1.06),      # die Sonne erzaehlt
    "momo": ("bear", "am_puck", 1.16),      # Momo der Baer
    "juju": ("bunny", "af_bella", 1.22),    # Juju der Hase
    "freddy": ("frog", "am_fenrir", 1.05),  # Freddy der Frosch
    "pip": ("chick", "af_nicole", 1.36),    # Pip das Kueken
    "kiki": ("cat", "af_sky", 1.26),        # Kiki die Katze
    "dodo": ("dog", "am_liam", 1.2),        # Dodo der Hund
}

# ---------------- Drehbuecher ----------------
# Eine Zeile: (Sprecher, Text, [Aktionen])  – Aktionen laufen ab dem Beginn der Zeile.
# Aktionen: show/hide/move/drop/away/jump/wave/wiggle/word/sparkle/confetti, optional {"at": 0..1}
EPISODEN = {
    "apples": dict(
        titel="MOMO'S APPLES",
        lernziel="Zaehlen von 1 bis 5 und Teilen",
        yt_titel="Momo Shares His Apples 🍎 Count to 5 | Story for Kids #shorts",
        yt_text="Momo the bear is hungry and finds an apple tree. Count the apples with Momo: one, two, three, four, five! "
                "Then his friend Juju the bunny comes along, and Momo learns that sharing is caring.\n\n"
                "Learning goals: counting 1 to 5, sharing with friends.",
        tags=["counting for kids", "count to 5", "sharing is caring", "story for kids", "preschool learning", "Momo and Juju"],
        buehne=[
            ("tree", "tree", dict(x=770, y=GY, z=0, s=1)),
            ("a1", "apple", dict(x=650, y=850, z=5, s=1)), ("a2", "apple", dict(x=770, y=770, z=5, s=1)),
            ("a3", "apple", dict(x=890, y=850, z=5, s=1)), ("a4", "apple", dict(x=700, y=980, z=5, s=1)),
            ("a5", "apple", dict(x=850, y=990, z=5, s=1)),
            ("momo", "actor", dict(x=300, z=3, size=125)), ("juju", "actor", dict(x=-250, z=3, size=108, s=1)),
        ],
        zeilen=[
            ("sunny", "Hi friends! This is Momo the bear.", [("show", "momo"), ("wave", "momo")]),
            ("momo", "Hello! I am so hungry!", [("jump", "momo")]),
            ("sunny", "Look, Momo! An apple tree! Let's count the apples.", [("move", "momo", 360, None), ("wiggle", "tree", {"at": .3})]),
            ("sunny", "One!", [("drop", "a1", 590, GY - 40), ("word", "1", "red")]),
            ("sunny", "Two!", [("drop", "a2", 680, GY - 40), ("word", "2", "orange")]),
            ("sunny", "Three!", [("drop", "a3", 770, GY - 40), ("word", "3", "green")]),
            ("sunny", "Four!", [("drop", "a4", 860, GY - 40), ("word", "4", "blue")]),
            ("sunny", "Five!", [("drop", "a5", 950, GY - 40), ("word", "5", "purple")]),
            ("momo", "Five apples! Yummy!", [("jump", "momo"), ("word", "5 APPLES", "red")]),
            ("sunny", "Oh look! Here comes Juju the bunny.", [("move", "juju", 115, None, 1.0), ("word", None)]),
            ("juju", "Hello Momo! I am hungry too.", [("wave", "juju")]),
            ("sunny", "Hmm. What can Momo do?", [("wiggle", "momo")], .5),
            ("momo", "Here, Juju! Let's share!", [("jump", "momo"), ("move", "a1", 70, GY + 40, .7, {"at": .4}), ("move", "a2", 160, GY + 40, .7, {"at": .5})]),
            ("sunny", "Two apples for Juju, and three apples for Momo.",
             [("move", "a3", 300, GY + 40, .7, {"at": .45}), ("move", "a4", 380, GY + 40, .7, {"at": .5}), ("move", "a5", 460, GY + 40, .7, {"at": .55}),
              ("jump", "juju", {"at": .2})]),
            ("juju", "Thank you, Momo!", [("jump", "juju"), ("sparkle", "juju")]),
            ("sunny", "Sharing is caring! Great job, Momo!", [("confetti",), ("word", "SHARING IS CARING!", "rainbow"), ("jump", "momo"), ("jump", "juju", {"at": .3})]),
            ("sunny", "Bye bye, friends! See you next time!", [("wave", "momo"), ("wave", "juju"), ("word", "BYE BYE!", "rainbow")]),
        ]),

    "balloon": dict(
        titel="JUJU'S BALLOON",
        lernziel="Farben Rot, Blau und Gelb erkennen; Danke sagen",
        yt_titel="Where Is Juju's Red Balloon? 🎈 Learn Colors | Story for Kids #shorts",
        yt_text="Oh no! The wind blows Juju's red balloon away. Help Juju the bunny find it! Is it the blue one? "
                "Is it the yellow one? A little story about colors and saying thank you.\n\n"
                "Learning goals: the colors red, blue and yellow, saying thank you.",
        tags=["learn colors", "colors for kids", "red blue yellow", "story for kids", "preschool learning", "Momo and Juju"],
        buehne=[
            ("juju", "actor", dict(x=300, z=3, size=130)),
            ("red", "balloon", dict(x=500, y=1020, z=4, size=105, farbe="red")),
            ("blue", "balloon", dict(x=760, y=820, z=4, size=125, farbe="blue")),
            ("yellow", "balloon", dict(x=760, y=820, z=4, size=125, farbe="yellow")),
        ],
        zeilen=[
            ("sunny", "Hi friends! Juju the bunny has a red balloon.", [("show", "juju"), ("show", "red", {"at": .5}), ("word", "RED", "red", {"at": .6})]),
            ("juju", "I love my red balloon!", [("jump", "juju")]),
            ("sunny", "Oh no! The wind blows the balloon away!", [("move", "red", 1350, 250, 1.5, {"at": .15}), ("word", None)]),
            ("juju", "My balloon! Where is it?", [("wiggle", "juju")], .5),
            ("sunny", "Let's help Juju. Is this Juju's balloon?", [("show", "blue", {"at": .45})], .7),
            ("juju", "No. That one is blue.", [("word", "BLUE", "blue", {"at": .5}), ("sparkle", "blue", {"at": .5})]),
            ("sunny", "Is this Juju's balloon?", [("away", "blue"), ("word", None), ("show", "yellow", {"at": .4})], .7),
            ("juju", "No. That one is yellow.", [("word", "YELLOW", "yellow", {"at": .5}), ("sparkle", "yellow", {"at": .5})]),
            ("sunny", "Look up there! Is this Juju's balloon?",
             [("away", "yellow"), ("word", None), ("place", "red", 760, -300), ("move", "red", 760, 840, 1.2, {"at": .25})], .7),
            ("juju", "Yes! That is my red balloon!", [("jump", "juju"), ("word", "RED", "red"), ("sparkle", "red"), ("confetti",)]),
            ("juju", "Thank you, friends!", [("move", "red", 500, 1020, .9), ("wave", "juju")]),
            ("sunny", "We found the red balloon. Great job! Bye bye!", [("word", "GREAT JOB!", "rainbow"), ("jump", "juju", {"at": .4}), ("wave", "juju", {"at": .6})]),
        ]),

    "hide": dict(
        titel="HIDE AND SEEK",
        lernziel="Genau hinhoeren: Tierlaute von Frosch, Kueken und Katze",
        yt_titel="Hide and Seek with Momo 🙈 Who Is Hiding? Animal Sounds for Kids #shorts",
        yt_text="Momo the bear plays hide and seek with his friends. Listen closely: who is hiding behind the bush? "
                "Ribbit, cheep or meow? Guess along with Momo and find Freddy the frog, Pip the chick and Kiki the cat.\n\n"
                "Learning goals: listening carefully, animal sounds.",
        tags=["animal sounds", "hide and seek", "guess the animal", "story for kids", "preschool learning", "Momo and Juju"],
        buehne=[
            ("freddy", "actor", dict(x=480, y=GY - 150, z=1, size=78)), ("pip", "actor", dict(x=720, y=GY - 150, z=1, size=78)),
            ("kiki", "actor", dict(x=955, y=GY - 150, z=1, size=78)),
            ("b1", "bush", dict(x=480, y=GY, z=2, s=1)), ("b2", "bush", dict(x=720, y=GY, z=2, s=1)), ("b3", "bush", dict(x=955, y=GY, z=2, s=1)),
            ("momo", "actor", dict(x=170, z=3, size=112)),
        ],
        zeilen=[
            ("sunny", "Hi friends! Momo plays hide and seek with his friends.", [("show", "momo"), ("wave", "momo")]),
            ("momo", "Ready or not, here I come!", [("jump", "momo")]),
            ("sunny", "Listen! Who is hiding here?", [("wiggle", "b1", {"at": .3}), ("word", "?", "yellow", {"at": .3})]),
            ("freddy", "Ribbit! Ribbit!", [("wiggle", "b1")], .7),
            ("momo", "It's Freddy the frog!", [("show", "freddy", {"at": .2}), ("move", "freddy", None, GY - 285, .4, {"at": .2}), ("word", "FROG", "green", {"at": .2}),
                                              ("sparkle", "freddy", {"at": .25}), ("jump", "momo")]),
            ("sunny", "Listen again! Who is hiding here?", [("wiggle", "b2", {"at": .4}), ("word", "?", "yellow", {"at": .4})]),
            ("pip", "Cheep! Cheep!", [("wiggle", "b2")], .7),
            ("momo", "It's Pip the chick!", [("show", "pip", {"at": .2}), ("move", "pip", None, GY - 285, .4, {"at": .2}), ("word", "CHICK", "orange", {"at": .2}),
                                            ("sparkle", "pip", {"at": .25}), ("jump", "momo")]),
            ("sunny", "One more! Who is hiding here?", [("wiggle", "b3", {"at": .4}), ("word", "?", "yellow", {"at": .4})]),
            ("kiki", "Meow! Meow!", [("wiggle", "b3")], .7),
            ("momo", "It's Kiki the cat!", [("show", "kiki", {"at": .2}), ("move", "kiki", None, GY - 285, .4, {"at": .2}), ("word", "CAT", "pink", {"at": .2}),
                                           ("sparkle", "kiki", {"at": .25}), ("jump", "momo")]),
            ("sunny", "Momo found all his friends! Great listening!",
             [("confetti",), ("word", "GREAT LISTENING!", "rainbow"), ("jump", "freddy"), ("jump", "pip", {"at": .15}), ("jump", "kiki", {"at": .3})]),
            ("sunny", "Bye bye! See you next time!", [("wave", "momo"), ("word", "BYE BYE!", "rainbow"), ("jump", "freddy", {"at": .3}), ("jump", "pip", {"at": .4}), ("jump", "kiki", {"at": .5})]),
        ]),

    "shapes": dict(
        titel="KIKI'S HOUSE",
        lernziel="Formen: Quadrat, Dreieck und Kreis",
        yt_titel="Kiki Builds a House 🏠 Learn Shapes | Story for Kids #shorts",
        yt_text="Kiki the cat wants to build a house. Help her find the right shapes: a square for the walls, a triangle for the roof "
                "and a circle for the window!\n\nLearning goals: square, triangle and circle.",
        tags=["learn shapes", "shapes for kids", "square triangle circle", "story for kids", "preschool learning", "Momo and Juju"],
        buehne=[
            ("sq", "shape", dict(x=700, y=GY - 150, z=1, s=0, size=150, art="square", farbe="yellow")),
            ("tri", "shape", dict(x=700, y=GY - 390, z=1, s=0, size=90, art="triangle", farbe="red")),
            ("ci", "shape", dict(x=700, y=GY - 165, z=2, s=0, size=62, art="circle", farbe="blue")),
            ("kiki", "actor", dict(x=215, z=3, size=115)),
        ],
        zeilen=[
            ("sunny", "Hi friends! This is Kiki the cat.", [("show", "kiki"), ("wave", "kiki")]),
            ("kiki", "Hello! I want to build a house!", [("jump", "kiki")]),
            ("sunny", "Let's help Kiki! First, we need a square.", [("show", "sq", {"at": .55}), ("word", "SQUARE", "yellow", {"at": .55})]),
            ("sunny", "A square has four sides.", [("wiggle", "sq")]),
            ("sunny", "Now a triangle, for the roof.", [("show", "tri", {"at": .2}), ("word", "TRIANGLE", "red", {"at": .2})]),
            ("sunny", "A triangle has three sides.", [("wiggle", "tri")]),
            ("sunny", "And a circle, for the window.", [("show", "ci", {"at": .25}), ("word", "CIRCLE", "blue", {"at": .25})]),
            ("kiki", "A circle is round!", [("jump", "kiki"), ("wiggle", "ci")]),
            ("sunny", "Square, triangle, circle. Look! A house!", [("sparkle", "sq", {"at": .55}), ("confetti", {"at": .55}), ("word", "A HOUSE!", "rainbow", {"at": .55})]),
            ("kiki", "I love my house! Thank you, friends!", [("move", "kiki", 330, None), ("wave", "kiki")]),
            ("sunny", "Bye bye! See you next time!", [("word", "BYE BYE!", "rainbow"), ("jump", "kiki", {"at": .4})]),
        ]),

    "bigsmall": dict(
        titel="BIG AND SMALL",
        lernziel="Gegensaetze: gross und klein, hoch und tief; einander helfen",
        yt_titel="Big Momo Helps Small Pip 🐻🐥 Big and Small | Story for Kids #shorts",
        yt_text="Momo the bear is big. Pip the chick is small. Pip wants an apple, but it hangs too high! Can big Momo help his small friend?\n\n"
                "Learning goals: big and small, high and low, helping each other.",
        tags=["big and small", "opposites for kids", "high and low", "story for kids", "preschool learning", "Momo and Juju"],
        buehne=[
            ("tree", "tree", dict(x=790, y=GY, z=0, s=1)),
            ("ap", "apple", dict(x=690, y=960, z=5, s=1, size=130)),
            ("momo", "actor", dict(x=215, z=3, size=135)), ("pip", "actor", dict(x=572, z=3, size=62)),
        ],
        zeilen=[
            ("sunny", "Hi friends! This is Momo. Momo is big.", [("show", "momo"), ("word", "BIG", "blue", {"at": .65})]),
            ("sunny", "And this is Pip. Pip is small.", [("show", "pip"), ("word", "SMALL", "pink", {"at": .65})]),
            ("pip", "I want that apple! But it is too high!", [("jump", "pip"), ("jump", "pip", {"at": .35}), ("word", "HIGH", "orange", {"at": .6}), ("wiggle", "ap", {"at": .6})]),
            ("sunny", "Pip jumps, and jumps. But Pip is too small.", [("jump", "pip"), ("jump", "pip", {"at": .3}), ("word", None, {"at": .5})]),
            ("momo", "Don't worry, Pip! I am big. I can help you!", [("move", "momo", 365, None, 1.0), ("wave", "momo", {"at": .5})]),
            ("sunny", "Momo shakes the tree.", [("wiggle", "tree"), ("drop", "ap", 688, GY - 55, {"at": .7})]),
            ("sunny", "Now the apple is low.", [("word", "LOW", "green", {"at": .5})]),
            ("pip", "Thank you, Momo! You are a good friend!", [("jump", "pip"), ("sparkle", "pip")]),
            ("sunny", "Big friends and small friends help each other. Great job!", [("confetti",), ("word", "FRIENDS HELP!", "rainbow"), ("jump", "momo"), ("jump", "pip", {"at": .2})]),
            ("sunny", "Bye bye! See you next time!", [("word", "BYE BYE!", "rainbow"), ("wave", "momo"), ("jump", "pip", {"at": .4})]),
        ]),

    "pond": dict(
        titel="FREDDY JUMPS",
        lernziel="Zaehlen bis 3; mutig sein und etwas versuchen",
        yt_titel="Freddy the Frog Is Brave 🐸 Count 1 2 3 | Story for Kids #shorts",
        yt_text="Freddy the frog wants to visit his friend Kiki, but the pond is so big! Count the jumps with Freddy: one, two, three! "
                "A little story about being brave.\n\nLearning goals: counting to 3, trying even when you are a little scared.",
        tags=["count to 3", "counting for kids", "being brave", "story for kids", "preschool learning", "Momo and Juju"],
        buehne=[
            ("pond", "pond", dict(x=520, y=GY + 15, z=0, s=1)),
            ("l1", "lily", dict(x=330, y=GY + 10, z=1, s=1)), ("l2", "lily", dict(x=520, y=GY + 10, z=1, s=1)), ("l3", "lily", dict(x=710, y=GY + 10, z=1, s=1)),
            ("freddy", "actor", dict(x=105, z=3, size=85)), ("kiki", "actor", dict(x=988, z=3, size=86)),
        ],
        zeilen=[
            ("sunny", "Hi friends! Freddy the frog wants to visit Kiki.", [("show", "freddy"), ("show", "kiki", {"at": .6})]),
            ("kiki", "Come over, Freddy!", [("wave", "kiki")]),
            ("freddy", "But the pond is so big. I am a little scared.", [("wiggle", "freddy", {"at": .5})], .45),
            ("sunny", "You can do it, Freddy! Let's count the jumps.", [("jump", "kiki", {"at": .2})]),
            ("sunny", "One!", [("move", "freddy", 330, None, .5), ("jump", "freddy"), ("word", "1", "green")]),
            ("sunny", "Two!", [("move", "freddy", 520, None, .5), ("jump", "freddy"), ("word", "2", "blue")]),
            ("sunny", "Three!", [("move", "freddy", 710, None, .5), ("jump", "freddy"), ("word", "3", "purple")]),
            ("freddy", "One more jump!", [("move", "freddy", 818, None, .5, {"at": .6}), ("jump", "freddy", {"at": .6}), ("word", None)]),
            ("freddy", "I did it! I did it!", [("jump", "freddy"), ("jump", "freddy", {"at": .5}), ("sparkle", "freddy"), ("confetti",)]),
            ("kiki", "Hooray, Freddy! You are so brave!", [("jump", "kiki"), ("word", "BRAVE!", "rainbow")]),
            ("sunny", "Freddy was scared, but he tried. Great job! Bye bye!", [("word", "YOU CAN DO IT!", "rainbow", {"at": .5}), ("wave", "kiki", {"at": .6})]),
        ]),

    "ball": dict(
        titel="WHERE IS THE BALL?",
        lernziel="Ortswoerter: auf, neben, hinter",
        yt_titel="Where Is Dodo's Ball? ⚽ On, Next To, Behind | Story for Kids #shorts",
        yt_text="Dodo the dog loves his red ball. Boing! Where does it bounce? On the box, next to the box, or behind the bush? "
                "Look closely and help Dodo find it!\n\nLearning goals: the position words on, next to and behind.",
        tags=["position words", "on next to behind", "prepositions for kids", "story for kids", "preschool learning", "Momo and Juju"],
        buehne=[
            ("box", "box", dict(x=540, y=GY - 85, z=1, s=1, size=85)),
            ("ball", "ball", dict(x=340, y=GY - 48, z=1.5, s=0, farbe="red")),
            ("b1", "bush", dict(x=880, y=GY, z=2, s=1)),
            ("dodo", "actor", dict(x=170, z=3, size=112)),
        ],
        zeilen=[
            ("sunny", "Hi friends! Dodo the dog loves his red ball.", [("show", "dodo"), ("show", "ball", {"at": .6})]),
            ("dodo", "Woof! Let's play!", [("jump", "dodo")]),
            ("sunny", "Boing! The ball is on the box.", [("move", "ball", 540, GY - 218, .55), ("jump", "ball"), ("word", "ON", "blue", {"at": .5})]),
            ("sunny", "Boing! Now the ball is next to the box.", [("move", "ball", 700, GY - 48, .55), ("jump", "ball"), ("word", "NEXT TO", "green", {"at": .5})]),
            ("sunny", "Boing! Oh! Where is the ball now?", [("move", "ball", 880, GY - 110, .55), ("jump", "ball"), ("word", "?", "yellow", {"at": .45})], .6),
            ("dodo", "Hmm. Where is my ball?", [("wiggle", "dodo")], .5),
            ("sunny", "Look closely! The ball is behind the bush!",
             [("wiggle", "b1", {"at": .25}), ("move", "ball", None, GY - 225, .4, {"at": .45}), ("word", "BEHIND", "purple", {"at": .5}), ("sparkle", "ball", {"at": .55})]),
            ("dodo", "I found it! Woof, woof!", [("move", "dodo", 690, None, .8), ("jump", "dodo", {"at": .7}), ("confetti", {"at": .3})]),
            ("sunny", "On, next to, behind. Great looking! Bye bye!", [("word", "GREAT JOB!", "rainbow"), ("wave", "dodo", {"at": .5})]),
        ]),

    "picnic": dict(
        titel="MOMO'S PICNIC",
        lernziel="Obst benennen: Apfel, Banane, Orange; Farben und Formen beschreiben",
        yt_titel="What Is in the Basket? 🍌 Learn Fruits | Story for Kids #shorts",
        yt_text="Momo and Juju have a picnic! What is in the basket? It is red and round... it is long and yellow... Guess the fruit with Momo and Juju!\n\n"
                "Learning goals: apple, banana and orange, describing colors and shapes.",
        tags=["learn fruits", "fruits for kids", "apple banana orange", "story for kids", "preschool learning", "Momo and Juju"],
        buehne=[
            ("ap", "apple", dict(x=540, y=GY - 110, z=1, s=0, size=175)), ("ba", "banana", dict(x=540, y=GY - 110, z=1, s=0, size=120)),
            ("or", "orange", dict(x=540, y=GY - 110, z=1, s=0, size=175)),
            ("basket", "basket", dict(x=540, y=GY - 75, z=2, s=0, size=100)),
            ("momo", "actor", dict(x=185, z=3, size=118)), ("juju", "actor", dict(x=895, z=3, size=105)),
        ],
        zeilen=[
            ("sunny", "Hi friends! Momo and Juju have a picnic today.", [("show", "momo"), ("show", "juju", {"at": .3}), ("show", "basket", {"at": .6})]),
            ("juju", "What is in the basket, Momo?", [("jump", "juju")]),
            ("momo", "Let's look!", [("wiggle", "basket")]),
            ("sunny", "It is red, and round. It's an apple!", [("show", "ap"), ("move", "ap", 540, 1040, .5), ("word", "APPLE", "red", {"at": .6})]),
            ("sunny", "It is long, and yellow. It's a banana!", [("move", "ap", 300, 790, .5), ("show", "ba"), ("move", "ba", 540, 1040, .5), ("word", "BANANA", "yellow", {"at": .6})]),
            ("sunny", "It is round, and orange. It's an orange!", [("move", "ba", 540, 790, .5), ("show", "or"), ("move", "or", 540, 1040, .5), ("word", "ORANGE", "orange", {"at": .6})]),
            ("juju", "Apple, banana, orange. Yummy fruit!", [("move", "or", 780, 790, .5), ("jump", "juju"), ("word", "FRUIT", "green")]),
            ("momo", "Fruit makes us strong!", [("jump", "momo"), ("sparkle", "momo")]),
            ("sunny", "What is your favorite fruit? Bye bye, friends!", [("confetti",), ("word", "BYE BYE!", "rainbow", {"at": .55}), ("wave", "momo"), ("wave", "juju")]),
        ]),

    "abc": dict(
        titel="PIP'S ABC",
        lernziel="Die Buchstaben A, B und C mit je einem Wort",
        yt_titel="A B C with Pip 🐥 A Is for Apple | Learn Letters for Kids #shorts",
        yt_text="Pip the chick wants to learn the ABC! A is for apple, B is for bear, C is for cat. Say the letters together with Pip and his friends.\n\n"
                "Learning goals: the letters A, B and C.",
        tags=["abc for kids", "learn letters", "a is for apple", "alphabet", "preschool learning", "Momo and Juju"],
        buehne=[
            ("A", "letter", dict(x=540, y=1010, z=4, s=0, size=150, text="A", farbe="red")),
            ("Bl", "letter", dict(x=540, y=1010, z=4, s=0, size=150, text="B", farbe="blue")),
            ("Cl", "letter", dict(x=540, y=1010, z=4, s=0, size=150, text="C", farbe="green")),
            ("ap", "apple", dict(x=880, y=GY - 95, z=3, s=0, size=215)),
            ("momo", "actor", dict(x=870, z=3, size=108)), ("kiki", "actor", dict(x=870, z=3, size=100)),
            ("pip", "actor", dict(x=165, z=3, size=85)),
        ],
        zeilen=[
            ("sunny", "Hi friends! Pip wants to learn his letters: A, B, C!", [("show", "pip"), ("wave", "pip")]),
            ("pip", "Teach me, please!", [("jump", "pip")]),
            ("sunny", "This is the letter A.", [("show", "A")]),
            ("sunny", "A, is for apple.", [("show", "ap"), ("word", "APPLE", "red", {"at": .4})]),
            ("pip", "A! Apple!", [("jump", "pip")]),
            ("sunny", "This is the letter B.", [("move", "A", 290, 760, .5), ("scale", "A", .55), ("hide", "ap"), ("word", None), ("show", "Bl", {"at": .3})]),
            ("sunny", "B, is for bear.", [("show", "momo"), ("word", "BEAR", "orange", {"at": .4})]),
            ("momo", "That's me! B! Bear!", [("jump", "momo"), ("wave", "momo")]),
            ("sunny", "This is the letter C.", [("move", "Bl", 540, 760, .5), ("scale", "Bl", .55), ("hide", "momo"), ("word", None), ("show", "Cl", {"at": .3})]),
            ("sunny", "C, is for cat.", [("show", "kiki"), ("word", "CAT", "pink", {"at": .4})]),
            ("kiki", "Meow! C! Cat!", [("jump", "kiki")]),
            ("sunny", "A, B, C! Great job, Pip!", [("move", "Cl", 790, 760, .5), ("scale", "Cl", .55), ("confetti", {"at": .4}), ("word", "GREAT JOB!", "rainbow", {"at": .4}), ("jump", "pip", {"at": .5})]),
            ("pip", "A, B, C! Bye bye!", [("wave", "pip"), ("jump", "kiki", {"at": .4})]),
        ]),

    "light": dict(
        titel="STOP AND GO",
        lernziel="Ampelfarben: Rot heisst stehen, Gelb warten, Gruen gehen",
        yt_titel="Red Means Stop, Green Means Go! 🚦 Traffic Light for Kids #shorts",
        yt_text="Juju the bunny goes for a walk and finds a traffic light. Red means stop, yellow means wait, green means go! "
                "Play along with Juju: what do you do when the light is red?\n\nLearning goals: traffic light colors and what they mean.",
        tags=["traffic light for kids", "red means stop", "green means go", "road safety for kids", "preschool learning", "Momo and Juju"],
        buehne=[
            ("road", "road", dict(x=0, y=GY, z=0, s=1)),
            ("light", "light", dict(x=900, y=GY, z=1, s=1)),
            ("juju", "actor", dict(x=150, z=3, size=110)),
        ],
        zeilen=[
            ("sunny", "Hi friends! Juju goes for a walk. Look! A traffic light!", [("show", "juju"), ("wiggle", "light", {"at": .65})]),
            ("sunny", "Red means stop!", [("set", "light", 1), ("word", "STOP", "red")]),
            ("juju", "Red! I stop.", [("wiggle", "juju")]),
            ("sunny", "Yellow means wait.", [("set", "light", 2), ("word", "WAIT", "yellow")]),
            ("juju", "Yellow! I wait.", []),
            ("sunny", "Green means go!", [("set", "light", 3), ("word", "GO", "green")]),
            ("juju", "Green! I go! Hop, hop, hop!", [("move", "juju", 300, None, .45, {"at": .4}), ("jump", "juju", {"at": .4}), ("move", "juju", 450, None, .45, {"at": .62}),
                                                    ("jump", "juju", {"at": .62}), ("move", "juju", 600, None, .45, {"at": .84}), ("jump", "juju", {"at": .84})]),
            ("sunny", "Let's play again! The light is red.", [("set", "light", 1, {"at": .6}), ("word", "?", "red", {"at": .6})]),
            ("sunny", "What does Juju do?", [], .9),
            ("juju", "I stop!", [("wiggle", "juju"), ("sparkle", "juju"), ("word", "STOP", "red")]),
            ("sunny", "Yes! Red means stop, yellow means wait, green means go. Great job! Bye bye!",
             [("set", "light", 2, {"at": .28}), ("set", "light", 3, {"at": .48}), ("confetti", {"at": .65}), ("word", "GREAT JOB!", "rainbow", {"at": .65}), ("wave", "juju", {"at": .7})]),
        ]),

    "snowman": dict(
        titel="MOMO'S SNOWMAN", welt="winter",
        lernziel="Groessen: gross, mittel, klein; fuer andere sorgen",
        yt_titel="Momo Builds a Snowman! ⛄ Big, Medium, Small #shorts",
        yt_text="It is snowing! Momo the bear builds a snowman: a big snowball, a medium snowball and a small snowball on top. "
                "Then Juju the bunny brings a warm scarf.",
        ziele="big, medium and small, caring for others.",
        hashtags="#snowman #sizesforkids",
        tags=["snowman for kids", "big medium small", "sizes for kids", "winter story for kids"],
        buehne=[
            ("s1", "snowball", dict(x=690, y=GY - 150, z=1, s=0, size=155)), ("s2", "snowball", dict(x=690, y=GY - 385, z=2, s=0, size=112)),
            ("s3", "snowball", dict(x=690, y=GY - 555, z=3, s=0, size=80)),
            ("face", "snowface", dict(x=690, y=GY - 560, z=4, s=0, size=80)), ("nose", "carrot", dict(x=700, y=GY - 548, z=5, s=0, size=46)),
            ("scarf", "scarf", dict(x=690, y=GY - 478, z=5, s=0, size=100)),
            ("momo", "actor", dict(x=225, z=6, size=118)), ("juju", "actor", dict(x=1300, z=6, size=92, s=1)),
        ],
        zeilen=[
            ("sunny", "Hi friends! Look, it is snowing! Momo wants to build a snowman.", [("show", "momo"), ("wave", "momo")]),
            ("momo", "I love snow! Let's build!", [("jump", "momo")]),
            ("sunny", "First, a big snowball.", [("show", "s1", {"at": .3}), ("word", "BIG", "blue", {"at": .3})]),
            ("sunny", "Next, a medium snowball.", [("show", "s2", {"at": .3}), ("word", "MEDIUM", "green", {"at": .3})]),
            ("sunny", "And on top, a small snowball.", [("show", "s3", {"at": .45}), ("word", "SMALL", "pink", {"at": .45})]),
            ("momo", "Big, medium, small!", [("wiggle", "s1"), ("wiggle", "s2", {"at": .35}), ("wiggle", "s3", {"at": .7}), ("jump", "momo", {"at": .7})]),
            ("sunny", "Now the snowman needs a face. Two eyes, and a carrot nose!", [("word", None), ("show", "face", {"at": .5}), ("show", "nose", {"at": .78})]),
            ("sunny", "Oh! Here comes Juju, with a warm scarf.", [("move", "juju", 965, None, 1.0)]),
            ("juju", "Here you go, snowman! Now you are warm.", [("show", "scarf", {"at": .2}), ("sparkle", "scarf", {"at": .2}), ("jump", "juju", {"at": .5})]),
            ("sunny", "What a happy snowman! Great job, friends! Bye bye!", [("confetti",), ("word", "GREAT JOB!", "rainbow"), ("jump", "momo"), ("jump", "juju", {"at": .3}), ("wave", "momo", {"at": .6})]),
        ]),

    "xtree": dict(
        titel="THE STAR ON TOP", welt="winter",
        lernziel="Ortswoerter: unten, in der Mitte, oben; zusammen schafft man mehr",
        yt_titel="Kiki and Pip Decorate the Tree! 🎄 Top, Middle, Bottom #shorts",
        yt_text="Kiki the cat and Pip the chick decorate the Christmas tree. A red ball at the bottom, a blue ball in the middle... "
                "but who can put the star on the top? Little Pip needs a friend to help!",
        ziele="bottom, middle and top, working together.",
        hashtags="#christmastree #positionwords",
        tags=["christmas tree for kids", "top middle bottom", "position words", "christmas story for kids"],
        buehne=[
            ("tree", "xtree", dict(x=640, y=GY, z=0, s=1, size=100)),
            ("b1", "ball", dict(x=575, y=GY - 215, z=2, s=0, size=115, farbe="red")), ("b2", "ball", dict(x=700, y=GY - 430, z=2, s=0, size=115, farbe="blue")),
            ("star", "star", dict(x=640, y=GY - 830, z=3, s=0, size=85)),
            ("kiki", "actor", dict(x=175, z=4, size=105)), ("pip", "actor", dict(x=985, z=4, size=62)),
        ],
        zeilen=[
            ("sunny", "Hi friends! Kiki and Pip decorate the Christmas tree.", [("show", "kiki"), ("show", "pip", {"at": .4})]),
            ("kiki", "Let's make it pretty!", [("jump", "kiki")]),
            ("sunny", "A red ball goes at the bottom.", [("show", "b1", {"at": .25}), ("word", "BOTTOM", "red", {"at": .55})]),
            ("sunny", "A blue ball goes in the middle.", [("show", "b2", {"at": .25}), ("word", "MIDDLE", "blue", {"at": .55})]),
            ("pip", "I want to put the star on the top! But I am too small.", [("word", None), ("jump", "pip", {"at": .5}), ("jump", "pip", {"at": .75})], .4),
            ("kiki", "I will help you, Pip! Up you go!", [("move", "kiki", 330, None, .7), ("move", "pip", 800, GY - 700, 1.0, {"at": .55})]),
            ("sunny", "The star goes on the top!", [("show", "star", {"at": .2}), ("sparkle", "star", {"at": .2}), ("word", "TOP", "yellow", {"at": .5})]),
            ("pip", "We did it together!", [("move", "pip", 985, GY - 93, .9), ("jump", "kiki", {"at": .5})]),
            ("sunny", "Bottom, middle, top. What a beautiful tree! Happy holidays, friends!",
             [("wiggle", "b1"), ("wiggle", "b2", {"at": .2}), ("wiggle", "star", {"at": .4}), ("confetti", {"at": .5}), ("word", "HAPPY HOLIDAYS!", "rainbow", {"at": .5}),
              ("jump", "pip", {"at": .7}), ("wave", "kiki", {"at": .6})]),
        ]),

    "gifts": dict(
        titel="A GIFT FOR YOU", welt="winter",
        lernziel="Schenken macht Freude; welches Tier mag was (Katze-Fisch, Hund-Knochen, Hase-Karotte)",
        yt_titel="Juju's Gifts! 🎁 Who Likes Fish? Who Likes Bones? #shorts",
        yt_text="Juju the bunny has gifts for her friends! Look, a fish. Who likes fish? Look, a bone. Who likes bones? "
                "And then there is a surprise for Juju, too.",
        ziele="giving makes everyone happy, which animal likes what.",
        hashtags="#giving #animalsforkids",
        tags=["gifts for kids", "giving and sharing", "what do animals eat", "holiday story for kids"],
        buehne=[
            ("g1", "gift", dict(x=540, y=GY - 95, z=2, s=0, size=95, farbe="blue")), ("g2", "gift", dict(x=540, y=GY - 95, z=2, s=0, size=95, farbe="green")),
            ("g3", "gift", dict(x=540, y=GY - 95, z=2, s=0, size=95, farbe="red")),
            ("fish", "fish", dict(x=540, y=GY - 330, z=5, s=0, size=110)), ("bone", "bone", dict(x=540, y=GY - 330, z=5, s=0, size=110)),
            ("carrot", "carrot", dict(x=540, y=GY - 330, z=5, s=0, size=120)),
            ("kiki", "actor", dict(x=905, z=3, size=102)), ("dodo", "actor", dict(x=905, z=3, size=105)), ("momo", "actor", dict(x=905, z=3, size=112)),
            ("juju", "actor", dict(x=175, z=3, size=105)),
        ],
        zeilen=[
            ("sunny", "Hi friends! Juju has gifts for her friends today.", [("show", "juju"), ("wave", "juju"), ("show", "g1", {"at": .6})]),
            ("juju", "Giving makes me happy!", [("jump", "juju")]),
            ("sunny", "Look, a fish! Who likes fish?", [("wiggle", "g1"), ("show", "fish", {"at": .2}), ("hide", "g1", {"at": .25}), ("word", "?", "yellow", {"at": .6})], .6),
            ("kiki", "Me! Meow! Thank you, Juju!", [("show", "kiki"), ("word", "CAT", "pink"), ("move", "fish", 760, GY - 150, .6, {"at": .3}), ("jump", "kiki", {"at": .5})]),
            ("sunny", "Look, a bone! Who likes bones?",
             [("hide", "kiki"), ("hide", "fish"), ("word", None), ("show", "g2"), ("show", "bone", {"at": .3}), ("hide", "g2", {"at": .35}), ("word", "?", "yellow", {"at": .65})], .6),
            ("dodo", "Me! Woof! Thank you, Juju!", [("show", "dodo"), ("word", "DOG", "orange"), ("move", "bone", 760, GY - 150, .6, {"at": .3}), ("jump", "dodo", {"at": .5})]),
            ("sunny", "But wait! There is one more gift.", [("hide", "dodo"), ("hide", "bone"), ("word", None), ("show", "g3", {"at": .3})]),
            ("momo", "This one is for you, Juju! A carrot!", [("show", "momo"), ("wiggle", "g3", {"at": .3}), ("show", "carrot", {"at": .6}), ("hide", "g3", {"at": .65}), ("word", "CARROT", "orange", {"at": .7})]),
            ("juju", "For me? Thank you, Momo!", [("jump", "juju"), ("move", "carrot", 350, GY - 150, .7, {"at": .3}), ("sparkle", "juju", {"at": .4})]),
            ("sunny", "Giving makes everyone happy! Happy holidays! Bye bye!", [("confetti",), ("word", "HAPPY HOLIDAYS!", "rainbow"), ("jump", "momo"), ("jump", "juju", {"at": .3}), ("wave", "momo", {"at": .6})]),
        ]),

    "rainbow": dict(
        titel="RAINBOW COLORS", lernziel="Die sechs Regenbogenfarben in der richtigen Reihenfolge",
        yt_titel="Colors of the Rainbow! 🌈 Learn 6 Colors with Juju #shorts",
        yt_text="Look at the rainbow in the sky! Juju the bunny names its colors, one by one: red, orange, yellow, green, blue and purple. Can you say them too?",
        ziele="the six rainbow colors in order.", hashtags="#rainbowcolors #learncolors",
        tags=["rainbow colors", "learn colors", "colors for kids", "rainbow for kids"],
        buehne=[("c%d" % i, "ball", dict(x=165 + 150 * i, y=900 - [0, 70, 110, 110, 70, 0][i], z=2, s=0, size=140, farbe=f))
                for i, f in enumerate(["red", "orange", "yellow", "green", "blue", "purple"])] + [("juju", "actor", dict(x=540, z=3, size=108))],
        zeilen=[
            ("sunny", "Hi friends! Look at the rainbow in the sky! Let's name its colors.", [("show", "juju"), ("wave", "juju")]),
            ("sunny", "Red!", [("show", "c0"), ("word", "RED", "red")]), ("sunny", "Orange!", [("show", "c1"), ("word", "ORANGE", "orange")]),
            ("sunny", "Yellow!", [("show", "c2"), ("word", "YELLOW", "yellow")]), ("sunny", "Green!", [("show", "c3"), ("word", "GREEN", "green")]),
            ("sunny", "Blue!", [("show", "c4"), ("word", "BLUE", "blue")]), ("sunny", "Purple!", [("show", "c5"), ("word", "PURPLE", "purple")]),
            ("juju", "So many colors! I love the rainbow!", [("jump", "juju"), ("word", None)] + [("wiggle", "c%d" % i, {"at": i * .15}) for i in range(6)]),
            ("sunny", "Red, orange, yellow, green, blue, purple. You know the rainbow! Bye bye!",
             [("jump", "c%d" % i, {"at": .02 + i * .1}) for i in range(6)] + [("confetti", {"at": .65}), ("word", "RAINBOW!", "rainbow", {"at": .65}), ("wave", "juju", {"at": .7})]),
        ]),

    "inout": dict(
        titel="KIKI AND THE BOX", lernziel="Gegensatz: drin und draussen (in / out)",
        yt_titel="Kiki Jumps In the Box! 📦 In and Out #shorts",
        yt_text="Kiki the cat found a big box, and cats love boxes! She jumps in. She jumps out. In, out, in, out. Where is Kiki now?",
        ziele="in and out.", hashtags="#inandout #oppositesforkids",
        tags=["in and out", "opposites for kids", "cat in a box", "position words"],
        buehne=[("kiki", "actor", dict(x=215, z=1, size=100)), ("box", "box", dict(x=540, y=GY - 115, z=2, s=0, size=115))],
        zeilen=[
            ("sunny", "Hi friends! Kiki found a big box.", [("show", "kiki"), ("show", "box", {"at": .45})]),
            ("kiki", "I love boxes! Meow!", [("jump", "kiki")]),
            ("sunny", "Kiki jumps in the box.", [("move", "kiki", 540, GY - 262, .6, {"at": .25}), ("jump", "kiki", {"at": .25}), ("word", "IN", "green", {"at": .6})]),
            ("sunny", "Kiki jumps out of the box.", [("move", "kiki", 865, GY - 150, .6, {"at": .25}), ("jump", "kiki", {"at": .25}), ("word", "OUT", "orange", {"at": .6})]),
            ("sunny", "In!", [("move", "kiki", 540, GY - 262, .5), ("jump", "kiki"), ("word", "IN", "green")]),
            ("sunny", "Out!", [("move", "kiki", 215, GY - 150, .5), ("jump", "kiki"), ("word", "OUT", "orange")]),
            ("sunny", "Where is Kiki now?", [("move", "kiki", 540, GY - 262, .5), ("jump", "kiki"), ("word", "?", "yellow", {"at": .5})], .7),
            ("kiki", "I am in the box! Peekaboo!", [("jump", "kiki"), ("word", "IN", "green"), ("sparkle", "kiki")]),
            ("sunny", "In and out. Great job! Bye bye!", [("confetti",), ("word", "GREAT JOB!", "rainbow"), ("wave", "kiki", {"at": .4})]),
        ]),

    "onemore": dict(
        titel="ONE MORE BALLOON", lernziel="Erstes Rechnen: eins mehr und eins weniger (bis 3)",
        yt_titel="One More Balloon! 🎈 First Math for Kids #shorts",
        yt_text="Juju the bunny has one balloon. Here comes one more! How many are there now? And what happens when one balloon flies away? Count along with Juju!",
        ziele="one more and one less, numbers 1 to 3.", hashtags="#mathforkids #countingforkids",
        tags=["math for kids", "one more one less", "addition for kids", "counting to 3"],
        buehne=[("b1", "balloon", dict(x=470, y=1000, z=4, size=95, farbe="red")), ("b2", "balloon", dict(x=640, y=930, z=4, size=95, farbe="blue")),
                ("b3", "balloon", dict(x=810, y=1000, z=4, size=95, farbe="yellow")), ("juju", "actor", dict(x=215, z=3, size=112))],
        zeilen=[
            ("sunny", "Hi friends! Juju has one balloon.", [("show", "juju"), ("show", "b1", {"at": .5}), ("word", "1", "red", {"at": .6})]),
            ("sunny", "Here comes one more. One, and one more, makes...", [("show", "b2", {"at": .2})], .6),
            ("juju", "Two!", [("word", "2", "blue"), ("jump", "juju")]),
            ("sunny", "And one more! Two, and one more, makes...", [("show", "b3", {"at": .15})], .6),
            ("juju", "Three!", [("word", "3", "orange"), ("jump", "juju")]),
            ("sunny", "Oh! One balloon flies away. Three, take away one, is...", [("away", "b3", {"at": .15})], .6),
            ("juju", "Two! Bye bye, balloon!", [("word", "2", "blue"), ("wave", "juju")]),
            ("sunny", "One more, and one less. You can do math! Bye bye!", [("confetti",), ("word", "GREAT JOB!", "rainbow"), ("jump", "juju", {"at": .4})]),
        ]),

    "def": dict(
        titel="PIP'S D E F", lernziel="Die Buchstaben D, E und F mit je einem Wort",
        yt_titel="D E F with Pip! 🐥 D Is for Dog #shorts",
        yt_text="Pip the chick already knows A, B, C. Today he learns D, E and F! Who starts with D? What starts with E? Guess along with Pip and his friends.",
        ziele="the letters D, E and F.", hashtags="#abcforkids #learnletters",
        tags=["abc for kids", "learn letters", "d is for dog", "alphabet"],
        buehne=[("D", "letter", dict(x=540, y=1010, z=4, s=0, size=150, text="D", farbe="orange")), ("E", "letter", dict(x=540, y=1010, z=4, s=0, size=150, text="E", farbe="purple")),
                ("F", "letter", dict(x=540, y=1010, z=4, s=0, size=150, text="F", farbe="green")), ("egg", "egg", dict(x=880, y=GY - 110, z=3, s=0, size=110)),
                ("dodo", "actor", dict(x=870, z=3, size=105)), ("freddy", "actor", dict(x=870, z=3, size=95)), ("pip", "actor", dict(x=165, z=3, size=85))],
        zeilen=[
            ("sunny", "Hi friends! Pip knows A, B, C. Today we learn D, E, F!", [("show", "pip"), ("wave", "pip")]),
            ("sunny", "This is the letter D. Who starts with D?", [("show", "D")], .5),
            ("dodo", "Me! D! Dodo the dog!", [("show", "dodo"), ("jump", "dodo", {"at": .3}), ("word", "DOG", "orange")]),
            ("sunny", "This is the letter E. What starts with E?", [("move", "D", 290, 760, .5), ("scale", "D", .55), ("hide", "dodo"), ("word", None), ("show", "E", {"at": .25})], .5),
            ("pip", "E! Egg! I came from an egg!", [("show", "egg"), ("jump", "pip", {"at": .3}), ("word", "EGG", "purple")]),
            ("sunny", "This is the letter F. Who starts with F?", [("move", "E", 540, 760, .5), ("scale", "E", .55), ("hide", "egg"), ("word", None), ("show", "F", {"at": .25})], .5),
            ("freddy", "Me! F! Freddy the frog!", [("show", "freddy"), ("jump", "freddy", {"at": .3}), ("word", "FROG", "green")]),
            ("sunny", "D, E, F! Great job! Bye bye!", [("move", "F", 790, 760, .5), ("scale", "F", .55), ("confetti", {"at": .4}), ("word", "GREAT JOB!", "rainbow", {"at": .4}), ("jump", "pip", {"at": .5})]),
        ]),

    "sorry": dict(
        titel="OOPS! SORRY!", lernziel="Sich entschuldigen und beim Wiedergutmachen helfen",
        yt_titel="Oops! Dodo Says Sorry 🧱 Kindness Story for Kids #shorts",
        yt_text="Kiki the cat builds a tall tower. Then Dodo the dog runs by, and oops, the tower falls down! What does a good friend do now?",
        ziele="saying sorry and helping to fix a mistake.", hashtags="#sayingsorry #kindnessforkids",
        tags=["saying sorry", "kindness for kids", "manners for kids", "friendship story"],
        buehne=[("t1", "shape", dict(x=560, y=GY - 78, z=1, s=0, size=78, art="square", farbe="red")), ("t2", "shape", dict(x=560, y=GY - 234, z=1, s=0, size=78, art="square", farbe="yellow")),
                ("t3", "shape", dict(x=560, y=GY - 390, z=1, s=0, size=78, art="square", farbe="blue")),
                ("kiki", "actor", dict(x=170, z=3, size=100)), ("dodo", "actor", dict(x=1300, z=3, size=105, s=1))],
        zeilen=[
            ("sunny", "Hi friends! Kiki builds a tall tower.", [("show", "kiki"), ("show", "t1", {"at": .3}), ("show", "t2", {"at": .55}), ("show", "t3", {"at": .8})]),
            ("kiki", "One, two, three blocks! So tall!", [("jump", "kiki")]),
            ("sunny", "Here comes Dodo. He runs very fast.", [("move", "dodo", 905, None, .8, {"at": .35})]),
            ("sunny", "Oops! The tower falls down.", [("wiggle", "t1"), ("drop", "t3", 730, GY - 78), ("drop", "t2", 390, GY - 78, {"at": .15}), ("word", "OOPS!", "red")]),
            ("kiki", "Oh no! My tower!", [("wiggle", "kiki")]),
            ("dodo", "I am sorry, Kiki. It was an accident.", [("word", "SORRY", "blue")]),
            ("kiki", "It's okay, Dodo.", [("word", "IT'S OKAY", "green")]),
            ("sunny", "Dodo helps to build it again.", [("move", "t2", 560, GY - 234, .6), ("move", "t3", 560, GY - 390, .6, {"at": .45}), ("word", None)]),
            ("sunny", "When we make a mistake, we say sorry. Good friends! Bye bye!", [("confetti",), ("word", "GOOD FRIENDS!", "rainbow"), ("jump", "kiki"), ("jump", "dodo", {"at": .3})]),
        ]),

    "body": dict(
        titel="MOMO'S BODY", lernziel="Koerperteile: Augen, Ohren, Nase, Bauch und was sie tun",
        yt_titel="Eyes, Ears, Nose! 🐻 Body Parts with Momo #shorts",
        yt_text="Let's learn about our body with Momo the bear! We see with our eyes, we hear with our ears and we smell with our nose. Can you touch your nose?",
        ziele="eyes, ears, nose and tummy, and what they do.", hashtags="#bodyparts #bodypartsforkids",
        tags=["body parts for kids", "eyes ears nose", "my body", "parts of the body"],
        buehne=[("momo", "actor", dict(x=540, z=3, size=190))],
        zeilen=[
            ("sunny", "Hi friends! Let's learn about our body, with Momo!", [("show", "momo"), ("wave", "momo")]),
            ("sunny", "These are Momo's eyes. We see with our eyes.", [("spark", 540, GY - 305), ("word", "EYES", "blue")]),
            ("sunny", "These are Momo's ears. We hear with our ears.", [("spark", 403, GY - 410), ("spark", 677, GY - 410, {"at": .1}), ("word", "EARS", "purple")]),
            ("sunny", "This is Momo's nose. We smell with our nose.", [("spark", 540, GY - 245), ("word", "NOSE", "red")]),
            ("sunny", "And this is Momo's tummy!", [("spark", 540, GY - 85), ("word", "TUMMY", "orange"), ("jump", "momo", {"at": .6})]),
            ("momo", "Now you! Can you touch your nose?", [("word", "YOUR TURN!", "green")], 1.0),
            ("sunny", "Eyes, ears, nose and tummy. Great job! Bye bye!", [("confetti",), ("word", "GREAT JOB!", "rainbow"), ("wave", "momo")]),
        ]),

    "rocket": dict(
        titel="BLAST OFF!", lernziel="Rueckwaerts zaehlen von 5 bis 1",
        yt_titel="5, 4, 3, 2, 1, Blast Off! 🚀 Count Down with Pip #shorts",
        yt_text="Pip the chick built a rocket! Help him count down: five, four, three, two, one... blast off! Can you count backwards too?",
        ziele="counting backwards from 5 to 1.", hashtags="#countdown #countingforkids",
        tags=["count down for kids", "counting backwards", "rocket for kids", "5 4 3 2 1"],
        buehne=[("rocket", "rocket", dict(x=640, y=GY - 215, z=2, s=0, size=105)), ("pip", "actor", dict(x=250, z=3, size=80)), ("kiki", "actor", dict(x=925, z=3, size=92))],
        zeilen=[
            ("sunny", "Hi friends! Pip built a rocket! Let's count down from five.", [("show", "pip"), ("show", "rocket", {"at": .3}), ("show", "kiki", {"at": .6})]),
            ("pip", "I am ready to fly!", [("jump", "pip"), ("move", "pip", 640, GY - 300, .5, {"at": .5}), ("hide", "pip", {"at": .75})]),
            ("sunny", "Five!", [("word", "5", "red"), ("wiggle", "rocket")]), ("sunny", "Four!", [("word", "4", "orange")]),
            ("sunny", "Three!", [("word", "3", "green"), ("wiggle", "rocket")]), ("sunny", "Two!", [("word", "2", "blue")]),
            ("sunny", "One!", [("word", "1", "purple"), ("wiggle", "rocket"), ("set", "rocket", 1, {"at": .5})]),
            ("sunny", "Blast off!", [("word", "BLAST OFF!", "rainbow"), ("away", "rocket", {"at": .15}), ("confetti", {"at": .3}), ("jump", "kiki", {"at": .4})]),
            ("kiki", "Bye bye, Pip! Fly safe!", [("wave", "kiki")]),
            ("sunny", "Five, four, three, two, one. You can count backwards! Bye bye!", [("word", "GREAT JOB!", "rainbow", {"at": .6})]),
        ]),

    "sort": dict(
        titel="SORT THE COLORS", lernziel="Sortieren nach Farbe: Rot zu Rot, Blau zu Blau",
        yt_titel="Red or Blue? 🔴🔵 Sort the Balls with Dodo #shorts",
        yt_text="Dodo the dog has a red box and a blue box. Where does the red ball go? Where does the blue ball go? Help Dodo sort the balls by color!",
        ziele="sorting by color, red and blue.", hashtags="#sortingforkids #learncolors",
        tags=["sorting for kids", "sort by color", "red and blue", "matching colors"],
        buehne=[("binr", "shape", dict(x=300, y=GY - 120, z=1, s=0, size=120, art="square", farbe="red")), ("binb", "shape", dict(x=780, y=GY - 120, z=1, s=0, size=120, art="square", farbe="blue")),
                ("ra", "ball", dict(x=540, y=800, z=4, s=0, size=130, farbe="red")), ("ba", "ball", dict(x=540, y=800, z=4, s=0, size=130, farbe="blue")),
                ("rb", "ball", dict(x=540, y=800, z=4, s=0, size=130, farbe="red")), ("dodo", "actor", dict(x=540, z=3, size=88))],
        zeilen=[
            ("sunny", "Hi friends! Dodo has a red box, and a blue box. Let's sort the balls!", [("show", "dodo"), ("show", "binr", {"at": .35}), ("show", "binb", {"at": .55})]),
            ("sunny", "A red ball! Where does it go?", [("show", "ra", {"at": .1}), ("word", "?", "yellow", {"at": .55})], .6),
            ("dodo", "On the red box!", [("move", "ra", 300, GY - 300, .6), ("word", "RED", "red"), ("jump", "dodo", {"at": .4})]),
            ("sunny", "A blue ball! Where does it go?", [("show", "ba", {"at": .1}), ("word", "?", "yellow", {"at": .55})], .6),
            ("dodo", "On the blue box!", [("move", "ba", 780, GY - 300, .6), ("word", "BLUE", "blue"), ("jump", "dodo", {"at": .4})]),
            ("sunny", "One more ball. What color is it?", [("show", "rb", {"at": .1}), ("word", "?", "yellow", {"at": .55})], .6),
            ("dodo", "Red! On the red box! Woof!", [("move", "rb", 300, GY - 420, .6, {"at": .2}), ("word", "RED", "red"), ("jump", "dodo", {"at": .6})]),
            ("sunny", "Red with red, blue with blue. You can sort! Bye bye!", [("confetti",), ("word", "GREAT JOB!", "rainbow"), ("wave", "dodo", {"at": .4})]),
        ]),

    "leftright": dict(
        titel="LEFT AND RIGHT", lernziel="Richtungen: links und rechts",
        yt_titel="Hop Left, Hop Right! 🐰 Left and Right with Juju #shorts",
        yt_text="Play a game with Juju the bunny! Juju hops to the left. Juju hops to the right. Now it is your turn: can you point to the left and to the right?",
        ziele="left and right.", hashtags="#leftandright #directionsforkids",
        tags=["left and right", "directions for kids", "movement game for kids", "bunny hop"],
        buehne=[("juju", "actor", dict(x=540, z=3, size=118))],
        zeilen=[
            ("sunny", "Hi friends! Let's play a game with Juju. Left, and right!", [("show", "juju"), ("wave", "juju")]),
            ("sunny", "Juju hops to the left!", [("move", "juju", 215, None, .6, {"at": .3}), ("jump", "juju", {"at": .3}), ("word", "LEFT", "blue", {"at": .3})]),
            ("sunny", "Juju hops to the right!", [("move", "juju", 865, None, .7, {"at": .3}), ("jump", "juju", {"at": .3}), ("word", "RIGHT", "red", {"at": .3})]),
            ("sunny", "Now you! Point to the left!", [("move", "juju", 215, None, .7, {"at": .5}), ("jump", "juju", {"at": .5}), ("word", "LEFT", "blue", {"at": .5})], .6),
            ("sunny", "Point to the right!", [("move", "juju", 865, None, .7, {"at": .3}), ("jump", "juju", {"at": .3}), ("word", "RIGHT", "red", {"at": .3})], .6),
            ("juju", "Left, right, left, right! That was fun!", [("move", "juju", 380, None, .35), ("move", "juju", 700, None, .35, {"at": .25}), ("move", "juju", 380, None, .35, {"at": .5}),
                                                             ("move", "juju", 540, None, .35, {"at": .75}), ("word", None)]),
            ("sunny", "You know left and right! Great job! Bye bye!", [("confetti",), ("word", "GREAT JOB!", "rainbow"), ("jump", "juju", {"at": .3})]),
        ]),

    "seesaw": dict(
        titel="HEAVY AND LIGHT", lernziel="Gegensatz schwer und leicht; gemeinsam schafft man es",
        yt_titel="Momo on the Seesaw! ⚖️ Heavy and Light #shorts",
        yt_text="Momo the bear and Pip the chick play on the seesaw. Momo is heavy, so down he goes. Pip is light, so up he goes! How can little Pip come down again?",
        ziele="heavy and light, and that friends are stronger together.", hashtags="#heavyandlight #oppositesforkids",
        tags=["heavy and light", "opposites for kids", "seesaw", "weight for kids"],
        buehne=[("saw", "seesaw", dict(x=540, y=GY - 90, z=1, s=1)),
                ("momo", "actor", dict(x=270, y=GY - 255, z=3, size=100)), ("pip", "actor", dict(x=770, y=GY - 187, z=3, size=55)),
                ("kiki", "actor", dict(x=660, y=GY - 237, z=3, size=72)), ("freddy", "actor", dict(x=870, y=GY - 264, z=3, size=62))],
        zeilen=[
            ("sunny", "Hi friends! Momo and Pip play on the seesaw.", [("show", "pip"), ("show", "momo", {"at": .5})]),
            ("sunny", "Momo is heavy. Down goes Momo!", [("tilt", "saw", -.2, {"at": .35}), ("move", "momo", None, GY - 201, .6, {"at": .35}), ("move", "pip", None, GY - 233, .6, {"at": .35}), ("word", "HEAVY", "blue", {"at": .35})]),
            ("sunny", "Pip is light. Up goes Pip!", [("word", "LIGHT", "pink"), ("wiggle", "pip", {"at": .5})]),
            ("pip", "Help! I am stuck up here!", [("wiggle", "pip")]),
            ("sunny", "Here come Kiki and Freddy. They sit next to Pip.", [("word", None), ("show", "kiki", {"at": .2}), ("show", "freddy", {"at": .5})]),
            ("sunny", "Now both sides are the same. The seesaw is balanced!",
             [("tilt", "saw", 0), ("move", "momo", None, GY - 255, .6), ("move", "pip", None, GY - 187, .6), ("move", "kiki", None, GY - 213, .6), ("move", "freddy", None, GY - 198, .6),
              ("word", "BALANCED", "green", {"at": .5})]),
            ("momo", "Three little friends are as heavy as me!", [("wave", "momo")]),
            ("sunny", "Heavy and light. Great job, friends! Bye bye!", [("confetti",), ("word", "GREAT JOB!", "rainbow")]),
        ]),

    "quiet": dict(
        titel="SHH! PIP IS SLEEPING", lernziel="Gegensatz laut und leise; Ruecksicht nehmen",
        yt_titel="Shh! Pip Is Sleeping 😴 Loud and Quiet #shorts",
        yt_text="Shh! Pip the chick is sleeping. Kiki is very quiet. But here comes Dodo the dog: woof, woof! That was loud! What happens now?",
        ziele="loud and quiet, being considerate of others.", hashtags="#loudandquiet #oppositesforkids",
        tags=["loud and quiet", "opposites for kids", "quiet time", "bedtime story for kids"],
        buehne=[("zzz", "text", dict(x=890, y=GY - 290, z=5, s=0, size=80, text="Zzz", farbe="purple")),
                ("pip", "actor", dict(x=790, z=3, size=70)), ("kiki", "actor", dict(x=160, z=3, size=98)), ("dodo", "actor", dict(x=-250, z=3, size=105, s=1))],
        zeilen=[
            ("sunny", "Hi friends! Shh. Pip is sleeping.", [("show", "pip"), ("show", "kiki", {"at": .2}), ("show", "zzz", {"at": .5}), ("word", "SHH...", "purple", {"at": .5})]),
            ("kiki", "We must be quiet.", [("word", "QUIET", "blue")]),
            ("sunny", "Here comes Dodo.", [("move", "dodo", 450, None, .9), ("word", None)]),
            ("dodo", "Woof! Woof! Let's play!", [("jump", "dodo"), ("jump", "dodo", {"at": .4}), ("word", "LOUD", "red"), ("hide", "zzz", {"at": .25}), ("jump", "pip", {"at": .35})]),
            ("sunny", "Oh no! That was loud. Pip woke up!", [("wiggle", "pip")]),
            ("dodo", "Sorry, Pip. I will be quiet now.", [("word", "QUIET", "blue", {"at": .45})]),
            ("sunny", "Dodo is as quiet as a mouse. Pip goes back to sleep.", [("show", "zzz", {"at": .65})]),
            ("sunny", "Loud and quiet. When a friend sleeps, we are quiet. Bye bye!", [("word", "SHH...", "purple", {"at": .55})]),
        ]),

    "pattern": dict(
        titel="WHAT COMES NEXT?", lernziel="Muster erkennen und fortsetzen (Rot, Blau, Rot, Blau ...)",
        yt_titel="What Comes Next? 🔴🔵 Patterns for Kids with Pip #shorts",
        yt_text="Pip the chick makes a pattern: red, blue, red, blue... What comes next? Think along with Pip and find the answer!",
        ziele="recognizing and continuing a simple pattern.", hashtags="#patternsforkids #thinkinggames",
        tags=["patterns for kids", "what comes next", "logic for kids", "preschool math"],
        buehne=[("p%d" % i, "ball", dict(x=190 + 175 * i, y=900, z=2, s=0, size=150, farbe=f)) for i, f in enumerate(["red", "blue", "red", "blue", "red"])]
               + [("q", "text", dict(x=890, y=900, z=3, s=0, size=170, text="?", farbe="yellow")), ("pip", "actor", dict(x=540, z=3, size=88))],
        zeilen=[
            ("sunny", "Hi friends! Pip makes a pattern. Look!", [("show", "pip"), ("wave", "pip")]),
            ("sunny", "Red, blue, red, blue.", [("show", "p0"), ("show", "p1", {"at": .27}), ("show", "p2", {"at": .54}), ("show", "p3", {"at": .8})]),
            ("sunny", "What comes next?", [("show", "q")], 1.0),
            ("pip", "Hmm. Red, blue, red, blue...", [("wiggle", "p0"), ("wiggle", "p1", {"at": .3}), ("wiggle", "p2", {"at": .55}), ("wiggle", "p3", {"at": .8})], .5),
            ("pip", "Red!", [("hide", "q"), ("show", "p4", {"at": .1}), ("sparkle", "p4", {"at": .15}), ("word", "RED", "red"), ("jump", "pip")]),
            ("sunny", "Yes! Red comes next. Red, blue, red, blue, red. That is a pattern!", [("word", "PATTERN", "rainbow", {"at": .75})] + [("jump", "p%d" % i, {"at": .3 + i * .09}) for i in range(5)]),
            ("sunny", "Great thinking! Bye bye!", [("confetti",), ("word", "GREAT JOB!", "rainbow"), ("jump", "pip", {"at": .3})]),
        ]),

    "homes": dict(
        titel="WHO LIVES HERE?", lernziel="Tiere und ihr Zuhause: Teich, Nest, Hundehuette",
        yt_titel="Who Lives Here? 🏡 Animal Homes for Kids #shorts",
        yt_text="Every animal has a home! Who lives in the pond? Who lives in a nest, up in the tree? And who lives in the little house? Guess along!",
        ziele="animal homes: pond, nest and dog house.", hashtags="#animalhomes #animalsforkids",
        tags=["animal homes", "where do animals live", "animals for kids", "habitats for kids"],
        buehne=[("pond", "pond", dict(x=540, y=GY + 15, z=0, s=0)), ("tree", "tree", dict(x=600, y=GY, z=0, s=0)), ("nest", "nest", dict(x=600, y=GY - 560, z=2, s=0, size=100)),
                ("hs", "shape", dict(x=620, y=GY - 135, z=1, s=0, size=135, art="square", farbe="red")), ("hr", "shape", dict(x=620, y=GY - 350, z=1, s=0, size=80, art="triangle", farbe="blue")),
                ("hd", "shape", dict(x=620, y=GY - 95, z=2, s=0, size=75, art="circle", farbe="purple")),
                ("freddy", "actor", dict(x=540, z=3, size=88)), ("pip", "actor", dict(x=600, y=GY - 650, z=3, size=52)), ("dodo", "actor", dict(x=225, z=3, size=102))],
        zeilen=[
            ("sunny", "Hi friends! Every animal has a home. Who lives here?", [("show", "pond", {"at": .5}), ("word", "?", "yellow", {"at": .7})], .6),
            ("freddy", "Me! I live in the pond!", [("show", "freddy"), ("word", "POND", "blue"), ("jump", "freddy", {"at": .4})]),
            ("sunny", "And who lives here, up in the tree?", [("hide", "pond"), ("hide", "freddy"), ("word", None), ("show", "tree", {"at": .15}), ("show", "nest", {"at": .45}), ("word", "?", "yellow", {"at": .7})], .6),
            ("pip", "Me! I live in a nest!", [("show", "pip"), ("word", "NEST", "orange"), ("sparkle", "nest", {"at": .2})]),
            ("sunny", "And who lives in this little house?", [("hide", "tree"), ("hide", "nest"), ("hide", "pip"), ("word", None), ("show", "hs", {"at": .2}), ("show", "hr", {"at": .35}), ("show", "hd", {"at": .5}),
                                                         ("word", "?", "yellow", {"at": .7})], .6),
            ("dodo", "Me! Woof! I live in the dog house!", [("show", "dodo"), ("word", "DOG HOUSE", "red"), ("jump", "dodo", {"at": .4})]),
            ("sunny", "A pond, a nest and a house. Where do you live? Bye bye!", [("confetti",), ("word", "GREAT JOB!", "rainbow"), ("wave", "dodo", {"at": .4})]),
        ]),

    "more": dict(
        titel="WHO HAS MORE?", lernziel="Mengen vergleichen: mehr, weniger, gleich viel",
        yt_titel="Who Has More Apples? 🍎 More, Fewer, the Same #shorts",
        yt_text="Momo the bear has three apples. Juju the bunny has only one. Who has more? And what can Momo do to make it fair?",
        ziele="more, fewer and the same.", hashtags="#moreandless #mathforkids",
        tags=["more and less", "comparing for kids", "math for kids", "more fewer same"],
        buehne=[("m1", "apple", dict(x=130, y=GY + 50, z=5, s=0, size=110)), ("m2", "apple", dict(x=245, y=GY + 50, z=5, s=0, size=110)), ("m3", "apple", dict(x=360, y=GY + 50, z=5, s=0, size=110)),
                ("j1", "apple", dict(x=770, y=GY + 50, z=5, s=0, size=110)), ("momo", "actor", dict(x=245, z=3, size=118)), ("juju", "actor", dict(x=830, z=3, size=105))],
        zeilen=[
            ("sunny", "Hi friends! Momo and Juju have apples.", [("show", "momo"), ("show", "juju", {"at": .2}), ("show", "m1", {"at": .45}), ("show", "m2", {"at": .55}), ("show", "m3", {"at": .65}), ("show", "j1", {"at": .85})]),
            ("sunny", "Momo has three apples. Juju has one apple.", [("wiggle", "m1"), ("wiggle", "m2", {"at": .1}), ("wiggle", "m3", {"at": .2}), ("wiggle", "j1", {"at": .6})]),
            ("sunny", "Who has more?", [("word", "?", "yellow")], .8),
            ("sunny", "Momo has more! Juju has fewer.", [("word", "MORE", "blue"), ("sparkle", "momo"), ("word", "FEWER", "pink", {"at": .55})]),
            ("momo", "That is not fair. Here, Juju!", [("word", None), ("move", "m3", 885, GY + 50, .8, {"at": .45})]),
            ("sunny", "Now Momo has two, and Juju has two. That is the same!", [("word", "THE SAME", "green", {"at": .6}), ("jump", "momo", {"at": .65}), ("jump", "juju", {"at": .75})]),
            ("juju", "Thank you, Momo!", [("wave", "juju")]),
            ("sunny", "More, fewer, the same. Great job! Bye bye!", [("confetti",), ("word", "GREAT JOB!", "rainbow")]),
        ]),

    "turns": dict(
        titel="TAKING TURNS", lernziel="Sich abwechseln: erst du, dann ich",
        yt_titel="Dodo and Kiki Take Turns! ⚽ Sharing Story for Kids #shorts",
        yt_text="Dodo the dog and Kiki the cat both want the ball. I want it! No, I want it! Oh dear. What can they do? A little story about taking turns.",
        ziele="taking turns and playing together.", hashtags="#takingturns #kindnessforkids",
        tags=["taking turns", "sharing for kids", "social skills for kids", "friendship story"],
        buehne=[("ball", "ball", dict(x=540, y=GY - 62, z=4, s=0, size=130, farbe="blue")), ("dodo", "actor", dict(x=205, z=3, size=105)), ("kiki", "actor", dict(x=875, z=3, size=100))],
        zeilen=[
            ("sunny", "Hi friends! Dodo and Kiki both want the ball.", [("show", "dodo"), ("show", "kiki", {"at": .2}), ("show", "ball", {"at": .5})]),
            ("dodo", "I want it!", [("jump", "dodo"), ("move", "ball", 390, None, .3)]),
            ("kiki", "No, I want it!", [("jump", "kiki"), ("move", "ball", 690, None, .3)]),
            ("sunny", "Oh dear. What can they do? They can take turns!", [("move", "ball", 540, None, .5), ("word", "TAKE TURNS", "green", {"at": .6})]),
            ("sunny", "First, it is Dodo's turn.", [("move", "ball", 380, None, .5, {"at": .3}), ("jump", "ball", {"at": .3}), ("word", "DODO'S TURN", "orange", {"at": .3}), ("jump", "dodo", {"at": .6})]),
            ("sunny", "Then, it is Kiki's turn.", [("move", "ball", 700, None, .6, {"at": .3}), ("jump", "ball", {"at": .3}), ("word", "KIKI'S TURN", "pink", {"at": .3}), ("jump", "kiki", {"at": .6})]),
            ("dodo", "This is fun!", [("move", "ball", 380, None, .5), ("jump", "ball"), ("word", None)]),
            ("kiki", "Yes! Playing together is the best!", [("move", "ball", 700, None, .5), ("jump", "ball")]),
            ("sunny", "Taking turns is fair. Great job, friends! Bye bye!", [("move", "ball", 540, None, .5), ("confetti",), ("word", "GREAT JOB!", "rainbow"), ("jump", "dodo", {"at": .3}), ("jump", "kiki", {"at": .45})]),
        ]),

    "missing": dict(
        titel="THE MISSING NUMBER", lernziel="Zahlenreihe 1 bis 4: welche Zahl fehlt?",
        yt_titel="Which Number Is Missing? 🔢 Count 1 to 4 with Freddy #shorts",
        yt_text="Freddy the frog counts his number blocks: one, two... four? Something is missing! Which number is it? Help Freddy find it!",
        ziele="the number order 1, 2, 3, 4.", hashtags="#numbersforkids #countingforkids",
        tags=["missing number", "numbers for kids", "counting 1 to 4", "number order"],
        buehne=[("n1", "letter", dict(x=195, y=880, z=2, s=0, size=95, text="1", farbe="red")), ("n2", "letter", dict(x=425, y=880, z=2, s=0, size=95, text="2", farbe="orange")),
                ("n3", "letter", dict(x=655, y=880, z=2, s=0, size=95, text="3", farbe="green")), ("n4", "letter", dict(x=885, y=880, z=2, s=0, size=95, text="4", farbe="blue")),
                ("q", "text", dict(x=655, y=880, z=3, s=0, size=170, text="?", farbe="yellow")), ("freddy", "actor", dict(x=540, z=3, size=98))],
        zeilen=[
            ("sunny", "Hi friends! Freddy counts his number blocks.", [("show", "freddy"), ("show", "n1", {"at": .4}), ("show", "n2", {"at": .6}), ("show", "n4", {"at": .8})]),
            ("freddy", "One, two... four? Something is missing!", [("wiggle", "n1"), ("wiggle", "n2", {"at": .2}), ("wiggle", "n4", {"at": .45}), ("show", "q", {"at": .65})], .5),
            ("sunny", "Which number is missing? One, two, hmm, four.", [], .9),
            ("freddy", "Three! Three is missing!", [("hide", "q"), ("show", "n3", {"at": .1}), ("sparkle", "n3", {"at": .15}), ("word", "3", "green"), ("jump", "freddy", {"at": .4})]),
            ("sunny", "One, two, three, four. Now they are all here!", [("jump", "n1"), ("jump", "n2", {"at": .2}), ("jump", "n3", {"at": .4}), ("jump", "n4", {"at": .6}), ("word", None)]),
            ("sunny", "Great counting! Bye bye!", [("confetti",), ("word", "GREAT JOB!", "rainbow"), ("wave", "freddy")]),
        ]),

    "mix": dict(
        titel="MIXING COLORS", lernziel="Farben mischen: Rot + Gelb = Orange, Blau + Gelb = Gruen",
        yt_titel="Red and Yellow Make...? 🎨 Mixing Colors with Juju #shorts",
        yt_text="Juju the bunny mixes colors! Red and yellow: mix, mix, mix. What color do they make? And what happens with blue and yellow? Guess before Juju tells you!",
        ziele="mixing colors: red and yellow make orange, blue and yellow make green.", hashtags="#mixingcolors #learncolors",
        tags=["mixing colors", "color mixing for kids", "learn colors", "art for kids"],
        buehne=[("r", "ball", dict(x=440, y=900, z=2, s=0, size=160, farbe="red")), ("y1", "ball", dict(x=760, y=900, z=2, s=0, size=160, farbe="yellow")),
                ("o", "ball", dict(x=600, y=900, z=3, s=0, size=240, farbe="orange")), ("b", "ball", dict(x=440, y=900, z=2, s=0, size=160, farbe="blue")),
                ("y2", "ball", dict(x=760, y=900, z=2, s=0, size=160, farbe="yellow")), ("g", "ball", dict(x=600, y=900, z=3, s=0, size=240, farbe="green")),
                ("juju", "actor", dict(x=185, z=3, size=105))],
        zeilen=[
            ("sunny", "Hi friends! Juju has colors. Let's mix them!", [("show", "juju"), ("show", "r", {"at": .5}), ("show", "y1", {"at": .7})]),
            ("juju", "Red, and yellow. What will happen?", [("wiggle", "r"), ("wiggle", "y1", {"at": .35})], .4),
            ("sunny", "Mix, mix, mix!", [("move", "r", 600, None, .6), ("move", "y1", 600, None, .6), ("hide", "r", {"at": .7}), ("hide", "y1", {"at": .7}), ("show", "o", {"at": .7}), ("sparkle", "o", {"at": .75})]),
            ("juju", "Orange! Red and yellow make orange!", [("word", "ORANGE", "orange"), ("jump", "juju")]),
            ("sunny", "Now blue, and yellow. What will happen?", [("hide", "o"), ("word", None), ("show", "b", {"at": .2}), ("show", "y2", {"at": .45})], .5),
            ("sunny", "Mix, mix, mix!", [("move", "b", 600, None, .6), ("move", "y2", 600, None, .6), ("hide", "b", {"at": .7}), ("hide", "y2", {"at": .7}), ("show", "g", {"at": .7}), ("sparkle", "g", {"at": .75})]),
            ("juju", "Green! Blue and yellow make green!", [("word", "GREEN", "green"), ("jump", "juju")]),
            ("sunny", "You can mix colors! Great job! Bye bye!", [("confetti",), ("word", "GREAT JOB!", "rainbow"), ("wave", "juju", {"at": .4})]),
        ]),

    "tidy": dict(
        titel="CLEAN UP TIME", lernziel="Aufraeumen nach dem Spielen; zaehlen bis 3",
        yt_titel="Clean Up Time! 🧸 Juju Tidies Up Her Toys #shorts",
        yt_text="Playtime is over, and the toys are everywhere! Juju the bunny puts them back in the box: the ball, the star and the block. One, two, three. All clean!",
        ziele="tidying up after playing, counting to 3.", hashtags="#cleanuptime #goodhabits",
        tags=["clean up time", "tidy up for kids", "good habits for kids", "toys"],
        buehne=[("box", "box", dict(x=850, y=GY - 115, z=4, s=0, size=115)),
                ("ball", "ball", dict(x=150, y=GY - 20, z=5, s=0, size=120, farbe="red")), ("star", "star", dict(x=330, y=GY - 30, z=5, s=0, size=62)),
                ("blk", "letter", dict(x=510, y=GY - 30, z=5, s=0, size=60, text="A", farbe="green")), ("juju", "actor", dict(x=620, z=3, size=100))],
        zeilen=[
            ("sunny", "Hi friends! Playtime is over. Look at all the toys!", [("show", "juju"), ("show", "ball", {"at": .3}), ("show", "star", {"at": .45}), ("show", "blk", {"at": .6}), ("show", "box", {"at": .8})]),
            ("juju", "Clean up time! I can do it!", [("jump", "juju")]),
            ("sunny", "The ball goes in the box. One!", [("move", "ball", 850, GY - 290, .6, {"at": .1}), ("jump", "ball", {"at": .1}), ("hide", "ball", {"at": .5}), ("word", "1", "red", {"at": .65})]),
            ("sunny", "The star goes in the box. Two!", [("move", "star", 850, GY - 290, .6, {"at": .1}), ("jump", "star", {"at": .1}), ("hide", "star", {"at": .5}), ("word", "2", "orange", {"at": .65})]),
            ("sunny", "The block goes in the box. Three!", [("move", "blk", 850, GY - 290, .6, {"at": .1}), ("jump", "blk", {"at": .1}), ("hide", "blk", {"at": .5}), ("word", "3", "green", {"at": .65})]),
            ("juju", "All clean! That was fast!", [("jump", "juju"), ("sparkle", "box"), ("word", "ALL CLEAN!", "rainbow")]),
            ("sunny", "When we finish playing, we clean up. Great job, Juju! Bye bye!", [("confetti",), ("wave", "juju", {"at": .5})]),
        ]),

    "full": dict(
        titel="EMPTY AND FULL", lernziel="Gegensatz leer und voll; zaehlen bis 4",
        yt_titel="Momo Fills the Basket! 🧺 Empty and Full #shorts",
        yt_text="Momo the bear has a basket, but it is empty. He picks apples from the tree: one, two, three, four. Now the basket is full!",
        ziele="empty and full, counting to 4.", hashtags="#emptyandfull #oppositesforkids",
        tags=["empty and full", "opposites for kids", "counting to 4", "apple picking"],
        buehne=[("tree", "tree", dict(x=790, y=GY, z=0, s=1)),
                ("a1", "apple", dict(x=670, y=850, z=5, s=1, size=110)), ("a2", "apple", dict(x=790, y=780, z=5, s=1, size=110)),
                ("a3", "apple", dict(x=900, y=860, z=5, s=1, size=110)), ("a4", "apple", dict(x=760, y=990, z=5, s=1, size=110)),
                ("basket", "basket", dict(x=390, y=GY - 78, z=4, s=0, size=105)), ("momo", "actor", dict(x=140, z=3, size=105))],
        zeilen=[
            ("sunny", "Hi friends! Momo has a basket. Look inside. It is empty!", [("show", "momo"), ("show", "basket", {"at": .3}), ("word", "EMPTY", "blue", {"at": .75})]),
            ("momo", "My basket is empty. I need apples!", [("wiggle", "basket", {"at": .2})]),
            ("sunny", "One apple. Two apples.", [("word", None), ("drop", "a1", 335, GY - 165), ("drop", "a2", 445, GY - 165, {"at": .5})]),
            ("sunny", "Three apples. Four apples!", [("drop", "a3", 390, GY - 180), ("drop", "a4", 390, GY - 255, {"at": .5})]),
            ("sunny", "Now the basket is full!", [("word", "FULL", "red", {"at": .5}), ("sparkle", "basket", {"at": .5})]),
            ("momo", "Full! Now I can share with my friends!", [("jump", "momo")]),
            ("sunny", "Empty and full. Great job! Bye bye!", [("confetti",), ("word", "GREAT JOB!", "rainbow"), ("wave", "momo", {"at": .4})]),
        ]),

    "race": dict(
        titel="THE BIG RACE", lernziel="Reihenfolge: Erster, Zweiter, Dritter; nicht aufgeben",
        yt_titel="The Big Race! 🏁 First, Second, Third #shorts",
        yt_text="It is race day! Juju the bunny, Dodo the dog and little Pip run to the star. Who is first? Who is second? And who never gives up?",
        ziele="first, second and third, and never giving up.", hashtags="#firstsecondthird #mathforkids",
        tags=["first second third", "ordinal numbers for kids", "race for kids", "never give up"],
        buehne=[("road", "road", dict(x=0, y=GY, z=0, s=1)), ("star", "star", dict(x=985, y=GY - 360, z=1, s=0, size=70)),
                ("pip", "actor", dict(x=75, z=3, size=58)), ("dodo", "actor", dict(x=180, z=4, size=85)), ("juju", "actor", dict(x=300, z=5, size=85))],
        zeilen=[
            ("sunny", "Hi friends! It is race day! Juju, Dodo and Pip are ready.", [("show", "pip"), ("show", "dodo", {"at": .2}), ("show", "juju", {"at": .4}), ("show", "star", {"at": .7})]),
            ("sunny", "Ready, set, go!", [("word", "GO!", "green", {"at": .65}), ("move", "juju", 900, None, 1.3, {"at": .7}), ("move", "dodo", 720, None, 2.3, {"at": .7}), ("move", "pip", 560, None, 3.4, {"at": .7}),
                                        ("jump", "juju", {"at": .7}), ("jump", "dodo", {"at": .75}), ("jump", "pip", {"at": .8})], .6),
            ("sunny", "Juju is first!", [("word", "FIRST", "yellow"), ("sparkle", "juju")]),
            ("sunny", "Dodo is second!", [("word", "SECOND", "blue"), ("sparkle", "dodo")]),
            ("sunny", "And Pip is third!", [("word", "THIRD", "pink"), ("sparkle", "pip")]),
            ("pip", "I am small, but I did not give up!", [("jump", "pip"), ("jump", "pip", {"at": .5})]),
            ("juju", "Well done, Pip!", [("jump", "juju"), ("jump", "dodo", {"at": .3})]),
            ("sunny", "First, second, third. Everyone did great! Bye bye!", [("confetti",), ("word", "GREAT JOB!", "rainbow")]),
        ]),

    # ======== Folgen fuer 27.11. - 03.12.2026 ========
    "ispy": dict(
        titel="I SPY G H I", lernziel="Buchstaben G, H, I und ihre Woerter (grapes, hat, ice cream) mit dem Spiel 'I spy'",
        yt_titel="Kiki and Momo Play I Spy! 👀 Letters G H I #shorts",
        yt_text="👀 Kiki the cat and Momo the bear play I spy! Something starts with G, something sits on Momo's head 🎩 and something is cold and sweet. Can you guess before they do?",
        ziele="the letters G, H and I, with grapes, hat and ice cream.", hashtags="#learnletters #alphabetforkids #ispy",
        tags=["letters G H I", "I spy game for kids", "learn letters", "alphabet for kids", "phonics for kids", "letter G"],
        buehne=[("grapes", "grapes", dict(x=420, y=1290, z=4, s=0, size=82)), ("ice", "icecream", dict(x=655, y=1280, z=4, s=0, size=80)),
                ("kiki", "actor", dict(x=165, z=3, size=92)), ("momo", "actor", dict(x=900, z=3, size=100)),
                ("hat", "hat", dict(x=900, y=1262, z=5, s=0, size=72)),
                ("G", "letter", dict(x=540, y=830, z=6, s=0, size=110, text="G", farbe="purple")),
                ("Hl", "letter", dict(x=540, y=830, z=6, s=0, size=110, text="H", farbe="red")),
                ("I", "letter", dict(x=540, y=830, z=6, s=0, size=110, text="I", farbe="pink"))],
        zeilen=[
            ("sunny", "Hi friends! Kiki and Momo play I spy.", [("show", "kiki"), ("show", "momo", {"at": .2}), ("show", "hat", {"at": .3}),
                                                              ("show", "grapes", {"at": .55}), ("show", "ice", {"at": .7}), ("word", "I SPY", "blue", {"at": .75})]),
            ("kiki", "I spy something that starts with G!", [("word", None), ("show", "G", {"at": .7}), ("jump", "kiki")]),
            ("momo", "G? Hmm...", [("wiggle", "momo")], .5),
            ("kiki", "It is purple, and you can eat it!", [("wiggle", "grapes", {"at": .3})], .6),
            ("momo", "Grapes! G is for grapes!", [("move", "G", 420, 1050, .6), ("scale", "G", .55), ("sparkle", "grapes"), ("word", "GRAPES", "purple"), ("jump", "momo", {"at": .3})]),
            ("kiki", "Yes! Your turn, Momo.", [("word", None), ("wave", "kiki")]),
            ("momo", "I spy something that starts with H. It is on my head!", [("show", "Hl", {"at": .45}), ("wiggle", "hat", {"at": .75})], .5),
            ("kiki", "A hat! H is for hat!", [("move", "Hl", 900, 1015, .6), ("scale", "Hl", .55), ("word", "HAT", "red"), ("jump", "momo", {"at": .3}), ("jump", "hat", {"at": .3})]),
            ("sunny", "One more! I spy something that starts with I. It is cold, and sweet.", [("word", None), ("show", "I", {"at": .3}), ("wiggle", "ice", {"at": .75})], .7),
            ("kiki", "Ice cream! I is for ice cream!", [("move", "I", 650, 1035, .6), ("scale", "I", .55), ("sparkle", "ice"), ("word", "ICE CREAM", "pink"), ("jump", "kiki", {"at": .3})]),
            ("sunny", "G, H, I. Now you can play I spy too! Bye bye!", [("jump", "G"), ("jump", "Hl", {"at": .1}), ("jump", "I", {"at": .2}), ("confetti", {"at": .3}),
                                                                   ("word", "G H I", "rainbow"), ("wave", "kiki", {"at": .5}), ("wave", "momo", {"at": .55})]),
        ]),

    "bones": dict(
        titel="DODO'S TEN BONES", lernziel="Weiterzaehlen von 5 bis 10",
        yt_titel="Dodo Digs for Bones! 🦴 Count 6 to 10 #shorts",
        yt_text="🐶 Dodo the dog has five bones, but he wants ten! Dig, dig, dig... six, seven, eight, nine. 🦴 Oh no, no more bones! Who brings number ten?",
        ziele="counting on from 5 to 10.", hashtags="#countto10 #countingforkids #numbers",
        tags=["count to 10", "counting 6 to 10", "counting for kids", "numbers 1 to 10", "learn numbers", "counting on"],
        buehne=[("mound", "mound", dict(x=830, y=GY, z=1, s=0))]
               + [("b%d" % (i + 1), "bone", dict(x=150 + 195 * i, y=860, z=4, s=0, size=72)) for i in range(5)]
               + [("b%d" % (i + 6), "bone", dict(x=830, y=GY - 60, z=4, s=0, size=72)) for i in range(4)]
               + [("b10", "bone", dict(x=1250, y=GY - 60, z=6, s=1, size=72)),
                  ("dodo", "actor", dict(x=270, z=3, size=100)), ("kiki", "actor", dict(x=1300, z=5, size=92, s=1))],
        zeilen=[
            ("sunny", "Hi friends! Dodo the dog has five bones.", [("show", "dodo")] + [("show", "b%d" % (i + 1), {"at": .35 + i * .1}) for i in range(5)] + [("word", "5", "orange", {"at": .85})]),
            ("dodo", "One, two, three, four, five. But I want ten bones!", [("jump", "b%d" % (i + 1), {"at": .02 + i * .1}) for i in range(5)] + [("word", "10?", "purple", {"at": .7}), ("jump", "dodo", {"at": .7})]),
            ("sunny", "So Dodo digs in the garden. Dig, dig, dig!", [("word", None), ("show", "mound", {"at": .2}), ("move", "dodo", 600, None, .9, {"at": .2}), ("wiggle", "mound", {"at": .6}), ("jump", "dodo", {"at": .7})]),
            ("sunny", "Six!", [("show", "b6"), ("move", "b6", 150, 1010, .6), ("word", "6", "red")]),
            ("sunny", "Seven!", [("show", "b7"), ("move", "b7", 345, 1010, .6), ("word", "7", "orange"), ("wiggle", "mound")]),
            ("sunny", "Eight!", [("show", "b8"), ("move", "b8", 540, 1010, .6), ("word", "8", "green"), ("wiggle", "mound")]),
            ("sunny", "Nine!", [("show", "b9"), ("move", "b9", 735, 1010, .6), ("word", "9", "blue"), ("wiggle", "mound")]),
            ("dodo", "Dig, dig... Oh no! No more bones!", [("wiggle", "mound"), ("wiggle", "dodo", {"at": .5}), ("word", None)], .4),
            ("sunny", "Look! Here comes Kiki.", [("move", "kiki", 900, None, 1.0), ("move", "b10", 830, GY - 60, 1.0)]),
            ("kiki", "I found a bone for you, Dodo!", [("move", "b10", 930, 1010, .7, {"at": .4}), ("jump", "kiki")]),
            ("sunny", "Ten!", [("word", "10", "purple"), ("sparkle", "b10")]),
            ("dodo", "Ten bones! Thank you, Kiki!", [("jump", "dodo"), ("wave", "dodo", {"at": .5})]),
            ("sunny", "Six, seven, eight, nine, ten! Great counting! Bye bye!",
             [("jump", "b%d" % (i + 6), {"at": .02 + i * .1}) for i in range(5)] + [("confetti", {"at": .55}), ("word", "GREAT JOB!", "rainbow", {"at": .55}), ("jump", "kiki", {"at": .6})]),
        ]),

    "weather": dict(
        titel="JUJU'S WEATHER DAY", lernziel="Wetter: sonnig, regnerisch, windig; was man dann macht",
        yt_titel="Sun, Rain and Wind! ☔ Weather Words with Juju #shorts",
        yt_text="☀️ It is a sunny day, so Juju the bunny plays outside. But then a big gray cloud comes, drip, drop! ☔ And then, whoosh, the wind blows! What will Juju do?",
        ziele="the weather words sunny, rainy and windy.", hashtags="#weatherforkids #weather #rainyday",
        tags=["weather for kids", "sunny rainy windy", "weather words", "rainy day story", "umbrella", "learn weather"],
        buehne=[("cloud", "raincloud", dict(x=1350, y=720, z=1, s=1, size=150)),
                ("juju", "actor", dict(x=380, z=3, size=100)),
                ("umb", "umbrella", dict(x=430, y=1095, z=5, s=0, size=165)),
                ("wind", "wind", dict(x=0, y=0, z=6, s=1))],
        zeilen=[
            ("sunny", "Hi friends! Look, it is sunny today!", [("show", "juju"), ("word", "SUNNY", "yellow", {"at": .6})]),
            ("juju", "Yay! The sun is warm. I can play outside!", [("jump", "juju"), ("jump", "juju", {"at": .5})]),
            ("sunny", "Oh! Here comes a big gray cloud.", [("word", None), ("move", "cloud", 600, 720, 1.4, {"at": .2})]),
            ("sunny", "Drip, drop! Now it is rainy!", [("fade", "cloud", 1, .5), ("word", "RAINY", "blue", {"at": .5})]),
            ("juju", "I am getting wet! I need my umbrella.", [("wiggle", "juju")]),
            ("sunny", "Up goes the umbrella!", [("show", "umb", {"at": .3})]),
            ("juju", "Now I am nice and dry!", [("jump", "juju"), ("jump", "umb"), ("sparkle", "juju", {"at": .4})]),
            ("sunny", "Whoosh! Now it is windy!", [("fade", "wind", 1, .6), ("word", "WINDY", "green", {"at": .4}), ("tilt", "umb", .35, {"at": .4}), ("wiggle", "juju", {"at": .4})]),
            ("juju", "Hold on, umbrella! The wind blows the cloud away!",
             [("tilt", "umb", -.25), ("tilt", "umb", .3, {"at": .35}), ("fade", "cloud", 0, .4, {"at": .3}), ("move", "cloud", -450, 650, 1.8, {"at": .3}), ("tilt", "umb", 0, {"at": .75})]),
            ("sunny", "The wind stops, and the sun is back!", [("fade", "wind", 0, .6), ("hide", "umb", {"at": .5}), ("word", "SUNNY", "yellow", {"at": .5}), ("jump", "juju", {"at": .6})]),
            ("sunny", "Sunny, rainy, windy. What is the weather where you are? Bye bye!", [("confetti", {"at": .3}), ("word", "GREAT JOB!", "rainbow", {"at": .3}), ("wave", "juju", {"at": .5})]),
        ]),

    "night": dict(
        titel="GOOD NIGHT, MOMO", lernziel="Tag und Nacht: was wir am Tag und in der Nacht machen",
        yt_titel="Good Night, Momo! 🌙 Day and Night for Kids #shorts",
        yt_text="☀️ In the day, Momo the bear runs and plays in the sun. But then the sun goes down, and the moon and the stars come out. 🌙 Time for bed! And what happens in the morning?",
        ziele="day and night, and what we do at night.", hashtags="#dayandnight #bedtimestory #goodnight",
        tags=["day and night for kids", "bedtime story for kids", "good night", "moon and stars", "sleep routine", "morning and night"],
        buehne=[("nacht", "night", dict(x=0, y=0, z=-1, s=1, v=0)),
                ("bed", "bed", dict(x=760, y=GY, z=1, s=1)),
                ("momo", "actor", dict(x=240, z=3, size=100)),
                ("blank", "blanket", dict(x=760, y=GY - 95, z=4, s=0, size=100)),
                ("zzz", "text", dict(x=930, y=1080, z=5, s=0, size=80, text="Zzz", farbe="purple"))],
        zeilen=[
            ("sunny", "Hi friends! It is day. Momo plays in the sun.", [("show", "momo"), ("word", "DAY", "yellow", {"at": .3}), ("jump", "momo", {"at": .6})]),
            ("momo", "I love the day! I can run and play!", [("move", "momo", 420, None, .6), ("jump", "momo", {"at": .2}), ("move", "momo", 240, None, .6, {"at": .55}), ("jump", "momo", {"at": .6})]),
            ("sunny", "Now the sun goes down. It is getting dark.", [("word", None), ("fade", "nacht", .5, 2.0)]),
            ("momo", "Yawn! I am sleepy.", [("wiggle", "momo")], .5),
            ("sunny", "Look up! The moon and the stars. Now it is night.", [("fade", "nacht", 1, 1.2), ("word", "NIGHT", "purple", {"at": .7})]),
            ("sunny", "At night, we go to bed.", [("word", None), ("move", "momo", 700, GY - 200, 1.0), ("show", "blank", {"at": .7})]),
            ("momo", "Good night, moon! Good night, stars!", [("wave", "momo")]),
            ("sunny", "Shh. Momo is sleeping.", [("show", "zzz", {"at": .3}), ("word", "SHH...", "purple", {"at": .3})], .8),
            ("sunny", "Good morning! The sun comes up. It is day again!", [("fade", "nacht", 0, 1.6), ("hide", "zzz", {"at": .2}), ("word", "DAY", "yellow", {"at": .6}), ("jump", "momo", {"at": .7})]),
            ("momo", "Good morning, Sunny!", [("hide", "blank"), ("move", "momo", 420, GY - 150, .7), ("wave", "momo", {"at": .4})]),
            ("sunny", "Day and night. What do you do at night? Bye bye!", [("confetti", {"at": .3}), ("word", "GREAT JOB!", "rainbow", {"at": .3}), ("jump", "momo", {"at": .5})]),
        ]),

    "feelings": dict(
        titel="HOW DOES JUJU FEEL?", lernziel="Gefuehle benennen: froh, traurig, ueberrascht; Freunde helfen",
        yt_titel="Juju's Tower Falls Down! 😢 Happy, Sad, Surprised #shorts",
        yt_text="😊 Juju the bunny builds a tall tower and she is happy. But then the tower falls down, and Juju is sad. 😢 Can Dodo the dog help? And what surprise is waiting at the end?",
        ziele="the feelings happy, sad and surprised, and how friends help.", hashtags="#feelingsforkids #emotions #happyandsad",
        tags=["feelings for kids", "emotions for kids", "happy sad surprised", "social emotional learning", "friendship story", "how do you feel"],
        buehne=[("b1", "shape", dict(x=580, y=GY - 72, z=2, s=0, size=70, art="square", farbe="red")),
                ("b2", "shape", dict(x=580, y=GY - 214, z=2, s=0, size=70, art="square", farbe="yellow")),
                ("b3", "shape", dict(x=580, y=GY - 356, z=2, s=0, size=70, art="square", farbe="blue")),
                ("b4", "shape", dict(x=580, y=GY - 498, z=2, s=0, size=70, art="square", farbe="green")),
                ("star", "star", dict(x=580, y=GY - 640, z=2, s=0, size=62)),
                ("juju", "actor", dict(x=210, z=3, size=95)), ("dodo", "actor", dict(x=1300, z=3, size=92, s=1)),
                ("happy", "face", dict(x=215, y=820, z=5, s=0, size=95, art="happy")),
                ("sad", "face", dict(x=215, y=820, z=5, s=0, size=95, art="sad")),
                ("surp", "face", dict(x=215, y=820, z=5, s=0, size=95, art="surprised"))],
        zeilen=[
            ("sunny", "Hi friends! Juju builds a tall tower.", [("show", "juju"), ("show", "b1", {"at": .35}), ("show", "b2", {"at": .5}), ("show", "b3", {"at": .65})]),
            ("juju", "Look at my tower! I am happy!", [("show", "happy", {"at": .5}), ("word", "HAPPY", "yellow", {"at": .5}), ("jump", "juju", {"at": .5})]),
            ("sunny", "Oh no! The tower falls down!", [("word", None), ("wiggle", "b3"), ("move", "b3", 420, GY - 72, .5, {"at": .4}), ("move", "b2", 760, GY - 72, .5, {"at": .45})]),
            ("juju", "My tower! I am sad.", [("hide", "happy"), ("show", "sad", {"at": .1}), ("word", "SAD", "blue", {"at": .5}), ("wiggle", "juju", {"at": .3})], .5),
            ("sunny", "Here comes Dodo.", [("word", None), ("move", "dodo", 920, None, 1.0)]),
            ("dodo", "Don't be sad, Juju. Let's build it again, together!", [("wave", "dodo")]),
            ("sunny", "One, two, three, four. Up it goes!", [("move", "b2", 580, GY - 214, .5, {"at": .2}), ("move", "b3", 580, GY - 356, .5, {"at": .45}), ("show", "b4", {"at": .7}),
                                                         ("jump", "dodo", {"at": .2}), ("jump", "juju", {"at": .45})]),
            ("juju", "Our tower is even taller! I am happy again!", [("hide", "sad"), ("show", "happy", {"at": .1}), ("word", "HAPPY", "yellow", {"at": .4}), ("jump", "juju", {"at": .4})]),
            ("sunny", "And look! Dodo has a surprise.", [("word", None), ("show", "star", {"at": .5}), ("sparkle", "star", {"at": .55})]),
            ("juju", "Wow! A star! I am surprised!", [("hide", "happy"), ("show", "surp", {"at": .1}), ("word", "SURPRISED", "orange", {"at": .45}), ("jump", "juju", {"at": .2})]),
            ("sunny", "Happy, sad, surprised. How do you feel today? Bye bye!", [("hide", "surp", {"at": .5}), ("show", "happy", {"at": .55}), ("confetti", {"at": .55}),
                                                                                ("word", "GREAT JOB!", "rainbow", {"at": .55}), ("wave", "juju", {"at": .6}), ("wave", "dodo", {"at": .65})]),
        ]),

    "trip": dict(
        titel="DODO'S BIG TRIP", lernziel="Fahrzeuge und wo sie fahren: Auto (Strasse), Boot (Wasser), Flugzeug (Luft)",
        yt_titel="Dodo's Big Trip! 🚗 Car, Boat and Plane #shorts",
        yt_text="🐶 Dodo the dog goes on a big trip! First he drives a car. 🚗 Then he comes to the water, and a car cannot swim! What does Dodo take next? And how does he get up into the sky? ✈️",
        ziele="car, boat and plane, and where they go: road, water and sky.", hashtags="#vehiclesforkids #transportation #carsforkids",
        tags=["vehicles for kids", "car boat plane", "transportation for kids", "learn vehicles", "where do vehicles go", "toddler vehicles"],
        buehne=[("road", "road", dict(x=0, y=GY, z=0, s=1)), ("pond", "pond", dict(x=540, y=GY + 15, z=0, s=0)),
                ("dodo", "actor", dict(x=-300, y=GY - 170, z=3, size=62, s=1)),
                ("car", "car", dict(x=-300, y=GY + 40, z=4, s=1, size=115, farbe="red")),
                ("boat", "boat", dict(x=-400, y=GY, z=4, s=1, size=100, farbe="blue")),
                ("plane", "plane", dict(x=-400, y=880, z=4, s=1, size=110))],
        zeilen=[
            ("sunny", "Hi friends! Dodo goes on a big trip. First, he drives a car!", [("move", "car", 540, None, 1.6), ("move", "dodo", 510, None, 1.6), ("word", "CAR", "red", {"at": .7})]),
            ("dodo", "Vroom, vroom! A car drives on the road.", [("wiggle", "car"), ("wave", "dodo")]),
            ("sunny", "Now Dodo comes to the water. A car cannot swim!", [("word", None), ("move", "car", 1450, None, 1.2), ("move", "dodo", 1420, None, 1.2), ("hide", "road", {"at": .45}), ("show", "pond", {"at": .55})]),
            ("sunny", "So Dodo takes a boat.", [("place", "dodo", -430, GY - 120), ("move", "boat", 560, None, 1.4), ("move", "dodo", 530, None, 1.4), ("word", "BOAT", "blue", {"at": .6})]),
            ("dodo", "Toot, toot! A boat floats on the water.", [("wiggle", "boat"), ("wave", "dodo")]),
            ("sunny", "Now Dodo wants to go up, up, high in the sky!", [("word", None), ("move", "boat", 1500, None, 1.3), ("move", "dodo", 1470, None, 1.3), ("hide", "pond", {"at": .6})]),
            ("sunny", "So Dodo takes a plane!", [("place", "dodo", -360, 805), ("move", "plane", 540, 900, 1.5), ("move", "dodo", 580, 825, 1.5), ("word", "PLANE", "green", {"at": .6})]),
            ("dodo", "Zoom! A plane flies in the sky. Wheee!", [("move", "plane", 540, 760, .8, {"at": .3}), ("move", "dodo", 580, 685, .8, {"at": .3}), ("wave", "dodo")]),
            ("sunny", "A car on the road, a boat on the water, and a plane in the sky. Great trip, Dodo! Bye bye!",
             [("word", "GREAT TRIP!", "rainbow", {"at": .6}), ("confetti", {"at": .6}), ("move", "plane", 1500, 560, 1.6, {"at": .72}), ("move", "dodo", 1540, 485, 1.6, {"at": .72})]),
        ]),

    "wash": dict(
        titel="CLEAN HANDS, MOMO!", lernziel="Haende waschen in 5 Schritten: nass, Seife, schrubben, abspuelen, abtrocknen",
        yt_titel="Momo Washes His Hands! 🧼 Handwashing Steps #shorts",
        yt_text="🐻 Momo the bear played in the mud, and now he wants to eat an apple! 🍎 But wait, his hands are dirty. Juju shows him how to wash his hands, step by step. 🧼",
        ziele="washing hands: water, soap, scrub, rinse and dry.", hashtags="#washyourhands #goodhabits #healthyhabits",
        tags=["wash your hands", "handwashing for kids", "good habits for kids", "healthy habits", "hygiene for kids", "soap and water"],
        buehne=[("sink", "sink", dict(x=650, y=GY, z=1, s=0)),
                ("momo", "actor", dict(x=250, z=3, size=100)),
                ("mud", "mud", dict(x=250, y=GY - 150, z=4, s=0, size=100)),
                ("bub", "bubbles", dict(x=420, y=1330, z=5, s=0, size=100)),
                ("juju", "actor", dict(x=920, z=3, size=90)),
                ("towel", "towel", dict(x=830, y=1320, z=5, s=0, size=90)),
                ("ap", "apple", dict(x=290, y=1420, z=5, s=0, size=95))],
        zeilen=[
            ("sunny", "Hi friends! Momo played in the mud. Look at him!", [("show", "momo"), ("show", "mud", {"at": .55}), ("word", "MUDDY", "brown", {"at": .6})]),
            ("momo", "I am hungry! Can I eat an apple now?", [("jump", "momo")]),
            ("juju", "Wait, Momo! First, we wash our hands!", [("show", "juju"), ("wave", "juju"), ("show", "sink", {"at": .5}), ("word", None)]),
            ("sunny", "Turn on the water. Make your hands wet.", [("move", "momo", 400, None, .7), ("move", "mud", 400, None, .7), ("set", "sink", 1, {"at": .4}), ("word", "WET", "blue", {"at": .4})]),
            ("sunny", "Now the soap. Scrub, scrub, scrub!", [("show", "bub", {"at": .3}), ("word", "SOAP", "pink", {"at": .3}), ("wiggle", "momo", {"at": .5})]),
            ("sunny", "Scrub the front, the back, and between your fingers.", [("wiggle", "momo"), ("wiggle", "bub", {"at": .4}), ("word", "SCRUB", "purple")]),
            ("sunny", "Rinse the soap away.", [("hide", "bub", {"at": .3}), ("hide", "mud", {"at": .5}), ("word", "RINSE", "blue", {"at": .3})]),
            ("sunny", "Turn off the water, and dry your hands.", [("set", "sink", 0, {"at": .2}), ("show", "towel", {"at": .55}), ("word", "DRY", "green", {"at": .55})]),
            ("momo", "Clean hands! Now I can eat my apple!", [("hide", "towel"), ("show", "ap", {"at": .5}), ("sparkle", "momo"), ("jump", "momo", {"at": .2}), ("word", "CLEAN!", "rainbow")]),
            ("sunny", "Wet, soap, scrub, rinse, dry. Great job! Bye bye!", [("confetti", {"at": .5}), ("word", "GREAT JOB!", "rainbow", {"at": .5}), ("wave", "juju", {"at": .6}), ("jump", "momo", {"at": .6})]),
        ]),

    "drum": dict(
        titel="FAST AND SLOW", lernziel="Gegensatz schnell und langsam (Musik und Bewegung)",
        yt_titel="Kiki's Drum Dance! 🥁 Fast and Slow #shorts",
        yt_text="🥁 Kiki the cat plays the drum and her friends dance! Boom, boom, boom, fast! Pip and Freddy hop and hop... until little Pip is tired. 🐥 Can Kiki play slow? Dance along!",
        ziele="fast and slow, with music and moving.", hashtags="#fastandslow #oppositesforkids #movementforkids",
        tags=["fast and slow", "opposites for kids", "movement song for kids", "dance for kids", "drum for kids", "music and movement"],
        buehne=[("kiki", "actor", dict(x=180, z=3, size=92)), ("drum", "drum", dict(x=210, y=GY - 30, z=4, s=0, size=85)),
                ("pip", "actor", dict(x=560, z=3, size=62)), ("freddy", "actor", dict(x=830, z=3, size=82))],
        zeilen=[
            ("sunny", "Hi friends! Kiki has a drum. Let's dance!", [("show", "kiki"), ("show", "drum", {"at": .3}), ("show", "pip", {"at": .55}), ("show", "freddy", {"at": .7})]),
            ("kiki", "When I play fast, you hop fast!", [("wiggle", "drum")]),
            ("kiki", "Boom, boom, boom, boom, boom!", [("word", "FAST", "red")] + [x for k in range(5) for x in
                                                                              (("wiggle", "drum", {"at": k * .19}), ("jump", "pip", {"at": k * .19, "d": .3}), ("jump", "freddy", {"at": k * .19, "d": .3}))]),
            ("pip", "Fast, fast, fast! Phew, I am tired!", [("jump", "pip", {"d": .3}), ("jump", "pip", {"at": .2, "d": .3}), ("wiggle", "pip", {"at": .55})], .5),
            ("kiki", "Then I play slow. Hop slow!", [("word", None)]),
            ("kiki", "Boom... boom... boom...", [("word", "SLOW", "blue")] + [x for k in range(3) for x in
                                                                       (("wiggle", "drum", {"at": k * .33}), ("jump", "pip", {"at": k * .33, "d": 1.0}), ("jump", "freddy", {"at": k * .33, "d": 1.0}))]),
            ("freddy", "Slow is nice too!", [("jump", "freddy", {"d": 1.0})]),
            ("sunny", "Now you! Fast!", [("word", "FAST", "red"), ("wiggle", "drum", {"at": .3}), ("jump", "pip", {"at": .3, "d": .3}), ("jump", "freddy", {"at": .5, "d": .3}),
                                     ("jump", "pip", {"at": .7, "d": .3}), ("jump", "freddy", {"at": .9, "d": .3})]),
            ("sunny", "And slow...", [("word", "SLOW", "blue"), ("wiggle", "drum"), ("jump", "pip", {"d": 1.1}), ("jump", "freddy", {"at": .1, "d": 1.1})], .5),
            ("sunny", "Fast and slow. You are great dancers! Bye bye!", [("confetti", {"at": .3}), ("word", "GREAT JOB!", "rainbow", {"at": .3}), ("jump", "kiki", {"at": .4}),
                                                                       ("jump", "pip", {"at": .5}), ("jump", "freddy", {"at": .6})]),
        ]),

    "week": dict(
        titel="PIP'S PARTY WEEK", lernziel="Die sieben Wochentage in der richtigen Reihenfolge",
        yt_titel="When Is Pip's Party? 🎉 Days of the Week #shorts",
        yt_text="🐥 Pip the chick has a party on Sunday, and he can't wait! Is it Sunday today? Not yet! 📅 Count the days of the week with Pip, from Monday all the way to party day. 🎉",
        ziele="the seven days of the week, in order.", hashtags="#daysoftheweek #learnenglish #calendarforkids",
        tags=["days of the week", "days of the week for kids", "Monday to Sunday", "calendar for kids", "learn days", "week for kids"],
        buehne=[(k, "card", dict(x=x, y=y, z=2, s=0, size=74, text=k, farbe=f)) for k, x, y, f in
                [("MON", 155, 760, "red"), ("TUE", 385, 760, "orange"), ("WED", 615, 760, "yellow"), ("THU", 845, 760, "green"),
                 ("FRI", 270, 950, "blue"), ("SAT", 500, 950, "purple"), ("SUN", 730, 950, "pink")]]
               + [("bl1", "balloon", dict(x=330, y=1180, z=2, size=95, farbe="red")), ("bl2", "balloon", dict(x=780, y=1150, z=2, size=95, farbe="blue")),
                  ("gift", "gift", dict(x=800, y=GY - 80, z=3, s=0, size=80, farbe="green")),
                  ("pip", "actor", dict(x=540, z=4, size=78))],
        zeilen=[
            ("sunny", "Hi friends! Pip has a party on Sunday!", [("show", "pip"), ("jump", "pip", {"at": .6}), ("word", "SUNDAY", "pink", {"at": .65})]),
            ("pip", "Is it Sunday today?", [("wiggle", "pip")], .5),
            ("sunny", "Not yet! Today is Monday.", [("word", None), ("show", "MON", {"at": .6})]),
            ("sunny", "Tuesday.", [("show", "TUE"), ("jump", "pip")]),
            ("sunny", "Wednesday.", [("show", "WED"), ("jump", "pip")]),
            ("sunny", "Thursday.", [("show", "THU"), ("jump", "pip")]),
            ("pip", "Is it Sunday now?", [("wiggle", "pip")], .3),
            ("sunny", "Not yet! Friday.", [("show", "FRI", {"at": .5}), ("jump", "pip", {"at": .5})]),
            ("sunny", "Saturday.", [("show", "SAT"), ("jump", "pip")]),
            ("sunny", "And now, Sunday! Party day!", [("show", "SUN", {"at": .3}), ("sparkle", "SUN", {"at": .3}), ("show", "bl1", {"at": .6}), ("show", "bl2", {"at": .65}),
                                                     ("show", "gift", {"at": .7}), ("confetti", {"at": .6}), ("word", "PARTY DAY!", "rainbow", {"at": .6})]),
            ("pip", "Hooray! A week has seven days!", [("jump", "pip"), ("jump", "pip", {"at": .5}), ("word", "7 DAYS", "green", {"at": .6})]),
            ("sunny", "Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday! Bye bye!",
             [("jump", k, {"at": .02 + i * .11}) for i, k in enumerate(["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"])] + [("wave", "pip", {"at": .8})]),
        ]),

    "cookies": dict(
        titel="MOMO'S COOKIES", lernziel="Formen: Herz, Stern, Rechteck",
        yt_titel="Momo Bakes Shape Cookies! 🍪 Heart, Star, Rectangle #shorts",
        yt_text="🍪 Momo the bear bakes cookies for his friends, and every cookie has a different shape! ❤️ A heart, a star and a rectangle. Which one is for Juju, Pip and Dodo?",
        ziele="the shapes heart, star and rectangle.", hashtags="#learnshapes #shapesforkids #baking",
        tags=["shapes for kids", "heart star rectangle", "learn shapes", "shape cookies", "baking story for kids", "preschool shapes"],
        buehne=[("tray", "tray", dict(x=540, y=1035, z=1, s=0)),
                ("heart", "cookie", dict(x=270, y=935, z=4, s=0, size=92, art="heart", farbe="red")),
                ("star", "cookie", dict(x=540, y=925, z=4, s=0, size=88, art="star", farbe="yellow")),
                ("rect", "cookie", dict(x=815, y=950, z=4, s=0, size=76, art="rect", farbe="orange")),
                ("momo", "actor", dict(x=170, z=3, size=100)),
                ("juju", "actor", dict(x=500, z=3, size=80, s=0)), ("pip", "actor", dict(x=720, z=3, size=56, s=0)), ("dodo", "actor", dict(x=925, z=3, size=80, s=0))],
        zeilen=[
            ("sunny", "Hi friends! Momo bakes cookies today.", [("show", "momo"), ("show", "tray", {"at": .6})]),
            ("momo", "I make cookies in different shapes!", [("jump", "momo")]),
            ("sunny", "The first cookie is a heart.", [("show", "heart", {"at": .6}), ("word", "HEART", "red", {"at": .6})]),
            ("momo", "A heart, for my friend Juju!", [("wiggle", "heart")]),
            ("sunny", "Next, a star. A star has five points.", [("show", "star", {"at": .2}), ("word", "STAR", "yellow", {"at": .2}), ("wiggle", "star", {"at": .6})]),
            ("sunny", "And a rectangle. It has two long sides, and two short sides.", [("show", "rect", {"at": .2}), ("word", "RECTANGLE", "orange", {"at": .2}), ("wiggle", "rect", {"at": .55})]),
            ("momo", "The cookies are ready! Come, friends!", [("word", None), ("wave", "momo"), ("show", "juju", {"at": .5}), ("show", "pip", {"at": .65}), ("show", "dodo", {"at": .8})]),
            ("sunny", "A heart for Juju, a star for Pip, and a rectangle for Dodo.",
             [("move", "heart", 500, 1455, .7, {"at": .05}), ("scale", "heart", .5, {"at": .05}), ("move", "star", 720, 1460, .7, {"at": .35}), ("scale", "star", .42, {"at": .35}),
              ("move", "rect", 925, 1460, .7, {"at": .65}), ("scale", "rect", .5, {"at": .65}), ("hide", "tray", {"at": .8})]),
            ("juju", "Yummy! Thank you, Momo!", [("jump", "juju"), ("jump", "pip", {"at": .15}), ("jump", "dodo", {"at": .3})]),
            ("sunny", "Heart, star, rectangle. Which cookie do you like? Bye bye!", [("confetti", {"at": .3}), ("word", "GREAT JOB!", "rainbow", {"at": .3}), ("wave", "momo", {"at": .5})]),
        ]),

    "please": dict(
        titel="THE MAGIC WORD", lernziel="Hoeflich fragen: bitte (please) sagen",
        yt_titel="What Is the Magic Word? 🍌 Say Please with Pip #shorts",
        yt_text="🐥 Pip the chick sees a yummy banana and shouts: give me the banana! 🍌 Hmm, Momo the bear waits. What is the magic word? A little story about saying please. ✨",
        ziele="asking nicely and saying please.", hashtags="#sayplease #mannersforkids #kindness",
        tags=["say please", "manners for kids", "magic words", "please and thank you", "polite kids", "kindness story"],
        buehne=[("basket", "basket", dict(x=700, y=GY - 78, z=4, s=0, size=105)),
                ("ban", "banana", dict(x=650, y=GY - 190, z=3, s=0, size=95)), ("ora", "orange", dict(x=760, y=GY - 185, z=3, s=0, size=105)),
                ("momo", "actor", dict(x=950, z=2, size=95)),
                ("pip", "actor", dict(x=-200, z=3, size=62, s=1)), ("kiki", "actor", dict(x=-250, z=3, size=82, s=1))],
        zeilen=[
            ("sunny", "Hi friends! Momo has a basket of fruit.", [("show", "momo"), ("show", "basket", {"at": .5}), ("show", "ban", {"at": .65}), ("show", "ora", {"at": .75})]),
            ("pip", "Banana! Give me the banana!", [("move", "pip", 170, None, .8), ("jump", "pip", {"at": .5})]),
            ("momo", "Hmm...", [("wiggle", "momo")], .7),
            ("sunny", "Pip, what is the magic word?", [("word", "?", "yellow", {"at": .4})], .6),
            ("pip", "Oh! May I have the banana, please?", [("word", "PLEASE", "green", {"at": .7}), ("jump", "pip", {"at": .7})]),
            ("momo", "Of course! Here you go, Pip.", [("word", None), ("move", "ban", 290, GY - 70, .8, {"at": .4}), ("wave", "momo")]),
            ("pip", "Thank you, Momo!", [("jump", "pip"), ("word", "THANK YOU", "pink")]),
            ("sunny", "Here comes Kiki.", [("word", None), ("move", "kiki", 430, None, 1.0)]),
            ("kiki", "Momo, may I have an orange, please?", [("word", "PLEASE", "green", {"at": .75})]),
            ("momo", "Yes! You asked so nicely.", [("move", "ora", 530, GY - 60, .8, {"at": .3}), ("jump", "momo")]),
            ("kiki", "Thank you!", [("jump", "kiki"), ("word", "THANK YOU", "pink")]),
            ("sunny", "Please and thank you are magic words. Great job! Bye bye!", [("confetti", {"at": .4}), ("word", "MAGIC WORDS!", "rainbow", {"at": .4}),
                                                                                  ("jump", "pip", {"at": .5}), ("jump", "kiki", {"at": .6})]),
        ]),

    "cocoa": dict(
        titel="HOT COCOA", welt="winter", lernziel="Heiss, kalt und warm; vorsichtig sein mit heissen Getraenken",
        yt_titel="Too Hot for Momo! ☕ Hot, Cold and Warm #shorts",
        yt_text="❄️ It is a snowy day and Momo the bear is so cold! Juju the bunny brings him a cup of hot cocoa. ☕ But careful, it is hot! What can Momo do?",
        ziele="hot, cold and warm, and being careful with hot drinks.", hashtags="#hotandcold #oppositesforkids #winterforkids",
        tags=["hot and cold", "opposites for kids", "hot cold warm", "winter story for kids", "hot cocoa", "safety for kids"],
        buehne=[("momo", "actor", dict(x=280, z=3, size=105)), ("juju", "actor", dict(x=1300, z=3, size=90, s=1)),
                ("mug", "mug", dict(x=1220, y=GY - 60, z=5, s=1, size=95, v=1))],
        zeilen=[
            ("sunny", "Hi friends! Look, snow! It is cold today.", [("show", "momo"), ("word", "COLD", "blue", {"at": .6}), ("wiggle", "momo", {"at": .6})]),
            ("momo", "So cold! My paws are cold!", [("wiggle", "momo"), ("wiggle", "momo", {"at": .5})]),
            ("juju", "Here, Momo! I made hot cocoa.", [("move", "juju", 820, None, 1.0), ("move", "mug", 720, None, 1.0), ("word", None)]),
            ("sunny", "Careful! The cocoa is hot!", [("move", "mug", 470, GY - 60, .7), ("word", "HOT", "red", {"at": .5}), ("wiggle", "mug", {"at": .5})]),
            ("momo", "Ouch! Too hot! What can I do?", [("jump", "momo"), ("wiggle", "momo", {"at": .5})]),
            ("juju", "Blow on it, and wait a little.", [("wave", "juju")]),
            ("momo", "Whoo, whoo.", [("fade", "mug", .35, 1.5), ("wiggle", "mug")], .6),
            ("sunny", "Now the cocoa is warm. Not too hot, and not too cold.", [("word", "WARM", "orange", {"at": .2}), ("sparkle", "mug", {"at": .2})]),
            ("momo", "Mmm! Warm cocoa! Thank you, Juju!", [("jump", "momo"), ("jump", "juju", {"at": .5})]),
            ("sunny", "Cold snow, hot cocoa, and warm Momo. Great job! Bye bye!", [("confetti", {"at": .5}), ("word", "GREAT JOB!", "rainbow", {"at": .5}), ("wave", "momo", {"at": .6})]),
        ]),

    "float": dict(
        titel="SINK OR FLOAT?", lernziel="Schwimmt es oder sinkt es? Vermuten und ausprobieren",
        yt_titel="Will It Float? 🐸 Sink or Float with Freddy #shorts",
        yt_text="🐸 Freddy the frog plays a game at the pond: sink or float? A leaf, a stone and a ball. 🍃 Which one goes down, down, down? Make your guess before the splash! 💦",
        ziele="sink and float, and guessing before you try.", hashtags="#sinkorfloat #scienceforkids #experiment",
        tags=["sink or float", "science for kids", "preschool science", "float and sink experiment", "water play", "guessing game for kids"],
        buehne=[("pond", "pond", dict(x=560, y=GY + 15, z=0, s=1)),
                ("leaf", "leaf", dict(x=330, y=1080, z=4, s=0, size=78, farbe="green")),
                ("stone", "stone", dict(x=330, y=1080, z=4, s=0, size=75)),
                ("ball", "ball", dict(x=330, y=1080, z=4, s=0, size=125, farbe="red")),
                ("freddy", "actor", dict(x=110, z=3, size=80))],
        zeilen=[
            ("sunny", "Hi friends! Freddy plays a game at the pond. Sink, or float?", [("show", "freddy"), ("word", "SINK OR FLOAT?", "blue", {"at": .6})]),
            ("freddy", "First, a leaf. Will it sink, or float?", [("show", "leaf", {"at": .2}), ("wiggle", "leaf", {"at": .7})], .9),
            ("sunny", "Splash!", [("word", None), ("drop", "leaf", 400, GY - 5)]),
            ("freddy", "It floats! The leaf floats on the water.", [("word", "FLOAT", "green", {"at": .2}), ("jump", "freddy")]),
            ("freddy", "Now, a stone. Sink, or float?", [("word", None), ("show", "stone", {"at": .2}), ("wiggle", "stone", {"at": .6})], .9),
            ("sunny", "Splash!", [("drop", "stone", 570, GY), ("move", "stone", 570, GY + 45, .8, {"at": .6}), ("hide", "stone", {"at": .9})]),
            ("freddy", "It sinks! The stone goes down, down, down.", [("word", "SINK", "blue", {"at": .2}), ("wiggle", "freddy")]),
            ("freddy", "And my ball. Sink, or float?", [("word", None), ("show", "ball", {"at": .2}), ("wiggle", "ball", {"at": .6})], .9),
            ("sunny", "Splash!", [("drop", "ball", 740, GY - 22)]),
            ("freddy", "It floats! Yay!", [("word", "FLOAT", "green"), ("jump", "freddy"), ("sparkle", "ball")]),
            ("sunny", "Float, sink, float! Try it in the bath, with a grown-up. Bye bye!", [("jump", "leaf"), ("jump", "ball", {"at": .1}), ("confetti", {"at": .3}),
                                                                                           ("word", "GREAT JOB!", "rainbow", {"at": .3}), ("wave", "freddy", {"at": .5})]),
        ]),

    "autumn": dict(
        titel="AUTUMN LEAVES", lernziel="Herbst: Blaetter in Rot, Gelb, Orange und Braun",
        yt_titel="Juju's Leaf Pile! 🍂 Autumn Colors #shorts",
        yt_text="🍂 It is autumn, and the leaves fall from the tree: red, yellow, orange and brown! Juju the bunny makes a big leaf pile. But then Dodo the dog comes running... 🐶 Jump!",
        ziele="autumn and the leaf colors red, yellow, orange and brown.", hashtags="#autumnforkids #autumnleaves #learncolors",
        tags=["autumn for kids", "fall leaves", "autumn colors", "seasons for kids", "leaf pile", "learn colors"],
        buehne=[("tree", "atree", dict(x=760, y=GY, z=0, s=1)),
                ("pile", "pile", dict(x=520, y=GY - 5, z=4, s=0, size=100))]
               + [("l%d" % i, "leaf", dict(x=x, y=y, z=5, s=0, size=54, farbe=f)) for i, (x, y, f) in
                  enumerate([(620, 820, "red"), (880, 900, "red"), (700, 700, "yellow"), (940, 760, "yellow"), (590, 960, "orange"), (830, 1020, "brown")])]
               + [("juju", "actor", dict(x=200, z=3, size=95)), ("dodo", "actor", dict(x=1300, z=3, size=90, s=1))],
        zeilen=[
            ("sunny", "Hi friends! It is autumn. The leaves change color.", [("show", "juju"), ("wiggle", "tree", {"at": .3}), ("word", "AUTUMN", "orange", {"at": .3})]
             + [("show", "l%d" % i, {"at": .45 + i * .08}) for i in range(6)]),
            ("sunny", "Red leaves.", [("drop", "l0", 380, GY - 20), ("drop", "l1", 960, GY - 15, {"at": .2}), ("word", "RED", "red")]),
            ("sunny", "Yellow leaves.", [("drop", "l2", 470, GY - 10), ("drop", "l3", 650, GY - 25, {"at": .2}), ("word", "YELLOW", "yellow")]),
            ("sunny", "Orange leaves, and brown leaves!", [("drop", "l4", 560, GY - 15), ("word", "ORANGE", "orange"), ("drop", "l5", 850, GY - 20, {"at": .5}), ("word", "BROWN", "brown", {"at": .5})]),
            ("juju", "So many leaves! I make a big pile.", [("word", None)] + [("move", "l%d" % i, 520, GY - 60, .5, {"at": .3 + i * .1}) for i in range(6)]
             + [("show", "pile", {"at": .85}), ("jump", "juju", {"at": .3})]),
            ("sunny", "Here comes Dodo!", [("move", "dodo", 900, None, 1.0)]),
            ("dodo", "A leaf pile! Jump!", [("move", "dodo", 560, None, .5, {"at": .4}), ("jump", "dodo", {"at": .4}), ("hide", "pile", {"at": .65})]
             + [("move", "l%d" % i, x, y, .4, {"at": .65}) for i, (x, y) in enumerate([(300, 1050), (420, 950), (560, 900), (700, 960), (820, 1060), (220, 1150)])]),
            ("juju", "Oh, Dodo! The leaves are everywhere!", [("wiggle", "juju")]
             + [("drop", "l%d" % i, x, GY - 15, {"at": .05 + i * .04}) for i, x in enumerate([330, 430, 690, 780, 940, 470])]),
            ("dodo", "Sorry, Juju. But jumping is so much fun!", [("jump", "dodo"), ("jump", "dodo", {"at": .5})]),
            ("juju", "You are right! Let's jump together!", [("jump", "juju", {"at": .5}), ("jump", "dodo", {"at": .55})]
             + [("move", "l%d" % i, x, y, .4, {"at": .6}) for i, (x, y) in enumerate([(300, 1100), (460, 980), (600, 930), (740, 1000), (880, 1080), (180, 1180)])]),
            ("sunny", "Red, yellow, orange, brown. Autumn is fun! Bye bye!", [("drop", "l%d" % i, x, GY - 15, {"at": .02 + i * .04}) for i, x in enumerate([330, 430, 690, 780, 950, 480])]
             + [("confetti", {"at": .55}), ("word", "AUTUMN!", "rainbow", {"at": .55}), ("wave", "juju", {"at": .6}), ("jump", "dodo", {"at": .65})]),
        ]),
}


# ---------------- Requisiten ----------------

def apfel(ctx, x, y, r, t):
    if r < 3:
        return
    lw = max(3, r * .13)
    ctx.move_to(x, y - r * .8); ctx.curve_to(x, y - r * 1.2, x + r * .1, y - r * 1.3, x + r * .15, y - r * 1.4)
    ctx.set_source_rgb(*rgb("7a4a21")); ctx.set_line_width(lw); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.stroke()
    ellipse(ctx, x + r * .45, y - r * 1.1, r * .38, r * .18, -.5); fuell(ctx, rgb("4cd964"), lw * .8)
    ellipse(ctx, x, y, r, r * .95); fuell(ctx, COLORS["red"], lw)
    ellipse(ctx, x - r * .4, y - r * .4, r * .2, r * .3, .6); fuell(ctx, kw.WEISS, alpha=.7)


def baum(ctx, x, y, t, wackel=0):
    ctx.rectangle(x - 48, y - 470, 96, 480); fuell(ctx, rgb("b0733c"), 9)
    ctx.save(); ctx.translate(x, y - 590); ctx.rotate(wackel * .05)
    for dx, dy, r in [(-190, 60, 150), (190, 60, 150), (-110, -110, 170), (120, -120, 170), (0, 40, 210), (0, -190, 150)]:
        ellipse(ctx, dx, dy, r, r * .92)
        fuell(ctx, rgb("3fc45a"), 9)
    for dx, dy, r in [(-190, 60, 141), (190, 60, 141), (-110, -110, 161), (120, -120, 161), (0, 40, 201), (0, -190, 141)]:
        ellipse(ctx, dx, dy, r, r * .92)
    fuell(ctx, rgb("3fc45a"))
    for dx, dy in [(-150, -40), (60, -160), (150, 20), (-40, 90)]:
        ellipse(ctx, dx, dy, 34, 20, -.4); fuell(ctx, rgb("7de38a"))
    ctx.restore()


def busch(ctx, x, y, t, wackel=0):
    ctx.save(); ctx.translate(x, y); ctx.rotate(wackel * .09)
    teile = [(-75, -55, 62), (75, -55, 62), (0, -120, 78), (-35, -45, 70), (40, -45, 70)]
    for dx, dy, r in teile:
        ellipse(ctx, dx, dy, r, r); fuell(ctx, rgb("2fae4e"), 9)
    for dx, dy, r in teile:
        ellipse(ctx, dx, dy, r - 8, r - 8)
    ellipse(ctx, 0, -30, 120, 34)
    fuell(ctx, rgb("2fae4e"))
    for dx, dy in [(-50, -80), (30, -130), (60, -60)]:
        ellipse(ctx, dx, dy, 22, 14, -.4); fuell(ctx, rgb("6fdc82"))
    ctx.restore()


def p_shape(ctx, x, y, h, o, v, t):
    if h < 3:
        return
    f = COLORS[o["farbe"]]
    if o["art"] == "square":
        kw_rund(ctx, x - h, y - h, 2 * h, 2 * h, h * .12)
    elif o["art"] == "triangle":
        ctx.move_to(x, y - h); ctx.line_to(x + 2.1 * h, y + h); ctx.line_to(x - 2.1 * h, y + h); ctx.close_path()
    else:
        ellipse(ctx, x, y, h, h)
    fuell(ctx, f, 10)


def kw_rund(ctx, x, y, w, h, r):
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0); ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi); ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi); ctx.close_path()


def p_pond(ctx, x, y, g, o, v, t):
    ellipse(ctx, x, y, 365, 100); fuell(ctx, rgb("4db8ff"), 10, rgb("1f6fb5"))
    ctx.set_source_rgba(1, 1, 1, .6); ctx.set_line_width(7); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for dx, dy, w in [(-200, -30, 60), (120, 40, 80), (230, -20, 50), (-60, 55, 70)]:
        k = math.sin(t * 2 + dx) * 12
        ctx.move_to(x + dx - w / 2 + k, y + dy); ctx.line_to(x + dx + w / 2 + k, y + dy); ctx.stroke()


def p_lily(ctx, x, y, g, o, v, t):
    ctx.move_to(x, y); ctx.arc(x, y, 1, 0, 0)
    ctx.save(); ctx.translate(x, y); ctx.scale(82, 30); ctx.move_to(0, 0); ctx.arc(0, 0, 1, .35, 2 * math.pi - .1); ctx.close_path(); ctx.restore()
    fuell(ctx, rgb("3ec45a"), 8)
    for k in range(5):
        a = k * 2 * math.pi / 5
        ellipse(ctx, x - 40 + 13 * math.cos(a), y - 8 + 8 * math.sin(a), 10, 7); fuell(ctx, COLORS["pink"], 3)
    ellipse(ctx, x - 40, y - 8, 6, 5); fuell(ctx, COLORS["yellow"])


def p_box(ctx, x, y, h, o, v, t):
    kw_rund(ctx, x - h, y - h, 2 * h, 2 * h, 10); fuell(ctx, rgb("d9a066"), 10)
    ctx.rectangle(x - h * .16, y - h + 5, h * .32, 2 * h - 10); fuell(ctx, rgb("f0c894"))
    ctx.move_to(x - h, y - h * .45); ctx.line_to(x + h, y - h * .45)
    ctx.set_source_rgb(*kw.kontur(rgb("d9a066"))); ctx.set_line_width(7); ctx.stroke()


def p_ball(ctx, x, y, r, o, v, t):
    r *= .48
    if r < 3:
        return
    ellipse(ctx, x, y, r, r); fuell(ctx, COLORS[o["farbe"] or "red"], 9)
    ctx.save(); ellipse(ctx, x, y, r - 4, r - 4); ctx.clip()
    ctx.move_to(x - r, y - r * .1); ctx.curve_to(x - r * .3, y - r * .6, x + r * .3, y + r * .5, x + r, y + r * .1)
    ctx.set_source_rgb(*kw.WEISS); ctx.set_line_width(r * .3); ctx.stroke(); ctx.restore()
    ellipse(ctx, x - r * .4, y - r * .45, r * .16, r * .24, .6); fuell(ctx, kw.WEISS, alpha=.8)


def p_basket(ctx, x, y, g, o, v, t):
    g = g / 100
    if g < .05:
        return
    ctx.save(); ctx.translate(x, y); ctx.scale(g, g)
    ctx.arc(0, -60, 120, math.pi, 2 * math.pi); ctx.set_source_rgb(*kw.kontur(rgb("c98a4b"))); ctx.set_line_width(30); ctx.stroke()
    ctx.arc(0, -60, 120, math.pi, 2 * math.pi); ctx.set_source_rgb(*rgb("c98a4b")); ctx.set_line_width(14); ctx.stroke()
    ctx.move_to(-150, -65); ctx.line_to(150, -65); ctx.line_to(115, 75); ctx.line_to(-115, 75); ctx.close_path(); fuell(ctx, rgb("e0a868"), 10)
    ctx.set_source_rgb(*rgb("b97a3c")); ctx.set_line_width(7)
    for yy in (-25, 15, 50):
        ctx.move_to(-138 + (yy + 65) * .25, yy); ctx.line_to(138 - (yy + 65) * .25, yy)
    for xx in (-80, -27, 27, 80):
        ctx.move_to(xx * 1.15, -60); ctx.line_to(xx * .95, 70)
    ctx.stroke(); ctx.restore()


def p_banana(ctx, x, y, r, o, v, t):
    r *= .75
    if r < 3:
        return
    ctx.save(); ctx.translate(x, y); ctx.rotate(-.35)
    ctx.move_to(-r, -r * .35); ctx.curve_to(-r * .5, r * .75, r * .6, r * .75, r * 1.05, -r * .45)
    ctx.curve_to(r * .5, r * .2, -r * .4, r * .2, -r, -r * .35); ctx.close_path(); fuell(ctx, COLORS["yellow"], max(5, r * .1), rgb("b8860b"))
    ellipse(ctx, r * 1.05, -r * .47, r * .08, r * .1); fuell(ctx, rgb("7a4a21"))
    ctx.restore()


def p_orange(ctx, x, y, r, o, v, t):
    r *= .44
    if r < 3:
        return
    ellipse(ctx, x + r * .3, y - r * 1.0, r * .36, r * .17, -.5); fuell(ctx, rgb("4cd964"), max(4, r * .1))
    ellipse(ctx, x, y, r, r * .96); fuell(ctx, COLORS["orange"], max(5, r * .13))
    ellipse(ctx, x - r * .4, y - r * .4, r * .2, r * .3, .6); fuell(ctx, kw.WEISS, alpha=.6)
    for dx, dy in [(.2, .3), (.45, -.1), (-.1, .5), (.1, -.35)]:
        ellipse(ctx, x + dx * r, y + dy * r, r * .04, r * .04); fuell(ctx, rgb("d97706"))


def p_letter(ctx, x, y, h, o, v, t):
    if h < 6:
        return
    kw_rund(ctx, x - h, y - h, 2 * h, 2 * h, h * .22); fuell(ctx, COLORS[o["farbe"]], max(6, h * .07))
    kw_rund(ctx, x - h * .8, y - h * .8, 1.6 * h, 1.6 * h, h * .15); fuell(ctx, kw.mix(COLORS[o["farbe"]], kw.WEISS, .25))
    kw.schrift(ctx, h * 1.5)
    e = ctx.text_extents(o["text"])
    ctx.move_to(x - e.width / 2 - e.x_bearing, y - e.height / 2 - e.y_bearing); ctx.text_path(o["text"])
    ctx.set_source_rgb(*kw.INK); ctx.set_line_width(h * .14); ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.stroke_preserve()
    ctx.set_source_rgb(*kw.WEISS); ctx.fill()


def p_light(ctx, x, y, g, o, v, t):
    ctx.rectangle(x - 16, y - 330, 32, 330); fuell(ctx, rgb("8a94a6"), 8)
    kw_rund(ctx, x - 78, y - 720, 156, 400, 40); fuell(ctx, rgb("4a4f63"), 10, kw.INK)
    an = int(round(v))
    for k, name in enumerate(("red", "yellow", "green")):
        f = COLORS[name] if an == k + 1 else kw.mix(COLORS[name], kw.INK, .72)
        cy = y - 640 + k * 120
        if an == k + 1:
            ellipse(ctx, x, cy, 66 + 5 * math.sin(t * 8), 66 + 5 * math.sin(t * 8)); fuell(ctx, COLORS[name], alpha=.35)
        ellipse(ctx, x, cy, 48, 48); fuell(ctx, f, 7, kw.INK)
        if an == k + 1:
            ellipse(ctx, x - 16, cy - 18, 10, 14, .6); fuell(ctx, kw.WEISS, alpha=.8)


def p_road(ctx, x, y, g, o, v, t):
    ctx.rectangle(-10, y - 12, B + 20, 130); fuell(ctx, rgb("7d8597"), 9, rgb("4a4f63"))
    for xx in range(40, B, 190):
        kw_rund(ctx, xx, y + 45, 100, 16, 8); fuell(ctx, kw.WEISS)


def p_snowball(ctx, x, y, r, o, v, t):
    if r < 3:
        return
    ellipse(ctx, x, y, r, r * .97); fuell(ctx, rgb("ffffff"), 9, rgb("7fa6d6"))
    ctx.save(); ellipse(ctx, x, y, r - 5, r - 5); ctx.clip()
    ellipse(ctx, x + r * .25, y + r * .35, r, r); fuell(ctx, rgb("dcecff"))
    ellipse(ctx, x - r * .1, y - r * .1, r, r); fuell(ctx, rgb("ffffff")); ctx.restore()


def p_snowface(ctx, x, y, r, o, v, t):
    if r < 3:
        return
    for sx in (-1, 1):
        ellipse(ctx, x + sx * r * .36, y - r * .22, r * .11, r * .13); fuell(ctx, kw.INK)
    for k in range(5):
        a = math.radians(30 + k * 30)
        ellipse(ctx, x + math.cos(a) * r * .5 * (1 if k != 2 else 1), y + r * .12 + math.sin(a) * r * .36, r * .055, r * .055); fuell(ctx, kw.INK)


def p_carrot(ctx, x, y, r, o, v, t):
    if r < 3:
        return
    ctx.save(); ctx.translate(x, y); ctx.rotate(.25)
    for k in (-1, 0, 1):
        ellipse(ctx, -r * .95, k * r * .16, r * .3, r * .1, k * .5); fuell(ctx, rgb("4cd964"), max(3, r * .05))
    ctx.move_to(-r * .7, -r * .3); ctx.curve_to(-r * .2, -r * .32, r * .6, -r * .1, r, 0)
    ctx.curve_to(r * .6, r * .1, -r * .2, r * .32, -r * .7, r * .3); ctx.close_path(); fuell(ctx, COLORS["orange"], max(4, r * .07))
    ctx.restore()


def p_scarf(ctx, x, y, g, o, v, t):
    g = g / 100
    if g < .05:
        return
    ctx.save(); ctx.translate(x, y); ctx.scale(g, g)
    kw_rund(ctx, 40, 0, 46, 120, 14); fuell(ctx, COLORS["red"], 8)
    kw_rund(ctx, -92, -24, 184, 50, 24); fuell(ctx, COLORS["red"], 8)
    for xx in (-50, 0, 50):
        ctx.rectangle(xx - 9, -20, 18, 42)
    fuell(ctx, rgb("ffffff"), alpha=.85)
    ctx.restore()


def p_xtree(ctx, x, y, g, o, v, t):
    ctx.rectangle(x - 45, y - 110, 90, 115); fuell(ctx, rgb("a8683d"), 9)
    for i, (yy, w, h) in enumerate([(y - 90, 290, 300), (y - 300, 235, 270), (y - 500, 180, 250)]):
        ctx.move_to(x, yy - h); ctx.line_to(x + w, yy); ctx.line_to(x - w, yy); ctx.close_path(); fuell(ctx, rgb("2fae4e"), 10)
        ctx.move_to(x, yy - h + 8); ctx.line_to(x + w * .34, yy - h * .62); ctx.line_to(x + w * .1, yy - h * .68)
        ctx.line_to(x - w * .12, yy - h * .58); ctx.line_to(x - w * .32, yy - h * .66); ctx.close_path(); fuell(ctx, rgb("ffffff"))


def p_star(ctx, x, y, r, o, v, t):
    if r < 3:
        return
    kw.stern_pfad(ctx, x, y, r, math.sin(t * 2) * .08); fuell(ctx, COLORS["yellow"], max(5, r * .1), rgb("e07b00"))
    kw.stern_pfad(ctx, x, y - r * .05, r * .45, math.sin(t * 2) * .08); fuell(ctx, rgb("fff3a0"))


def p_gift(ctx, x, y, h, o, v, t):
    if h < 3:
        return
    f = COLORS[o["farbe"]]
    kw_rund(ctx, x - h, y - h * .75, 2 * h, h * 1.75, h * .1); fuell(ctx, f, 9)
    ctx.rectangle(x - h * .17, y - h * .75, h * .34, h * 1.75); fuell(ctx, COLORS["yellow"])
    kw_rund(ctx, x - h * 1.1, y - h * 1.02, 2.2 * h, h * .38, h * .1); fuell(ctx, kw.mix(f, kw.WEISS, .2), 9, kw.kontur(f))
    ctx.rectangle(x - h * .17, y - h * 1.0, h * .34, h * .34); fuell(ctx, COLORS["yellow"])
    for sx in (-1, 1):
        ellipse(ctx, x + sx * h * .3, y - h * 1.22, h * .3, h * .19, sx * -.5); fuell(ctx, COLORS["yellow"], 7, rgb("e07b00"))
    ellipse(ctx, x, y - h * 1.1, h * .12, h * .12); fuell(ctx, COLORS["yellow"], 6, rgb("e07b00"))


def p_fish(ctx, x, y, r, o, v, t):
    if r < 3:
        return
    lw = max(5, r * .08)
    wag = math.sin(t * 8) * r * .1
    ctx.move_to(x - r * .7, y); ctx.line_to(x - r * 1.35, y - r * .5 + wag); ctx.line_to(x - r * 1.35, y + r * .5 + wag); ctx.close_path(); fuell(ctx, rgb("2f7de0"), lw)
    ellipse(ctx, x, y, r, r * .6); fuell(ctx, COLORS["blue"], lw)
    ellipse(ctx, x + r * .1, y + r * .2, r * .55, r * .28); fuell(ctx, rgb("9dd0ff"))
    ellipse(ctx, x + r * .5, y - r * .12, r * .14, r * .16); fuell(ctx, kw.INK)
    ellipse(ctx, x + r * .46, y - r * .17, r * .05, r * .05); fuell(ctx, kw.WEISS)


def p_bone(ctx, x, y, r, o, v, t):
    if r < 3:
        return
    lw = max(5, r * .08)
    ctx.save(); ctx.translate(x, y); ctx.rotate(-.3)
    for sx in (-1, 1):
        for sy in (-1, 1):
            ellipse(ctx, sx * r * .85, sy * r * .2, r * .26, r * .26); fuell(ctx, rgb("fff6e0"), lw, rgb("b8a27a"))
    kw_rund(ctx, -r * .85, -r * .2, r * 1.7, r * .4, r * .1); fuell(ctx, rgb("fff6e0"), lw, rgb("b8a27a"))
    for sx in (-1, 1):
        for sy in (-1, 1):
            ellipse(ctx, sx * r * .82, sy * r * .17, r * .2, r * .2); fuell(ctx, rgb("fff6e0"))
    ctx.restore()


_WINTER = None


def welt_winter(ctx, t, offen):
    global _WINTER
    if _WINTER is None:
        _WINTER = cairo.ImageSurface(cairo.FORMAT_ARGB32, B, H)
        c = cairo.Context(_WINTER); c.set_line_join(cairo.LINE_JOIN_ROUND)
        g = cairo.LinearGradient(0, 0, 0, 1500)
        g.add_color_stop_rgb(0, *rgb("4aa8f0")); g.add_color_stop_rgb(1, *rgb("d8f1ff"))
        c.set_source(g); c.paint()
        kw.huegel(c, 1330, 60, 210, .4, rgb("cfe6fb"))
        rnd = random.Random(8)
        for px in (90, 300, 470, 880, 1010):
            h = rnd.uniform(170, 260); base = 1390 + rnd.uniform(-10, 30)
            c.rectangle(px - 12, base - 30, 24, 40); fuell(c, rgb("a8683d"), 6)
            for k in range(3):
                yy = base - 25 - k * h * .27; w = h * (.42 - k * .09)
                c.move_to(px, yy - h * .42); c.line_to(px + w, yy); c.line_to(px - w, yy); c.close_path(); fuell(c, rgb("3aa76a"), 7)
                c.move_to(px, yy - h * .42); c.line_to(px + w * .4, yy - h * .25); c.line_to(px - w * .4, yy - h * .25); c.close_path(); fuell(c, rgb("ffffff"))
        kw.huegel(c, 1410, 45, 170, 1.0, rgb("eef7ff"))
        kw.huegel(c, 1500, 35, 230, 3.2, rgb("ffffff"))
        for _ in range(60):
            x, y = rnd.uniform(0, B), rnd.uniform(1560, H)
            ellipse(c, x, y, rnd.uniform(14, 40), 6); fuell(c, rgb("e3f0fd"))
    ctx.set_source_surface(_WINTER, 0, 0); ctx.paint()
    for i, (y, s, v) in enumerate([(470, 95, 22), (780, 70, 14)]):
        kw.wolke(ctx, (i * 520 + t * v) % (B + 400) - 200, y, s)
    rnd = random.Random(3)
    for i in range(70):
        x = (rnd.uniform(0, B) + math.sin(t * 1.3 + i) * 30) % B
        y = (rnd.uniform(0, H) + t * rnd.uniform(90, 190)) % H
        r = rnd.uniform(5, 13)
        ellipse(ctx, x, y, r, r); fuell(ctx, kw.WEISS, alpha=.92)
    kw.sonne(ctx, 170, 215, 100, t, offen)


def p_egg(ctx, x, y, r, o, v, t):
    if r < 3:
        return
    ctx.save(); ctx.translate(x, y); ctx.rotate(math.sin(t * 3) * .06)
    ellipse(ctx, 0, 0, r * .78, r); fuell(ctx, rgb("fff3d6"), max(5, r * .08), rgb("b8a27a"))
    for dx, dy, q in [(-.3, -.35, .12), (.25, .1, .15), (-.15, .45, .1), (.3, -.5, .08)]:
        ellipse(ctx, dx * r, dy * r, q * r, q * r); fuell(ctx, rgb("ffd08a"))
    ctx.restore()


def p_rocket(ctx, x, y, g, o, v, t):
    if g < 4:
        return
    lw = max(5, g * .08)
    if v > .5:
        for k, f in enumerate(["ff7a1a", "ffd633"]):
            fl = g * (1.3 - k * .45) * (1 + .15 * math.sin(t * 40 + k))
            ctx.move_to(x - g * (.42 - k * .15), y + g * 1.5); ctx.line_to(x, y + g * 1.5 + fl); ctx.line_to(x + g * (.42 - k * .15), y + g * 1.5); ctx.close_path(); fuell(ctx, rgb(f))
    for sx in (-1, 1):
        ctx.move_to(x + sx * g * .5, y + g * .6); ctx.line_to(x + sx * g * 1.1, y + g * 1.75); ctx.line_to(x + sx * g * .4, y + g * 1.5); ctx.close_path(); fuell(ctx, COLORS["red"], lw)
    ctx.move_to(x, y - g * 2.0); ctx.curve_to(x + g * .95, y - g * 1.0, x + g * .7, y + g * 1.0, x + g * .5, y + g * 1.6)
    ctx.line_to(x - g * .5, y + g * 1.6); ctx.curve_to(x - g * .7, y + g * 1.0, x - g * .95, y - g * 1.0, x, y - g * 2.0); ctx.close_path(); fuell(ctx, rgb("ffffff"), lw, rgb("7f8fb0"))
    ctx.save(); ctx.move_to(x, y - g * 2.0); ctx.curve_to(x + g * .95, y - g * 1.0, x + g * .7, y + g * 1.0, x + g * .5, y + g * 1.6)
    ctx.line_to(x - g * .5, y + g * 1.6); ctx.curve_to(x - g * .7, y + g * 1.0, x - g * .95, y - g * 1.0, x, y - g * 2.0); ctx.clip()
    ctx.rectangle(x - g, y - g * 2.1, 2 * g, g * .95); fuell(ctx, COLORS["red"]); ctx.restore()
    ellipse(ctx, x, y - g * .35, g * .33, g * .33); fuell(ctx, rgb("7fd4ff"), lw, rgb("3d6fb0"))
    ellipse(ctx, x - g * .1, y - g * .45, g * .1, g * .1); fuell(ctx, kw.WEISS)


def p_seesaw(ctx, x, y, g, o, v, t):
    ctx.move_to(x - 62, GY + 4); ctx.line_to(x + 62, GY + 4); ctx.line_to(x, y - 6); ctx.close_path(); fuell(ctx, COLORS["blue"], 9)
    ctx.save(); ctx.translate(x, y); ctx.rotate(v)
    kw_rund(ctx, -370, -16, 740, 32, 14); fuell(ctx, rgb("ffb347"), 9)
    for sx in (-1, 1):
        kw_rund(ctx, sx * 345 - 9, -62, 18, 50, 8); fuell(ctx, COLORS["red"], 6)
    ctx.restore()


def p_nest(ctx, x, y, g, o, v, t):
    g = g / 100
    if g < .05:
        return
    ctx.save(); ctx.translate(x, y); ctx.scale(g, g)
    ctx.move_to(-120, -20); ctx.curve_to(-110, 85, 110, 85, 120, -20); ctx.curve_to(60, 5, -60, 5, -120, -20); ctx.close_path(); fuell(ctx, rgb("b0733c"), 9)
    ctx.set_source_rgb(*rgb("7a4a21")); ctx.set_line_width(6); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for a, b_, c_, d in [(-90, 10, -30, 40), (-40, 15, 30, 45), (20, 12, 85, 30), (-70, 40, 0, 55), (10, 50, 70, 42)]:
        ctx.move_to(a, b_); ctx.line_to(c_, d)
    ctx.stroke(); ctx.restore()


def p_text(ctx, x, y, g, o, v, t):
    f = REGENBOGEN if o["farbe"] == "rainbow" else COLORS[o["farbe"]]
    kw.titel(ctx, o["text"], x, y, g, f, t, welle=.6)


# ---- Requisiten fuer die Folgen ab 27.11.2026 ----
COLORS.setdefault("brown", rgb("a0612b"))


def _f(name):
    return COLORS.get(name) or rgb(name)


def p_grapes(ctx, x, y, r, o, v, t):
    if r < 4:
        return
    ctx.move_to(x, y - r * 1.05); ctx.curve_to(x + r * .05, y - r * 1.3, x + r * .25, y - r * 1.4, x + r * .3, y - r * 1.5)
    ctx.set_source_rgb(*rgb("7a4a21")); ctx.set_line_width(max(4, r * .1)); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.stroke()
    ellipse(ctx, x + r * .38, y - r * 1.1, r * .4, r * .2, -.4); fuell(ctx, rgb("4cd964"), max(3, r * .06))
    for dx, dy in [(-.55, -.7), (0, -.75), (.55, -.7), (-.3, -.25), (.3, -.25), (-.6, .15), (0, .2), (.6, .15), (-.3, .6), (.3, .6), (0, 1.0)]:
        ellipse(ctx, x + dx * r, y + dy * r, r * .32, r * .32); fuell(ctx, COLORS["purple"], max(4, r * .06))
        ellipse(ctx, x + dx * r - r * .1, y + dy * r - r * .1, r * .07, r * .09, .5); fuell(ctx, kw.WEISS, alpha=.7)


def p_hat(ctx, x, y, r, o, v, t):
    if r < 4:
        return
    lw = max(5, r * .08)
    ellipse(ctx, x, y, r * 1.35, r * .3); fuell(ctx, COLORS["red"], lw)
    kw_rund(ctx, x - r * .75, y - r * 1.0, r * 1.5, r * 1.05, r * .3); fuell(ctx, COLORS["red"], lw)
    ctx.rectangle(x - r * .75, y - r * .35, r * 1.5, r * .25); fuell(ctx, COLORS["yellow"])
    ellipse(ctx, x - r * .4, y - r * .75, r * .1, r * .16, .4); fuell(ctx, kw.WEISS, alpha=.6)


def p_icecream(ctx, x, y, r, o, v, t):
    if r < 4:
        return
    lw = max(5, r * .08)
    ctx.move_to(x - r * .62, y - r * .2); ctx.line_to(x + r * .62, y - r * .2); ctx.line_to(x, y + r * 1.25); ctx.close_path()
    fuell(ctx, rgb("e8b56a"), lw, rgb("a8742f"))
    ctx.save(); ctx.move_to(x - r * .62, y - r * .2); ctx.line_to(x + r * .62, y - r * .2); ctx.line_to(x, y + r * 1.25); ctx.close_path(); ctx.clip()
    ctx.set_source_rgb(*rgb("c48d45")); ctx.set_line_width(max(3, r * .05))
    for k in range(-3, 4):
        ctx.move_to(x + k * r * .3 - r, y - r * .2); ctx.line_to(x + k * r * .3 + r, y + r * 1.3)
        ctx.move_to(x + k * r * .3 + r, y - r * .2); ctx.line_to(x + k * r * .3 - r, y + r * 1.3)
    ctx.stroke(); ctx.restore()
    ellipse(ctx, x, y - r * .45, r * .62, r * .5); fuell(ctx, COLORS["pink"], lw)
    ellipse(ctx, x, y - r * .95, r * .5, r * .42); fuell(ctx, rgb("fff3d6"), lw, rgb("b8a27a"))
    ellipse(ctx, x + r * .05, y - r * 1.42, r * .14, r * .14); fuell(ctx, COLORS["red"], max(3, r * .05))
    ellipse(ctx, x - r * .25, y - r * 1.05, r * .08, r * .12, .5); fuell(ctx, kw.WEISS, alpha=.8)


def p_mound(ctx, x, y, g, o, v, t):
    ctx.move_to(x - 170, y + 6); ctx.curve_to(x - 120, y - 120, x + 120, y - 120, x + 170, y + 6); ctx.close_path()
    fuell(ctx, rgb("9a6232"), 9, rgb("5e3a1a"))
    for dx, dy in [(-60, -40), (30, -60), (80, -25), (-10, -20)]:
        ellipse(ctx, x + dx, y + dy, 13, 8); fuell(ctx, rgb("7a4a21"))


def p_raincloud(ctx, x, y, g, o, v, t):
    s = g / 100
    if s < .05:
        return
    if v > .05:
        ctx.save()
        for i in range(24):
            dx = (i * 53) % 320 - 160
            dy = (t * 650 + i * 97) % 640
            a = v * min(1, 1.25 - dy / 640)
            px, py = x + dx * s, y + 40 * s + dy
            ctx.move_to(px, py - 34); ctx.curve_to(px + 17, py - 3, px + 14, py + 12, px, py + 12); ctx.curve_to(px - 14, py + 12, px - 17, py - 3, px, py - 34)
            ctx.set_source_rgba(*rgb("2f7de0"), a); ctx.fill()
        ctx.restore()
    teile = [(-1.0, .15, .55), (-.4, -.25, .75), (.45, -.15, .65), (1.0, .15, .5), (0, .2, .75)]
    for dx, dy, r in teile:
        ellipse(ctx, x + dx * 100 * s, y + dy * 100 * s, r * 100 * s, r * 80 * s); fuell(ctx, rgb("9aa7bd"), 10, rgb("5d6a80"))
    for dx, dy, r in teile:
        ellipse(ctx, x + dx * 100 * s, y + dy * 100 * s, r * 100 * s - 5, r * 80 * s - 5)
    fuell(ctx, rgb("9aa7bd"))
    ellipse(ctx, x - 50 * s, y - 40 * s, 40 * s, 18 * s, -.2); fuell(ctx, rgb("c3cddd"))


def p_umbrella(ctx, x, y, r, o, v, t):
    if r < 5:
        return
    lw = max(5, r * .07)
    ctx.save(); ctx.translate(x, y); ctx.rotate(v)
    ctx.move_to(0, -r * .1); ctx.line_to(0, r * 1.25); ctx.arc_negative(r * .17, r * 1.25, r * .17, math.pi, 0)
    ctx.set_source_rgb(*kw.INK); ctx.set_line_width(lw * 1.9); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.stroke()
    ctx.move_to(0, -r * .1); ctx.line_to(0, r * 1.25); ctx.arc_negative(r * .17, r * 1.25, r * .17, math.pi, 0)
    ctx.set_source_rgb(*rgb("8a94a6")); ctx.set_line_width(lw * .9); ctx.stroke()
    farben = [COLORS["red"], COLORS["yellow"], COLORS["red"], COLORS["yellow"]]
    for k in range(4):
        a0, a1 = math.pi + k * math.pi / 4, math.pi + (k + 1) * math.pi / 4
        ctx.move_to(0, 0); ctx.arc(0, 0, r, a0, a1)
        ctx.close_path(); fuell(ctx, farben[k], lw)
    ellipse(ctx, 0, -r, r * .07, r * .07); fuell(ctx, kw.INK)
    ctx.restore()


def p_wind(ctx, x, y, g, o, v, t):
    if v < .02:
        return
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for i, yy in enumerate([650, 830, 1010, 1190, 1330]):
        xx = (t * 950 + i * 377) % (B + 600) - 300
        ctx.move_to(xx - 170, yy); ctx.curve_to(xx - 80, yy - 30, xx + 20, yy + 30, xx + 110, yy)
        ctx.arc(xx + 110, yy - 30, 30, math.pi / 2, math.pi / 2 + 5)
        ctx.set_source_rgba(1, 1, 1, .85 * v); ctx.set_line_width(12); ctx.stroke()


def p_night(ctx, x, y, g, o, v, t):
    if v < .01:
        return
    ctx.set_source_rgba(*rgb("1b1f4a"), .74 * v); ctx.paint()
    rnd = random.Random(11)
    for i in range(26):
        sx, sy = rnd.uniform(40, B - 40), rnd.uniform(320, 1250)
        if sy < 620 and 320 < sx < 760:
            continue
        r = rnd.uniform(12, 22) * (1 + .15 * math.sin(t * 3 + i))
        kw.stern_pfad(ctx, sx, sy, r); fuell(ctx, COLORS["yellow"], alpha=min(1, v * 1.3))
    ctx.save(); ctx.push_group()
    ellipse(ctx, 870, 640, 95, 95); ctx.set_source_rgb(*rgb("fff3b0")); ctx.fill()
    ctx.set_operator(cairo.OPERATOR_CLEAR); ellipse(ctx, 920, 600, 85, 85); ctx.fill()
    ctx.pop_group_to_source(); ctx.paint_with_alpha(min(1, v * 1.3)); ctx.restore()


def p_bed(ctx, x, y, g, o, v, t):
    kw_rund(ctx, x + 175, y - 330, 50, 330, 20); fuell(ctx, rgb("b0733c"), 9)
    kw_rund(ctx, x - 225, y - 230, 50, 230, 20); fuell(ctx, rgb("b0733c"), 9)
    kw_rund(ctx, x - 200, y - 150, 400, 80, 20); fuell(ctx, rgb("ffffff"), 9, rgb("8a94a6"))
    ctx.rectangle(x - 180, y - 70, 20, 70); ctx.rectangle(x + 160, y - 70, 20, 70); fuell(ctx, rgb("b0733c"), 8)


def p_blanket(ctx, x, y, g, o, v, t):
    if g < 5:
        return
    s = g / 100
    kw_rund(ctx, x - 205 * s, y - 50 * s, 410 * s, 125 * s, 30 * s); fuell(ctx, COLORS["blue"], 9)
    for k in range(4):
        ellipse(ctx, x - 140 * s + k * 95 * s, y + 10 * s, 18 * s, 18 * s); fuell(ctx, COLORS["yellow"])


def p_face(ctx, x, y, r, o, v, t):
    if r < 5:
        return
    lw = max(5, r * .08)
    ellipse(ctx, x, y, r, r); fuell(ctx, rgb("ffd93b"), lw, rgb("e07b00"))
    art = o["art"]
    for sx in (-1, 1):
        if art == "surprised":
            ellipse(ctx, x + sx * r * .35, y - r * .2, r * .13, r * .17); fuell(ctx, kw.INK)
            ctx.move_to(x + sx * r * .5, y - r * .58); ctx.line_to(x + sx * r * .2, y - r * .65)
        elif art == "sad":
            ellipse(ctx, x + sx * r * .35, y - r * .15, r * .1, r * .12); fuell(ctx, kw.INK)
            ctx.move_to(x + sx * r * .52, y - r * .42); ctx.line_to(x + sx * r * .2, y - r * .52)
        else:
            ctx.arc(x + sx * r * .35, y - r * .1, r * .13, math.pi * 1.1, math.pi * 1.9)
        ctx.set_source_rgb(*kw.INK); ctx.set_line_width(lw); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.stroke()
    if art == "surprised":
        ellipse(ctx, x, y + r * .4, r * .17, r * .23); fuell(ctx, kw.INK)
    elif art == "sad":
        ctx.arc(x, y + r * .62, r * .32, math.pi * 1.15, math.pi * 1.85)
        ctx.set_source_rgb(*kw.INK); ctx.set_line_width(lw * 1.2); ctx.stroke()
        tr = y + r * .05 + (t * 90) % (r * .45)
        ctx.move_to(x + r * .5, tr - r * .15); ctx.curve_to(x + r * .6, tr, x + r * .58, tr + r * .08, x + r * .5, tr + r * .08)
        ctx.curve_to(x + r * .42, tr + r * .08, x + r * .4, tr, x + r * .5, tr - r * .15); fuell(ctx, COLORS["blue"])
    else:
        ctx.arc(x, y + r * .12, r * .42, math.pi * .15, math.pi * .85); ctx.close_path(); fuell(ctx, kw.INK)
        ellipse(ctx, x, y + r * .45, r * .17, r * .08); fuell(ctx, COLORS["red"])
    for sx in (-1, 1):
        ellipse(ctx, x + sx * r * .62, y + r * .2, r * .14, r * .09); fuell(ctx, COLORS["pink"], alpha=.6)


def p_car(ctx, x, y, g, o, v, t):
    if g < 5:
        return
    lw = max(6, g * .07)
    ctx.move_to(x - g * 1.5, y - g * .35); ctx.line_to(x - g * 1.5, y - g * .8); ctx.curve_to(x - g * 1.45, y - g * 1.0, x - g * 1.1, y - g * 1.0, x - g * .9, y - g * 1.0)
    ctx.line_to(x + g * .9, y - g * 1.0); ctx.curve_to(x + g * 1.3, y - g * .95, x + g * 1.55, y - g * .8, x + g * 1.55, y - g * .55)
    ctx.line_to(x + g * 1.55, y - g * .35); ctx.close_path(); fuell(ctx, COLORS[o["farbe"] or "red"], lw)
    ctx.move_to(x + g * .55, y - g * 1.0); ctx.line_to(x + g * .85, y - g * 1.55)
    ctx.set_source_rgb(*kw.INK); ctx.set_line_width(lw * 1.6); ctx.stroke()
    ctx.move_to(x + g * .55, y - g * 1.0); ctx.line_to(x + g * .85, y - g * 1.55)
    ctx.set_source_rgba(*rgb("bfe9ff"), 1); ctx.set_line_width(lw * .6); ctx.stroke()
    ellipse(ctx, x + g * 1.42, y - g * .72, g * .1, g * .08); fuell(ctx, COLORS["yellow"], max(3, lw * .6))
    ctx.rectangle(x - g * 1.2, y - g * .78, g * 1.6, g * .08); fuell(ctx, kw.WEISS, alpha=.5)
    for wx in (-.9, .95):
        cx, cy, rr = x + wx * g, y - g * .3, g * .32
        ellipse(ctx, cx, cy, rr, rr); fuell(ctx, rgb("3b3f55"), lw, kw.INK)
        ellipse(ctx, cx, cy, rr * .45, rr * .45); fuell(ctx, rgb("c9cfdc"))
        a = x / (rr + 1)
        ctx.move_to(cx + math.cos(a) * rr * .45, cy + math.sin(a) * rr * .45); ctx.line_to(cx - math.cos(a) * rr * .45, cy - math.sin(a) * rr * .45)
        ctx.set_source_rgb(*rgb("7d8597")); ctx.set_line_width(max(3, lw * .5)); ctx.stroke()


def p_boat(ctx, x, y, g, o, v, t):
    if g < 5:
        return
    lw = max(6, g * .07)
    y = y + math.sin(t * 2.5) * 0
    ctx.move_to(x - g * 1.15, y - g * 2.3); ctx.line_to(x - g * 1.15, y - g * .5)
    ctx.set_source_rgb(*rgb("7a4a21")); ctx.set_line_width(lw * 1.3); ctx.stroke()
    ctx.move_to(x - g * 1.05, y - g * 2.2); ctx.line_to(x - g * .25, y - g * .75); ctx.line_to(x - g * 1.05, y - g * .75); ctx.close_path()
    fuell(ctx, rgb("ffffff"), lw, rgb("8a94a6"))
    ctx.move_to(x - g * 1.15, y - g * 2.3); ctx.line_to(x - g * .75, y - g * 2.15); ctx.line_to(x - g * 1.15, y - g * 2.0); ctx.close_path(); fuell(ctx, COLORS["red"], max(3, lw * .5))
    ctx.move_to(x - g * 1.6, y - g * .55); ctx.line_to(x + g * 1.6, y - g * .55); ctx.line_to(x + g * 1.15, y + g * .3); ctx.line_to(x - g * 1.15, y + g * .3); ctx.close_path()
    fuell(ctx, COLORS[o["farbe"] or "blue"], lw)
    ctx.rectangle(x - g * 1.45, y - g * .4, g * 2.9, g * .12); fuell(ctx, kw.WEISS)
    for k in (-1, 0, 1):
        ellipse(ctx, x + k * g * .7, y - g * .05, g * .1, g * .1); fuell(ctx, rgb("bfe9ff"), max(3, lw * .5))


def p_plane(ctx, x, y, g, o, v, t):
    if g < 5:
        return
    lw = max(6, g * .07)
    ctx.move_to(x - g * 1.6, y - g * .1); ctx.line_to(x - g * 2.0, y - g * .9); ctx.line_to(x - g * 1.55, y - g * .9); ctx.line_to(x - g * 1.0, y - g * .2); ctx.close_path()
    fuell(ctx, COLORS["red"], lw)
    ellipse(ctx, x, y, g * 1.8, g * .45); fuell(ctx, rgb("ffffff"), lw, rgb("7f8fb0"))
    ctx.move_to(x - g * .3, y + g * .05); ctx.line_to(x + g * .5, y + g * .05); ctx.line_to(x - g * .1, y + g * 1.0); ctx.line_to(x - g * .8, y + g * 1.0); ctx.close_path()
    fuell(ctx, COLORS["blue"], lw)
    for k in range(3):
        ellipse(ctx, x - g * 1.0 + k * g * .38, y - g * .05, g * .1, g * .1); fuell(ctx, rgb("7fd4ff"), max(3, lw * .5))
    ellipse(ctx, x + g * 1.82, y, g * .12, g * .4 * abs(math.sin(t * 30)) + 2); fuell(ctx, rgb("8a94a6"), max(3, lw * .5))


def p_mud(ctx, x, y, g, o, v, t):
    if g < 5:
        return
    s = g / 100
    for dx, dy, r in [(-62, 88, 30), (-38, 118, 18), (66, 78, 26), (84, 108, 16), (-52, -38, 18), (12, 128, 22), (40, 40, 12)]:
        ellipse(ctx, x + dx * s, y + dy * s, r * s, r * s * .8, dx * .01); fuell(ctx, rgb("7a4a21"), alpha=.95)


def p_sink(ctx, x, y, g, o, v, t):
    ctx.rectangle(x - 35, y - 170, 70, 170); fuell(ctx, rgb("ffffff"), 9, rgb("8a94a6"))
    ctx.move_to(x - 170, y - 260); ctx.line_to(x + 170, y - 260); ctx.curve_to(x + 160, y - 150, x + 90, y - 140, x, y - 140)
    ctx.curve_to(x - 90, y - 140, x - 160, y - 150, x - 170, y - 260); ctx.close_path(); fuell(ctx, rgb("ffffff"), 9, rgb("8a94a6"))
    kw_rund(ctx, x - 22, y - 400, 44, 140, 12); fuell(ctx, rgb("c9cfdc"), 8, rgb("7d8597"))
    kw_rund(ctx, x - 22, y - 400, 110, 40, 16); fuell(ctx, rgb("c9cfdc"), 8, rgb("7d8597"))
    kw_rund(ctx, x - 50, y - 430, 100, 26, 12); fuell(ctx, COLORS["blue"], 6)
    if v > .02:
        ctx.rectangle(x + 64, y - 360, 24, 100); ctx.set_source_rgba(*rgb("7fd4ff"), .85 * v); ctx.fill()
        for k in range(4):
            yy = y - 360 + (t * 300 + k * 25) % 100
            ellipse(ctx, x + 76, yy, 6, 9); fuell(ctx, kw.WEISS, alpha=.7 * v)


def p_bubbles(ctx, x, y, g, o, v, t):
    if g < 5:
        return
    s = g / 100
    rnd = random.Random(5)
    for i in range(14):
        a = rnd.uniform(0, 2 * math.pi); d = rnd.uniform(40, 150) * s
        bx = x + math.cos(a + t * .8) * d; by = y + math.sin(a + t * .8) * d * .7 - (t * 40 + i * 30) % 80
        r = rnd.uniform(14, 34) * s
        ellipse(ctx, bx, by, r, r); fuell(ctx, rgb("ffffff"), max(3, r * .15), rgb("8fd3ff"), alpha=.55)
        ellipse(ctx, bx - r * .35, by - r * .35, r * .2, r * .2); fuell(ctx, kw.WEISS)


def p_towel(ctx, x, y, g, o, v, t):
    if g < 5:
        return
    s = g / 100
    kw_rund(ctx, x - 70 * s, y - 100 * s, 140 * s, 200 * s, 18 * s); fuell(ctx, COLORS["green"], 8)
    for k in (-1, 1):
        ctx.rectangle(x - 70 * s, y + k * 60 * s - 8 * s, 140 * s, 16 * s)
    fuell(ctx, kw.WEISS, alpha=.85)


def p_drum(ctx, x, y, g, o, v, t):
    if g < 5:
        return
    lw = max(6, g * .07)
    ctx.move_to(x - g, y - g * .9); ctx.line_to(x - g, y); ctx.curve_to(x - g, y + g * .4, x + g, y + g * .4, x + g, y); ctx.line_to(x + g, y - g * .9); ctx.close_path()
    fuell(ctx, COLORS["red"], lw)
    ctx.set_source_rgb(*COLORS["yellow"]); ctx.set_line_width(lw)
    for k in range(5):
        xx = x - g + k * g * .5
        ctx.move_to(xx, y - g * .75); ctx.line_to(xx + g * .25, y + g * .1)
        if k < 4:
            ctx.move_to(xx + g * .5, y - g * .75); ctx.line_to(xx + g * .25, y + g * .1)
    ctx.stroke()
    ellipse(ctx, x, y - g * .9, g, g * .3); fuell(ctx, rgb("fff6e0"), lw, rgb("b8a27a"))


def p_card(ctx, x, y, h, o, v, t):
    if h < 6:
        return
    w = h * 1.45
    kw_rund(ctx, x - w, y - h, 2 * w, 2 * h, h * .25); fuell(ctx, COLORS[o["farbe"]], max(6, h * .08))
    kw_rund(ctx, x - w * .86, y - h * .78, 1.72 * w, 1.56 * h, h * .18); fuell(ctx, kw.WEISS)
    kw.schrift(ctx, h * .82)
    e = ctx.text_extents(o["text"])
    ctx.move_to(x - e.width / 2 - e.x_bearing, y - e.height / 2 - e.y_bearing); ctx.text_path(o["text"])
    ctx.set_source_rgb(*kw.kontur(COLORS[o["farbe"]])); ctx.fill()


def _herz(ctx, x, y, r):
    ctx.move_to(x, y + r * .95)
    ctx.curve_to(x - r * 1.4, y + r * .05, x - r * 1.05, y - r * 1.05, x, y - r * .45)
    ctx.curve_to(x + r * 1.05, y - r * 1.05, x + r * 1.4, y + r * .05, x, y + r * .95); ctx.close_path()


def p_cookie(ctx, x, y, r, o, v, t):
    if r < 5:
        return
    lw = max(6, r * .08)
    teig, rand = rgb("e0a868"), rgb("a8742f")
    art = o["art"]
    for k, (f, kante, s) in enumerate([(teig, rand, 1.0), (COLORS[o["farbe"]], None, .78)]):
        if art == "heart":
            _herz(ctx, x, y, r * s)
        elif art == "star":
            kw.stern_pfad(ctx, x, y, r * 1.15 * s)
        else:
            kw_rund(ctx, x - r * 1.35 * s, y - r * .8 * s, 2.7 * r * s, 1.6 * r * s, r * .2 * s)
        fuell(ctx, f, lw if k == 0 else 0, kante)
    for dx, dy in [(-.3, -.1), (.25, .15), (0, .35)]:
        ellipse(ctx, x + dx * r, y + dy * r, r * .06, r * .06); fuell(ctx, kw.WEISS)


def p_tray(ctx, x, y, g, o, v, t):
    kw_rund(ctx, x - 420, y - 22, 840, 44, 18); fuell(ctx, rgb("c9cfdc"), 9, rgb("7d8597"))


def p_mug(ctx, x, y, g, o, v, t):
    if g < 5:
        return
    lw = max(6, g * .08)
    if v > .02:
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for k in (-1, 0, 1):
            ph = t * 3 + k * 2
            ctx.move_to(x + k * g * .35, y - g * 1.1)
            for j in range(1, 7):
                ctx.line_to(x + k * g * .35 + math.sin(ph + j * .9) * g * .12, y - g * 1.1 - j * g * .16)
            ctx.set_source_rgba(1, 1, 1, .9 * min(v, 1)); ctx.set_line_width(lw * 1.1); ctx.stroke()
    ctx.arc(x + g * .72, y - g * .35, g * .32, -math.pi / 2, math.pi / 2)
    ctx.set_source_rgb(*kw.kontur(COLORS["red"])); ctx.set_line_width(lw * 2.4); ctx.stroke()
    ctx.arc(x + g * .72, y - g * .35, g * .32, -math.pi / 2, math.pi / 2)
    ctx.set_source_rgb(*COLORS["red"]); ctx.set_line_width(lw * 1.1); ctx.stroke()
    kw_rund(ctx, x - g * .7, y - g * .95, g * 1.4, g * 1.15, g * .18); fuell(ctx, COLORS["red"], lw)
    ellipse(ctx, x, y - g * .92, g * .62, g * .14); fuell(ctx, rgb("7a4a21"))
    for dx, dy in [(-.35, -.5), (.2, -.3), (-.1, -.05), (.4, -.65)]:
        ellipse(ctx, x + dx * g, y + dy * g, g * .07, g * .07); fuell(ctx, kw.WEISS)


def p_stone(ctx, x, y, r, o, v, t):
    if r < 4:
        return
    ctx.move_to(x - r, y + r * .3); ctx.curve_to(x - r * 1.05, y - r * .5, x - r * .3, y - r * .75, x + r * .25, y - r * .65)
    ctx.curve_to(x + r * .9, y - r * .55, x + r * 1.05, y + r * .1, x + r * .8, y + r * .45); ctx.curve_to(x + r * .3, y + r * .7, x - r * .7, y + r * .7, x - r, y + r * .3)
    ctx.close_path(); fuell(ctx, rgb("9aa1ad"), max(5, r * .08), rgb("5d6370"))
    ellipse(ctx, x - r * .3, y - r * .3, r * .22, r * .12, -.3); fuell(ctx, rgb("c4c9d2"))


def p_leaf(ctx, x, y, r, o, v, t):
    if r < 4:
        return
    f = _f(o["farbe"] or "green")
    ctx.save(); ctx.translate(x, y); ctx.rotate(math.sin(t * 2 + o["seed"]) * .25 + o["seed"] * .7)
    ctx.move_to(-r, 0); ctx.curve_to(-r * .5, -r * .7, r * .5, -r * .6, r, 0); ctx.curve_to(r * .5, r * .6, -r * .5, r * .7, -r, 0); ctx.close_path()
    fuell(ctx, f, max(4, r * .08), kw.kontur(f))
    ctx.move_to(-r * 1.25, 0); ctx.line_to(r * .8, 0)
    ctx.set_source_rgb(*kw.kontur(f)); ctx.set_line_width(max(3, r * .07)); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.stroke()
    ctx.restore()


def p_atree(ctx, x, y, g, o, v, t):
    ctx.rectangle(x - 48, y - 470, 96, 480); fuell(ctx, rgb("b0733c"), 9)
    teile = [(-190, 60, 150), (190, 60, 150), (-110, -110, 170), (120, -120, 170), (0, 40, 210), (0, -190, 150)]
    for dx, dy, r in teile:
        ellipse(ctx, x + dx, y - 590 + dy, r, r * .92); fuell(ctx, rgb("ff9a2e"), 9, rgb("b35a00"))
    for dx, dy, r in teile:
        ellipse(ctx, x + dx, y - 590 + dy, r - 9, r * .92 - 9)
    fuell(ctx, rgb("ff9a2e"))
    for i, (dx, dy) in enumerate([(-150, -40), (60, -160), (150, 20), (-40, 90), (-200, 90), (210, 110), (0, -250), (-90, -170)]):
        ellipse(ctx, x + dx, y - 590 + dy, 34, 22, -.4); fuell(ctx, [COLORS["red"], COLORS["yellow"], rgb("a0612b")][i % 3])


def p_pile(ctx, x, y, g, o, v, t):
    if g < 5:
        return
    s = g / 100
    ctx.move_to(x - 190 * s, y + 10 * s); ctx.curve_to(x - 150 * s, y - 150 * s, x + 150 * s, y - 150 * s, x + 190 * s, y + 10 * s); ctx.close_path()
    fuell(ctx, rgb("e07b22"), 9, rgb("8a4a10"))
    rnd = random.Random(2)
    for i in range(16):
        a = rnd.uniform(.15, .85) * math.pi; d = rnd.uniform(.2, .95)
        lx, ly = x - math.cos(a) * 150 * s * d, y - math.sin(a) * 105 * s * d
        f = [COLORS["red"], COLORS["yellow"], COLORS["orange"], rgb("a0612b")][i % 4]
        ellipse(ctx, lx, ly, 30 * s, 16 * s, rnd.uniform(-1, 1)); fuell(ctx, f, 5, kw.kontur(f))


SKAL = ("tree", "bush", "pond", "lily", "xtree", "light", "road", "seesaw", "mound", "bed", "sink", "tray", "atree")
PROPS = dict(egg=p_egg, rocket=p_rocket, seesaw=p_seesaw, nest=p_nest, text=p_text, snowball=p_snowball, snowface=p_snowface, carrot=p_carrot, scarf=p_scarf, xtree=p_xtree, star=p_star, gift=p_gift,
             fish=p_fish, bone=p_bone, shape=p_shape, pond=p_pond, lily=p_lily, box=p_box, ball=p_ball, basket=p_basket, banana=p_banana,
             orange=p_orange, letter=p_letter, light=p_light, road=p_road,
             grapes=p_grapes, hat=p_hat, icecream=p_icecream, mound=p_mound, raincloud=p_raincloud, umbrella=p_umbrella, wind=p_wind,
             night=p_night, bed=p_bed, blanket=p_blanket, face=p_face, car=p_car, boat=p_boat, plane=p_plane, mud=p_mud, sink=p_sink,
             bubbles=p_bubbles, towel=p_towel, drum=p_drum, card=p_card, cookie=p_cookie, tray=p_tray, mug=p_mug, stone=p_stone,
             leaf=p_leaf, atree=p_atree, pile=p_pile)


# ---------------- Zeitleiste ----------------

def _ease(art, k):
    k = max(0.0, min(1.0, k))
    if art == "pop":
        return 1 + math.exp(-5.5 * k) * math.sin(11 * k) * .35 if k < 1 else 1
    if art == "bounce":
        if k < .55:
            return (k / .55) ** 2
        k2 = (k - .55) / .45
        return 1 - abs(math.sin(k2 * math.pi * 2)) * .12 * (1 - k2)
    if art == "in":
        return k * k
    return k * k * (3 - 2 * k)


ATTR = ("x", "y", "s", "v")


class Folge:
    def __init__(self, key):
        self.key, self.ep = key, EPISODEN[key]
        self.obj, self.tw, self.cur = {}, {}, {}
        self.emotes, self.words, self.sparkles, self.pops, self.funken = [], [], [], [], []
        self.konfetti = None
        for oid, kind, p in self.ep["buehne"]:
            p = dict(p)
            size = p.pop("size", 100)
            if kind == "actor":
                p.setdefault("y", GY - 1.5 * size); p.setdefault("s", 0)
            elif kind == "balloon":
                p.setdefault("s", 0)
            self.obj[oid] = dict(kind=kind, size=size, z=p.pop("z", 0), farbe=p.pop("farbe", None), seed=len(self.obj),
                                 art=p.pop("art", None), text=p.pop("text", None))
            for a in ATTR:
                self.cur[oid, a] = p.get(a, 1 if a == "s" else 0); self.tw[oid, a] = []
            self.obj[oid]["init"] = {a: self.cur[oid, a] for a in ATTR}

    def _tween(self, oid, attr, t0, dauer, ziel, ease="io"):
        if ziel is None:
            return
        self.tw[oid, attr].append((t0, dauer, self.cur[oid, attr], ziel, ease)); self.cur[oid, attr] = ziel

    def wert(self, oid, attr, t):
        v = self.obj[oid]["init"][attr]
        for t0, d, v0, v1, e in self.tw[oid, attr]:
            if t < t0:
                break
            v = v0 + (v1 - v0) * _ease(e, (t - t0) / d)
        return v

    def aktion(self, a, t0, zeilen_dauer):
        a = list(a)
        opt = a.pop() if isinstance(a[-1], dict) else {}
        t = t0 + opt.get("at", 0) * zeilen_dauer
        art = a[0]
        if art == "show":
            self._tween(a[1], "s", t, .6, 1, "pop"); self.pops.append(t)
        elif art == "hide":
            self._tween(a[1], "s", t, .25, 0)
        elif art == "scale":
            self._tween(a[1], "s", t, .45, a[2])
        elif art == "tilt":
            self._tween(a[1], "v", t, .6, a[2])
        elif art == "fade":  # Wert v langsam aendern (z. B. Nacht), a[3] = Dauer
            self._tween(a[1], "v", t, a[3] if len(a) > 3 else 1.5, a[2])
        elif art == "spark":
            self.funken.append((a[1], a[2], t)); self.pops.append(t)
        elif art == "set":
            self._tween(a[1], "v", t, .001, a[2]); self.pops.append(t)
        elif art == "place":
            self._tween(a[1], "x", t, .001, a[2]); self._tween(a[1], "y", t, .001, a[3])
        elif art == "move":
            d = a[4] if len(a) > 4 else .8
            self._tween(a[1], "x", t, d, a[2]); self._tween(a[1], "y", t, d, a[3])
        elif art == "drop":
            self._tween(a[1], "x", t, .7, a[2]); self._tween(a[1], "y", t, .7, a[3], "bounce"); self.pops.append(t + .38)
        elif art == "away":
            self._tween(a[1], "y", t, .9, -400, "in")
        elif art in ("jump", "wave", "wiggle"):
            self.emotes.append((a[1], art, t, opt.get("d") or {"jump": .55, "wiggle": .9}.get(art, max(1.0, zeilen_dauer))))
        elif art == "word":
            self.words.append((t, a[1], a[2] if len(a) > 2 else None))
        elif art == "sparkle":
            self.sparkles.append((a[1], t)); self.pops.append(t)
        elif art == "confetti":
            self.konfetti = t

    def emote(self, oid, art, t):
        for o, a, t0, d in self.emotes:
            if o == oid and a == art and t0 <= t < t0 + d:
                return (t - t0) / d
        return None

    # ----- Ton -----
    def vertonen(self, pfad):
        t, teile, self.env = .5, [], {}
        for z in self.ep["zeilen"]:
            wer, text, akt = z[0], z[1], z[2]
            pause = z[3] if len(z) > 3 else .32
            _, voice, pitch = FIGUREN[wer]
            a = stimme(text, voice, pitch)
            d = len(a) / SR
            for ak in akt:
                self.aktion(ak, t, d)
            teile.append((wer, t, a))
            t += d + pause
        self.dauer = t + .5
        n = int(self.dauer * SR)
        voc, hop = np.zeros(n), SR // FPS
        for wer in {w for w, _, _ in teile}:
            spur = np.zeros(n)
            for w, st, a in teile:
                if w == wer:
                    s = int(st * SR); spur[s:s + len(a)] += a[:n - s]
            e = np.array([np.sqrt(np.mean(spur[i:i + hop] ** 2)) for i in range(0, n, hop)])
            e = np.clip(e / (np.percentile(e[e > 0], 90) + 1e-9), 0, 1)
            self.env[wer] = np.convolve(e, [.25, .5, .25], "same")
            voc += spur
        ges = np.array([np.sqrt(np.mean(voc[i:i + hop] ** 2)) for i in range(0, n, hop)])
        duck = np.repeat(np.convolve(ges > .02, np.ones(12) / 12, "same"), hop)[:n]
        seed = sum(map(ord, self.key))
        mix = voc + kw.musik(self.dauer, seed)[:n] * (.22 - .11 * duck) + kw.effekte(self.dauer, self.pops, self.konfetti or self.dauer + 9)[:n] * .4
        mix = mix / max(np.abs(mix).max(), 1e-9) * .92
        mix[-int(.4 * SR):] *= np.linspace(1, 0, int(.4 * SR))
        with wave.open(pfad, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((mix * 32767).astype(np.int16).tobytes())

    def laut(self, wer, i):
        e = self.env.get(wer)
        return float(e[min(i, len(e) - 1)]) if e is not None else 0.0

    # ----- Bild -----
    def zeichne(self, ctx, i):
        t = i / FPS
        (welt_winter if self.ep.get("welt") == "winter" else kw.welt)(ctx, t, self.laut("sunny", i))
        objekte = sorted(self.obj.items(), key=lambda kv: kv[1]["z"])
        self.zeichne_objekte(ctx, t, i, [kv for kv in objekte if kv[1]["z"] < 0])  # z < 0: Hintergrund (z. B. Nacht)
        kw.titel(ctx, "MOTOJUMPER", 660, 92, 50, kw.WEISS, t, welle=0)  # Kanalname in jeder Folge
        kw.titel(ctx, self.ep["titel"], 660, 222, 118, REGENBOGEN, t, maxw=690)
        self.zeichne_objekte(ctx, t, i, [kv for kv in objekte if kv[1]["z"] >= 0])
        self.zeichne_effekte(ctx, t)

    def zeichne_objekte(self, ctx, t, i, objekte):
        for oid, o in objekte:
            x, y, s, v = (self.wert(oid, a, t) for a in ATTR)
            j = self.emote(oid, "jump", t)
            if j is not None:
                y -= math.sin(j * math.pi) * 90
            skal = o["kind"] in SKAL
            if skal:
                if s < .02:
                    continue
                ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.translate(-x, -y)
            wig = self.emote(oid, "wiggle", t)
            wk = math.sin(wig * math.pi * 6) * (1 - wig) if wig is not None else 0
            if o["kind"] == "tree":
                baum(ctx, x, y, t, wk)
            elif o["kind"] == "bush":
                busch(ctx, x + wk * 10, y, t, wk)
            elif o["kind"] == "apple":
                apfel(ctx, x, y, o["size"] * .44 * s, t)
            elif o["kind"] in PROPS:
                PROPS[o["kind"]](ctx, x + wk * 10, y, o["size"] * s, o, v, t)
            elif o["kind"] == "balloon":
                kw.ballon(ctx, x, y + math.sin(t * 2.4 + o["seed"]) * 14, o["size"] * s, COLORS[o["farbe"]], t, o["seed"])
            else:
                lt = self.laut(oid, i)
                kw.tier(ctx, FIGUREN[oid][0], x + wk * 14, y - lt * 7, o["size"] * s, t, o["seed"],
                        wink=self.emote(oid, "wave", t) is not None, sprech=lt)
            if skal:
                ctx.restore()

    def zeichne_effekte(self, ctx, t):
        for fx, fy, t0 in self.funken:
            kw.funkeln(ctx, fx, fy, t, t0, int(t0 * 10), R=230, n=10)
        wort = None
        for t0, text, farbe in self.words:
            if t0 <= t:
                wort = (t0, text, farbe)
        if wort and wort[1]:
            f = REGENBOGEN if wort[2] == "rainbow" else COLORS[wort[2]]
            kw.titel(ctx, wort[1], B / 2, 455, 175 * kw.hopsen(t, wort[0]), f, t, maxw=980)
        for oid, t0 in self.sparkles:
            kw.funkeln(ctx, self.wert(oid, "x", t0 + .3), self.wert(oid, "y", t0 + .3), t, t0, int(t0 * 10), R=300)
        if self.konfetti is not None:
            kw.konfetti(ctx, t, self.konfetti, 7)

    def render(self, ordner):
        os.makedirs(ordner, exist_ok=True)
        wav, out = os.path.join(ordner, f"_{self.key}.wav"), os.path.join(ordner, f"motojumper_{self.key}.mp4")
        self.vertonen(wav)
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{B}x{H}", "-r", str(FPS),
               "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, B, H)
        for i in range(int(self.dauer * FPS)):
            ctx = cairo.Context(surf); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            self.zeichne(ctx, i); surf.flush()
            p.stdin.write(bytes(surf.get_data()))
        p.stdin.close(); p.wait(); os.remove(wav)
        ep = self.ep
        with open(out.replace(".mp4", ".txt"), "w") as f:  # alles fuers Hochladen
            f.write(f"TITEL:\n{ep['yt_titel']}\n\nBESCHREIBUNG:\n{beschreibung(ep)}\n\n"
                    f"TAGS:\n{', '.join(ep['tags'])}\n\nLERNZIEL:\n{ep['lernziel']}\n\nDREHBUCH:\n"
                    + "\n".join(f"{z[0].capitalize()}: {z[1]}" for z in ep["zeilen"]) + "\n")
        return out


def beschreibung(ep):
    """YouTube-Beschreibung im Format aus CLAUDE.md."""
    ziele = f"\n\n✨ What you learn: {ep['ziele']}" if ep.get("ziele") else ""
    return (f"{ep['yt_text']}{ziele}\n\n🌈 New learning stories every day on Motojumper, with Momo, Juju and friends! 💛\n\n"
            f"#shorts {ep.get('hashtags', '#storyforkids')} #kidslearning #preschool #toddlerlearning #educationalvideos")


_K, _CACHE = None, {}


def stimme(text, voice, pitch):
    global _K
    if (text, voice) in _CACHE:
        return _CACHE[text, voice]
    if _K is None:
        kw.stimme("Hi!")  # laedt das Stimm-Modell (und holt die Dateien beim ersten Mal)
        _K = kw._K
    a, sr = _K.create(text, voice=voice, speed=max(.6, .98 / pitch), lang="en-us")
    a = np.asarray(a, dtype=np.float64).flatten()
    laut = np.where(np.abs(a) > .015 * np.abs(a).max())[0]
    a = a[max(0, laut[0] - int(.03 * sr)):laut[-1] + int(.1 * sr)]
    n = int(len(a) * SR / sr / pitch)
    a = np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a)
    a = a / max(np.abs(a).max(), 1e-9) * .9
    _CACHE[text, voice] = a
    return a


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("folge", nargs="?")
    ap.add_argument("--alle", action="store_true")
    ap.add_argument("--liste", action="store_true")
    ap.add_argument("--ordner", default="folgen")
    a = ap.parse_args()
    if a.liste or not (a.folge or a.alle):
        for k, e in EPISODEN.items():
            print(f"{k:10s} {e['titel']:18s} Lernziel: {e['lernziel']}")
    else:
        for k in (EPISODEN if a.alle else [a.folge]):
            print("Fertig:", Folge(k).render(a.ordner))
