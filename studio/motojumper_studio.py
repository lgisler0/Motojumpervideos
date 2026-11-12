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


PROPS = dict(snowball=p_snowball, snowface=p_snowface, carrot=p_carrot, scarf=p_scarf, xtree=p_xtree, star=p_star, gift=p_gift,
             fish=p_fish, bone=p_bone, shape=p_shape, pond=p_pond, lily=p_lily, box=p_box, ball=p_ball, basket=p_basket, banana=p_banana,
             orange=p_orange, letter=p_letter, light=p_light, road=p_road)


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
        self.emotes, self.words, self.sparkles, self.pops = [], [], [], []
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
            self.emotes.append((a[1], art, t, {"jump": .55, "wiggle": .9}.get(art, max(1.0, zeilen_dauer))))
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
        kw.titel(ctx, "MOTOJUMPER", 660, 92, 50, kw.WEISS, t, welle=0)  # Kanalname in jeder Folge
        kw.titel(ctx, self.ep["titel"], 660, 222, 118, REGENBOGEN, t, maxw=690)
        for oid, o in sorted(self.obj.items(), key=lambda kv: kv[1]["z"]):
            x, y, s, v = (self.wert(oid, a, t) for a in ATTR)
            j = self.emote(oid, "jump", t)
            if j is not None:
                y -= math.sin(j * math.pi) * 90
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
               "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, B, H)
        for i in range(int(self.dauer * FPS)):
            ctx = cairo.Context(surf); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            self.zeichne(ctx, i); surf.flush()
            p.stdin.write(bytes(surf.get_data()))
        p.stdin.close(); p.wait(); os.remove(wav)
        ep = self.ep
        with open(out.replace(".mp4", ".txt"), "w") as f:  # alles fuers Hochladen
            ziele = f"\n\nLearning goals: {ep['ziele']}" if ep.get("ziele") else ""
            f.write(f"TITEL:\n{ep['yt_titel']}\n\nBESCHREIBUNG:\n{ep['yt_text']}{ziele}\n\n"
                    f"🌈 A new learning story every day on Motojumper, with Momo, Juju and friends!\n\n"
                    f"#shorts {ep.get('hashtags', '#storyforkids #preschool')} #kidslearning\n\n"
                    f"TAGS:\n{', '.join(ep['tags'])}\n\nLERNZIEL:\n{ep['lernziel']}\n\nDREHBUCH:\n"
                    + "\n".join(f"{z[0].capitalize()}: {z[1]}" for z in ep["zeilen"]) + "\n")
        return out


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
