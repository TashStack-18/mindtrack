"""
Mindy's reusable content: jokes, riddles, games, small explanations and
reply pools. Kept separate from the conversation engine in mindy_service.py
so content can grow without touching the logic.
"""

# ---------------------------------------------------------------------------
# Jokes, grouped by category. Clean, broadly relatable humour that doesn't
# assume the user's job, country, religion, age or culture, and never punches
# at groups of people. Tech is just one opt-in category, not the default.
# ---------------------------------------------------------------------------
JOKES = {
    'everyday': [
        "Why can't you trust stairs? They're always up to something.",
        "I used to hate facial hair, but then it grew on me.",
        "What did the ocean say to the beach? Nothing, it just waved.",
        "Why did the bicycle fall over? It was two tired.",
        "I made a to-do list to get organised. Step one: find the to-do list.",
        "My alarm clock and I have a complicated relationship. It's always going off on me.",
        "I tried to catch some fog this morning. I mist.",
        "I told my plant a joke. It didn't laugh, but I could tell it was rooting for me.",
    ],
    'food': [
        "Why did the tomato blush? It saw the salad dressing.",
        "What do you call a sad strawberry? A blueberry.",
        "Why did the cookie go to the doctor? It was feeling crummy.",
        "I'm on a seafood diet. I see food and I eat it.",
        "Why don't eggs tell jokes? They'd crack each other up.",
        "What do you call a fake noodle? An impasta.",
        "What do you call cheese that isn't yours? Nacho cheese.",
        "Why did the banana go to the doctor? It wasn't peeling well.",
        "Why don't oysters share their pearls? Because they're shellfish.",
    ],
    'school': [
        "Why did the student eat their homework? The teacher said it was a piece of cake.",
        "Why was the maths book sad? It had too many problems.",
        "What's a teacher's favourite nation? Expla-nation.",
        "Why did the music teacher need a ladder? To reach the high notes.",
        "Why is the library the tallest building? It has the most stories.",
        "Why did the pencil go to the principal's office? It kept making points.",
        "Why did the kid bring a ladder to school? They heard it was high school.",
    ],
    'work': [
        "Why did the scarecrow get a promotion? He was outstanding in his field.",
        "Why did the coffee file a police report? It got mugged.",
        "I wanted to tell you a joke about the office printer, but it's jammed.",
        "Why was the employee fired from the calendar factory? They took a few days off.",
        "My boss told me to have a good day. So I went home.",
        "Why did the clock get a raise? It was always on time and worked around the clock.",
    ],
    'family': [
        "What did the baby corn say to the mama corn? Where's pop corn?",
        "Why are families like fudge? Mostly sweet, with a few nuts.",
        "Grandma started walking five kilometres a day when she was sixty. She's ninety now, and we have no idea where she is.",
        "My parents raised me as an only child, which really annoyed my sister.",
        "Why did the cookie cry? Its mum had been a wafer so long.",
        "What do you call a house full of people arguing over the TV remote? A family meeting.",
    ],
    'animal': [
        "What do you call a sleeping bull? A bulldozer.",
        "Why don't cats play cards in the jungle? Too many cheetahs.",
        "What do you call a bear with no teeth? A gummy bear.",
        "Why do cows wear bells? Because their horns don't work.",
        "What do you call a fish wearing a bowtie? Sofishticated.",
        "Why are frogs so happy? They eat whatever bugs them.",
        "What do you call a dog magician? A labracadabrador.",
        "Why don't elephants use computers? They're scared of the mouse.",
    ],
    'travel': [
        "I told my suitcase there'd be no holiday this year. Now I'm dealing with emotional baggage.",
        "Why don't mountains ever get cold? They wear snow caps.",
        "What did the beach say when the tide came in? Long time, no sea.",
        "Why did the map go to school? It wanted a little direction in life.",
        "I booked a hotel with a view of the sea. Turns out it was a photo of the sea. Still a view, technically.",
        "Why do seagulls fly over the sea? Because if they flew over the bay, they'd be bagels.",
    ],
    'friendship': [
        "What did one plate say to the other? Lunch is on me.",
        "What do you call two birds in love? Tweethearts.",
        "Why did the bee get married? Because he found his honey.",
        "What did the left eye say to the right eye? Between you and me, something smells.",
        "A good friend helps you move. A great friend helps you move and doesn't ask why there are three boxes labelled 'miscellaneous snacks'.",
        "What did one wall say to the other? I'll meet you at the corner.",
    ],
    'wordplay': [
        "I only know 25 letters of the alphabet. I don't know y.",
        "I'm reading a book on anti-gravity. It's impossible to put down.",
        "I used to be a banker, but I lost interest.",
        "I'm terrified of elevators, so I'm taking steps to avoid them.",
        "Time flies like an arrow. Fruit flies like a banana.",
        "What's the best thing about Switzerland? I don't know, but the flag is a big plus.",
        "Did you hear about the claustrophobic astronaut? He just needed a little space.",
    ],
    'silly': [
        "What do you call a fish with no eyes? A fsh.",
        "Why can't a nose be 12 inches long? Because then it would be a foot.",
        "What's orange and sounds like a parrot? A carrot.",
        "What do you call a sleeping dinosaur? A dino-snore.",
        "Why did the golfer bring two pairs of trousers? In case he got a hole in one.",
        "What do you call a pile of cats? A meow-ntain.",
    ],
    'trivia': [
        "Why don't scientists trust atoms? Because they make up everything.",
        "What did the triangle say to the circle? You're pointless.",
        "Why was the geology teacher so calm? She took everything for granite.",
        "Why did the ancient Romans find algebra so easy? Because X was always 10.",
        "What do you call an educated tube? A graduated cylinder.",
        "What did the photon say when asked if it needed help with its luggage? No thanks, I'm travelling light.",
    ],
    'dark': [
        "My grandfather has the heart of a lion... and a lifetime ban from the zoo.",
        "I asked the librarian if they had any books on paranoia. She whispered, 'They're right behind you.'",
        "The cemetery near me is so crowded, people are dying to get in.",
        "My houseplant died while I was away. In my defence, I did tell it to stay hydrated.",
        "I have a joke about procrastination, but I'll tell you later. Possibly never.",
    ],
    'tech': [
        "Why did the computer go to therapy? It had too many unresolved issues.",
        "Why do programmers prefer dark mode? Because light attracts bugs.",
        "There are 10 kinds of people in the world: those who understand binary and those who don't.",
        "A SQL query walks into a bar, goes up to two tables and asks: can I join you?",
        "Why did the developer go broke? They used up all their cache.",
        "How many programmers does it take to change a light bulb? None, that's a hardware problem.",
        "My phone and I have a lot in common: we both run out of energy right when someone needs us.",
    ],
    'knock': [
        "Knock knock. Who's there? Lettuce. Lettuce who? Lettuce in, it's cold out here!",
        "Knock knock. Who's there? Boo. Boo who? Aww, don't cry, it's just a joke!",
        "Knock knock. Who's there? Cow says. Cow says who? No silly, a cow says moooo!",
        "Knock knock. Who's there? Interrupting cow. Interrupting c- MOO!",
        "Knock knock. Who's there? Olive. Olive who? Olive you, and I'm glad you're here!",
    ],
}

# Categories used when someone just asks for "a joke". Dark humour, tech and
# knock-knock jokes are only told when asked for (or when the user enjoys them).
DEFAULT_JOKE_KINDS = ['everyday', 'food', 'school', 'work', 'family', 'animal', 'travel',
                      'friendship', 'wordplay', 'silly', 'trivia']

# Words that pick a category, checked in order (so "dad joke" wins over "dad").
# Includes common spellings and informal phrasing.
JOKE_KIND_KEYWORDS = [
    ('knock', ['knock knock', 'knock-knock', 'knockknock']),
    ('wordplay', ['dad joke', 'dad jokes', 'pun', 'puns', 'punny', 'wordplay', 'word play', 'clever']),
    ('dark', ['dark', 'darker', 'morbid', 'edgy', 'grim']),
    ('tech', ['programming', 'programmer', 'coding', 'code', 'coder', 'computer', 'computers', 'tech', 'techie',
              'developer', 'software', 'geek', 'nerdy tech', 'engineering', 'engineer']),
    ('trivia', ['science', 'scientist', 'history', 'geography', 'trivia', 'nerdy', 'nerd', 'smart', 'chemistry', 'physics']),
    ('animal', ['animal', 'animals', 'cat', 'cats', 'dog', 'dogs', 'pet', 'pets', 'bird', 'birds', 'cow', 'cows', 'zoo', 'farm']),
    ('food', ['food', 'foodie', 'snack', 'snacks', 'pizza', 'cooking', 'cook', 'kitchen', 'fruit', 'eating', 'chef', 'baking', 'dinner', 'lunch']),
    ('school', ['school', 'college', 'uni', 'university', 'student', 'students', 'teacher', 'teachers', 'study',
                'studying', 'exam', 'exams', 'class', 'homework', 'maths', 'math']),
    ('work', ['work', 'office', 'job', 'jobs', 'boss', 'workplace', 'coworker', 'coworkers', 'colleague', 'colleagues',
              'meeting', 'meetings', 'career', 'corporate']),
    ('family', ['family', 'families', 'mom', 'mum', 'mother', 'dad', 'father', 'parents', 'parent', 'sibling',
                'siblings', 'grandma', 'grandpa', 'grandparents', 'kids', 'sister', 'brother']),
    ('travel', ['travel', 'travelling', 'traveling', 'holiday', 'holidays', 'vacation', 'trip', 'beach', 'flight', 'tourist']),
    ('friendship', ['friend', 'friends', 'friendship', 'love', 'relationship', 'relationships', 'romantic', 'romance', 'couple']),
    ('silly', ['silly', 'stupid', 'dumb', 'random', 'absurd', 'weird', 'goofy', 'corny', 'cheesy']),
    ('everyday', ['everyday', 'life', 'relatable', 'normal', 'clean']),
]

JOKE_KIND_NAMES = {
    'everyday': 'everyday', 'food': 'food', 'school': 'school', 'work': 'work', 'family': 'family',
    'animal': 'animal', 'travel': 'travel', 'friendship': 'friendship', 'wordplay': 'pun',
    'silly': 'silly', 'trivia': 'science-y', 'dark': 'dark-ish', 'tech': 'tech', 'knock': 'knock-knock',
}


JOKE_OPENERS = [
    "Okay, okay 😂 ", "Alright, here goes: ", "Okay, this one's a classic. ", "Ready? ",
    "Hehe, okay. ", "You asked for it. ", "", "Okay, I've got one. ",
]
JOKE_CLOSERS = [
    " Want another one?", "", " I'll be here all week.", " One more?", "", " Okay, that one was mostly for me 😄",
]
JOKE_BAD_FEEDBACK = [
    "Okay, rude 😭 but fair. Let me redeem myself: ",
    "Tough crowd! Fine, here's a better one: ",
    "Wow, booed off my own stage. Okay, try this: ",
    "That's fair, that one was mostly for me. How about: ",
]
JOKE_GOOD_FEEDBACK = [
    "Haha, I'm glad that landed 😄 Want another?",
    "Yesss, a laugh! My work here is done. Or... one more?",
    "Okay, I'm taking that as a standing ovation. Another one?",
    "Hehe. I've got plenty more where that came from.",
]

# ---------------------------------------------------------------------------
# Riddles: (question, accepted answer keywords, answer sentence, hint)
# ---------------------------------------------------------------------------
RIDDLES = [
    ("What has keys but can't open locks?", ['piano', 'keyboard'], "A piano!", "You can play it."),
    ("What gets wetter the more it dries?", ['towel'], "A towel!", "You probably used one this morning."),
    ("What has hands but can't clap?", ['clock', 'watch'], "A clock!", "It's always telling you something."),
    ("What can you catch but not throw?", ['cold', 'flu'], "A cold!", "You'd rather not catch it, honestly."),
    ("What goes up but never comes down?", ['age'], "Your age!", "It changes once a year."),
    ("The more of these you take, the more you leave behind. What are they?", ['footstep', 'footsteps', 'steps', 'step'], "Footsteps!", "You make them when you walk."),
    ("What has a neck but no head?", ['bottle'], "A bottle!", "You might drink from it."),
    ("What has one eye but can't see?", ['needle'], "A needle!", "It's used for sewing."),
    ("What is full of holes but still holds water?", ['sponge'], "A sponge!", "It lives by the kitchen sink."),
    ("What can travel around the world while staying in a corner?", ['stamp'], "A stamp!", "It goes on envelopes."),
    ("I'm tall when I'm young and short when I'm old. What am I?", ['candle'], "A candle!", "You light it."),
    ("What has many teeth but can't bite?", ['comb'], "A comb!", "It's for your hair."),
]

RIDDLE_WRONG = [
    "Ooh, nope! Good guess though. Want a hint, or another try?",
    "Not quite! Try again, or say 'hint' if you're stuck.",
    "Close-ish? Actually no 😅 One more try, or I can give you a hint.",
]
RIDDLE_RIGHT = [
    "YES! That's it! 🎉 You're good at this. Another one?",
    "Correct! Okay, I'm impressed. Want another?",
    "Got it in one?! Okay, genius. Want a harder one?",
]

# ---------------------------------------------------------------------------
# Would you rather
# ---------------------------------------------------------------------------
WOULD_YOU_RATHER = [
    ("be able to fly", "be invisible whenever you want"),
    ("always have to sing instead of speak", "always have to dance everywhere you walk"),
    ("have unlimited free food", "unlimited free travel"),
    ("live without music", "live without movies and shows"),
    ("know every language", "be able to talk to animals"),
    ("never have to sleep", "never have to eat"),
    ("have a rewind button for your life", "a pause button"),
    ("live in a treehouse", "live in a houseboat"),
    ("always be 10 minutes late", "always be 20 minutes early"),
    ("have a personal chef", "a personal chauffeur"),
]
WYR_REACTIONS = {
    'a': ["Ooh, solid pick. Honestly, I'd probably go for that one too.", "Okay, I respect it. That one's such a power move."],
    'b': ["Interesting! That one's underrated, honestly.", "Ha, bold choice and I love it."],
    'other': ["Ha, I'll allow that answer 😄", "Okay, that's a creative way out of it."],
}

# ---------------------------------------------------------------------------
# Open-ended questions and hypotheticals
# ---------------------------------------------------------------------------
FUN_QUESTIONS = [
    "If you could instantly master one skill, what would it be?",
    "What's a song you could listen to on repeat right now?",
    "What's the best thing you've eaten recently?",
    "If your life had a theme song this week, what would it be?",
    "What's a tiny thing that always makes your day better?",
    "If you could live in any fictional world, where would you go?",
    "What's something you're weirdly good at?",
    "What's the last thing that made you laugh really hard?",
]
HYPOTHETICALS = [
    "You wake up and you're 10cm tall for one day. What's the first thing you do?",
    "A door appears in your room that leads anywhere you want, but only once. Where do you go?",
    "You can add one completely new subject to every college. What is it?",
    "Every animal can suddenly talk. Which one do you think would be the rudest?",
    "You get a free billboard in the middle of the city for a week. What does it say?",
    "You can swap lives with any fictional character for 24 hours. Who?",
]
QUESTION_REACTIONS = [
    "Okay, I love that answer 😄",
    "Ha, that's such a good one.",
    "Honestly? Excellent choice.",
    "Oh that's interesting, I didn't expect that!",
    "Okay, that tells me a lot about you, and I approve.",
]

# ---------------------------------------------------------------------------
# Word chain: Mindy answers with a word starting with the last letter.
# ---------------------------------------------------------------------------
WORD_BANK = {
    'a': ['apple', 'anchor', 'avocado', 'astronaut'], 'b': ['banana', 'blanket', 'butterfly', 'biscuit'],
    'c': ['cactus', 'candle', 'cookie', 'castle'], 'd': ['dolphin', 'daisy', 'dragon', 'donut'],
    'e': ['elephant', 'emerald', 'eclipse', 'echo'], 'f': ['firefly', 'feather', 'forest', 'flamingo'],
    'g': ['galaxy', 'guitar', 'giraffe', 'garden'], 'h': ['harbor', 'honey', 'hammock', 'helmet'],
    'i': ['igloo', 'island', 'iris', 'ink'], 'j': ['jellyfish', 'jungle', 'jacket', 'jasmine'],
    'k': ['kite', 'koala', 'kettle', 'kingdom'], 'l': ['lantern', 'lemon', 'lighthouse', 'lavender'],
    'm': ['mango', 'meadow', 'marshmallow', 'moon'], 'n': ['notebook', 'nectar', 'noodle', 'nest'],
    'o': ['ocean', 'origami', 'owl', 'orange'], 'p': ['pancake', 'penguin', 'pillow', 'puzzle'],
    'q': ['quilt', 'quokka', 'quartz', 'quest'], 'r': ['rainbow', 'rocket', 'raspberry', 'river'],
    's': ['sunflower', 'sparkle', 'sandwich', 'snowflake'], 't': ['teapot', 'tulip', 'tiger', 'treasure'],
    'u': ['umbrella', 'unicorn', 'ukulele', 'universe'], 'v': ['violin', 'volcano', 'velvet', 'village'],
    'w': ['waffle', 'window', 'whale', 'willow'], 'x': ['xylophone', 'xenon'],
    'y': ['yogurt', 'yacht', 'yarn', 'yellow'], 'z': ['zebra', 'zucchini', 'zigzag', 'zephyr'],
}

FUN_FACTS = [
    "Octopuses have three hearts, and the main one pauses while they swim, which is partly why they prefer crawling.",
    "Honey never spoils. Archaeologists have found edible honey in ancient Egyptian tombs.",
    "A group of flamingos is called a 'flamboyance'.",
    "Bananas are berries, but strawberries aren't, at least botanically.",
    "Sea otters hold hands while they sleep so they don't drift apart.",
    "A day on Venus is longer than its year: it spins so slowly that it orbits the Sun before finishing one rotation.",
    "The shortest war in recorded history, between Britain and Zanzibar in 1896, lasted under an hour.",
    "Butterflies taste with their feet.",
    "The Eiffel Tower can grow about 15 cm taller in summer, because the metal expands in the heat.",
    "A group of owls is called a parliament.",
    "Your nose can remember tens of thousands of different smells.",
    "Some cats are allergic to people.",
    "Scotland's national animal is the unicorn.",
    "Wombat poop is cube-shaped.",
]

# ---------------------------------------------------------------------------
# Small, reliable explanations for common questions. Keys are keyword sets:
# every keyword in a set must appear in the message for that entry to match.
# ---------------------------------------------------------------------------
KNOWLEDGE = [
    ({'fetch', 'pull'}, "Fetch downloads the latest changes from the remote without merging them into your current branch. Pull downloads them and integrates them into your branch. Think of fetch as checking what's new, and pull as bringing those changes into your work."),
    ({'merge', 'rebase'}, "Both combine work from two branches. Merge keeps the full history and adds a merge commit. Rebase replays your commits on top of the other branch, so the history looks like a straight line. A common rule: rebase your own local work, merge shared branches."),
    ({'git', 'commit'}, "A commit is a saved snapshot of your project at a point in time, with a message describing what changed. You stage changes with `git add`, then save them with `git commit -m \"message\"`."),
    ({'recursion'}, "Recursion is when a function solves a problem by calling itself on a smaller version of the same problem, until it reaches a simple 'base case' it can answer directly. Classic example: factorial(n) = n × factorial(n − 1), with factorial(1) = 1 as the base case."),
    ({'api'}, "An API (Application Programming Interface) is a set of rules that lets one program talk to another. For example, a weather app asks a weather service's API for today's forecast and gets data back, without needing to know how that service works inside."),
    ({'list', 'tuple'}, "In Python, a list is mutable (you can change, add or remove items) and uses square brackets [1, 2]. A tuple is immutable (fixed once created) and uses parentheses (1, 2). Use tuples for data that shouldn't change."),
    ({'oop'}, "OOP (object-oriented programming) organises code around objects: bundles of data (attributes) and behaviour (methods). Its key ideas are classes, inheritance, encapsulation and polymorphism."),
    ({'object', 'oriented'}, "Object-oriented programming organises code around objects: bundles of data (attributes) and behaviour (methods). Its key ideas are classes, inheritance, encapsulation and polymorphism."),
    ({'http', 'https'}, "HTTPS is HTTP with encryption (TLS). Plain HTTP sends data as readable text, while HTTPS encrypts it so people on the network can't read or tamper with it. That's why login pages should always use HTTPS."),
    ({'sql', 'join'}, "A SQL JOIN combines rows from two tables based on a related column. INNER JOIN keeps only matching rows; LEFT JOIN keeps every row from the left table and fills in NULLs where there's no match."),
    ({'flask'}, "Flask is a lightweight Python web framework. You define routes (URLs) with decorators like @app.route('/'), and each route returns a response, often an HTML page rendered with Jinja templates. MindTrack itself is built with Flask!"),
    ({'variable'}, "A variable is a named container for a value. In Python, `age = 20` stores the value 20 under the name `age`, so you can use or change it later."),
    ({'algorithm'}, "An algorithm is a step-by-step set of instructions for solving a problem, like a recipe. Sorting a list or finding the shortest route on a map are both done with algorithms."),
    ({'pomodoro'}, "The Pomodoro technique: work with full focus for 25 minutes, take a 5-minute break, and after four rounds take a longer 15 to 30 minute break. It works because short sprints feel much less daunting than 'study for 3 hours'."),
    ({'cbt'}, "CBT (cognitive behavioural therapy) is a structured approach that looks at how thoughts, feelings and actions affect each other. MindTrack's reflection prompts borrow some CBT-inspired questions, like looking for other ways to see a situation, but MindTrack isn't therapy."),
    ({'photosynthesis'}, "Photosynthesis is how plants make food: they use sunlight, water and carbon dioxide to produce glucose (energy) and release oxygen as a by-product."),
    ({'gravity'}, "Gravity is the force that pulls objects with mass toward each other. It keeps us on the ground, keeps the Moon orbiting Earth, and keeps Earth orbiting the Sun."),
    ({'machine', 'learning'}, "Machine learning is a way of building programs that learn patterns from examples instead of following only hand-written rules. Show a model lots of labelled examples, and it learns to make predictions on new ones."),
    # Everyday and general-knowledge questions (not just tech).
    ({'sky', 'blue'}, "Sunlight contains all colours, and as it passes through the air, the tiny gas molecules scatter short blue wavelengths much more than red ones. That scattered blue light reaches your eyes from every direction, so the sky looks blue."),
    ({'sunset', 'orange'}, "At sunset, light travels through much more air to reach you, so most of the blue gets scattered away before it arrives. What's left is the warmer oranges and reds."),
    ({'sunsets', 'red'}, "At sunset, light travels through much more air to reach you, so most of the blue gets scattered away before it arrives. What's left is the warmer oranges and reds."),
    ({'rainbow'}, "A rainbow forms when sunlight enters raindrops, bends, reflects off the back of the drop and bends again on the way out. Each colour bends by a slightly different amount, so white light spreads into a band of colours. You'll see one with the sun behind you and rain in front."),
    ({'seasons'}, "Seasons happen because Earth is tilted on its axis (about 23.5°). For part of the year your half of the planet leans toward the Sun and gets more direct sunlight and longer days (summer), and later it leans away (winter). It's not about being closer to the Sun."),
    ({'leaves', 'colour'}, "In autumn, trees stop making green chlorophyll. As it fades, yellow and orange pigments that were there all along show through, and some trees also make red pigments."),
    ({'leaves', 'color'}, "In autumn, trees stop making green chlorophyll. As it fades, yellow and orange pigments that were there all along show through, and some trees also make red pigments."),
    ({'continents'}, "There are usually said to be seven continents: Africa, Antarctica, Asia, Australia (Oceania), Europe, North America and South America. Some countries teach it slightly differently, for example combining the Americas."),
    ({'largest', 'ocean'}, "The Pacific is the largest ocean. It's bigger than all of Earth's land area combined."),
    ({'tallest', 'mountain'}, "Mount Everest is the highest mountain above sea level, at about 8,849 metres. Measured from base to peak, Mauna Kea in Hawaii is taller, but much of it is underwater."),
    ({'bones', 'body'}, "An adult human usually has 206 bones. Babies are born with more (around 270), and some fuse together as they grow."),
    ({'airplanes', 'fly'}, "Plane wings are shaped and angled so that air moving over and under them gets pushed downward. Pushing air down pushes the wing up, which is lift. Engines provide thrust to keep air flowing over the wings fast enough."),
    ({'planes', 'fly'}, "Plane wings are shaped and angled so that air moving over and under them gets pushed downward. Pushing air down pushes the wing up, which is lift. Engines provide thrust to keep air flowing over the wings fast enough."),
    ({'inflation'}, "Inflation is when prices across an economy rise over time, so the same amount of money buys a bit less. A little inflation is normal; very high inflation makes everyday things noticeably more expensive quickly."),
    ({'calorie'}, "A calorie is a unit of energy. On food labels, 'calories' really means kilocalories: the energy your body can get from that food."),
    ({'calories'}, "A calorie is a unit of energy. On food labels, 'calories' really means kilocalories: the energy your body can get from that food."),
    ({'moon', 'phases'}, "The Moon doesn't make its own light; we see the half lit by the Sun. As it orbits Earth over about 29.5 days, we see different amounts of that lit half, which gives the phases from new moon to full moon and back."),
    ({'boiling', 'water'}, "At sea level, water boils at 100°C (212°F). Higher up, the air pressure is lower, so it boils at a lower temperature, which is why cooking times change in the mountains."),
    ({'compost'}, "Composting is letting food scraps and garden waste break down naturally into rich soil. Mix 'greens' (veg scraps, coffee grounds) with 'browns' (dry leaves, cardboard), keep it slightly damp, and turn it now and then."),
    ({'compiler', 'interpreter'}, "A compiler translates your whole program into machine code before it runs. An interpreter translates and runs it line by line. C is usually compiled; Python is usually interpreted."),
]

# ---------------------------------------------------------------------------
# Accurate descriptions of MindTrack features (keep in sync with the app).
# ---------------------------------------------------------------------------
FEATURE_INFO = {
    'journal': "In the Journal you pick a mood (Very Low to Great), add any feelings that fit, and write whatever you want. You can edit or delete entries any time from your journal history.",
    'insights': "The Insights page looks at your entries over time: mood trends, recurring themes (like sleep, academics or friends), and which themes tend to show up alongside different moods. It points out patterns, it doesn't diagnose anything.",
    'reports': "On the Reports page you can generate a PDF summary of your moods and themes for a date range, which can be handy if you want to share how things have been with a counselor.",
    'privacy': "The text of your journal entries, reflection answers and our chats is encrypted before it's stored, and everything sits behind your login. Things like entry titles and mood scores aren't encrypted, so I'd keep anything super sensitive in the entry text itself.",
    'reflection': "After you write an entry, MindTrack can offer a CBT-inspired reflection prompt, like asking what you'd say to a friend in the same situation. They're totally optional.",
    'sentiment': "MindTrack runs a simple sentiment check (TextBlob) on your entries to estimate whether the writing leans positive, negative or neutral. It's a rough text estimate, separate from the mood you actually pick, and definitely not a diagnosis.",
    'mindy': "I'm Mindy! I'm here to chat, listen, cheer you on, tell terrible jokes, play little games, and help you think things through. I run on built-in logic inside MindTrack, not a big online AI, so I'm better at conversation than at deep research. And I'm not a therapist.",
}

# ---------------------------------------------------------------------------
# Advice, keyed by situation. Each entry: (keywords, advice, follow-up).
# ---------------------------------------------------------------------------
ADVICE = [
    (['ignor', 'not replying', 'left on read', 'no reply', "doesn't reply", 'doesnt reply', 'not texting', 'ghost'],
     "I'd probably start by giving them a little space, then check in once, calmly, instead of sending lots of messages. Something like 'hey, haven't heard from you, everything okay?' leaves the door open without pressure.",
     "Has this been happening for a while, or is it unusual for them?"),
    (['roommate', 'flatmate', 'clean', 'chores'],
     "Pick a calm moment (not right after a fight) and talk about the actual tasks, not who's the worse person. Writing down who does what can take the guesswork and resentment out of it.",
     "Do you think you'd be able to have that conversation with them?"),
    (['exam', 'test', 'study', 'studying', 'revision', 'assignment', 'deadline'],
     "Break it into tiny chunks: pick the one topic or task that matters most and give it 25 focused minutes. Starting is usually the hardest part, and a small win makes the next bit easier.",
     "What's the one thing that's due soonest?"),
    (['procrastinat', 'motivation', 'lazy', 'cant start', "can't start", 'focus'],
     "Try the two-minute rule: commit to just two minutes of the task. Most of the time you'll keep going, and if not, at least you started. Putting your phone in another room helps more than it should.",
     "What's the task you keep avoiding?"),
    (['sleep', 'insomnia', 'cant sleep', "can't sleep", 'tired'],
     "A few things that genuinely help: same wake-up time every day, screens down for a bit before bed, and if your brain won't stop, jotting the thoughts down so they're 'parked' for tomorrow.",
     "Is it more trouble falling asleep, or waking up during the night?"),
    (['presentation', 'speech', 'public speaking', 'interview', 'nervous'],
     "Practice out loud a couple of times, ideally once in front of someone. Know your first two sentences really well, because once you're past the opening, the nerves usually settle.",
     "When is it?"),
    (['breakup', 'broke up', 'ex '],
     "Give yourself permission to feel rubbish for a bit, and lean on people who make you feel like yourself. Muting or archiving their stuff for now isn't dramatic, it's self-protection.",
     "How long ago did it happen?"),
    (['parents', 'mom', 'mum', 'dad', 'family'],
     "With family, timing matters a lot. Try raising it when things are calm, and start with how you feel ('I feel stressed when...') rather than what they're doing wrong. It tends to land better.",
     "Is this a one-off thing or something that keeps coming up?"),
    (['friend', 'friends', 'friendship'],
     "If something's bothering you, talking to them one-on-one is usually better than in the group. You could say something honest but gentle, like 'hey, I've been feeling a bit left out lately'.",
     "Is there one friend you feel closest to in the group?"),
    (['work', 'job', 'boss', 'manager', 'shift'],
     "If it's workload, it's okay to ask your manager which things matter most right now. That's not weakness, it's prioritising. And protect at least a bit of your evening for yourself.",
     "Is it more the amount of work, or the people?"),
    (['lonely', 'alone', 'no friends', 'isolated'],
     "Small steps help: message one person you haven't talked to in a while, or join one club or activity where you'll see the same faces regularly. Regular, low-pressure contact is how friendships grow.",
     "Is there anyone you've been meaning to reach out to?"),
    (['overthink', 'overthinking', 'cant stop thinking', "can't stop thinking"],
     "Try writing the thought down and asking: what do I actually know, and what am I guessing? Often the spiral lives mostly in the guesses. A short walk can break the loop too.",
     "What's the thought that keeps coming back?"),
    (['money', 'broke', 'budget', 'rent'],
     "Writing down exactly where money goes for a week can be eye-opening, and it turns a vague worry into something you can plan around. If it's urgent, your college may have hardship support worth asking about.",
     "Is it a short-term crunch or an ongoing thing?"),
]
GENERAL_ADVICE = [
    ("Honest take? Start with the smallest next step you can actually do today, rather than trying to solve the whole thing at once.",
     "What feels like the biggest part of it?"),
    ("Sometimes it helps to ask: what would I tell a friend in this exact spot? We're usually kinder and clearer with friends than with ourselves.",
     "What would you tell them?"),
]

# ---------------------------------------------------------------------------
# Reply pools for conversational moments. Emojis are used sparingly.
# ---------------------------------------------------------------------------
TEMPLATES = {
    'greeting': [
        "Hey! 💜 I'm Mindy. What's up?",
        "Hii! What's going on with you today?",
        "Hey, you! How's your day been?",
        "Hey! Good to see you. What's on your mind?",
    ],
    'end_conversation': [
        "This was nice. Take care of yourself, okay? I'm here whenever you want to talk again 💜",
        "Okay, we'll leave it here for now. Go be kind to yourself today.",
        "Thanks for hanging out. Talk soon!",
    ],
    'safety_concern': [],  # filled below with SAFETY_MESSAGE
}

GREETING_REPLIES = [
    "Heeey! 💜 What's up?",
    "Hey hey! How's it going?",
    "Hi! Good to see you. What's new?",
    "Hey! How's your day treating you?",
    "Hiii. What are we talking about today?",
]
HOW_ARE_YOU = [
    "I'm good, thanks for asking! Ready to chat. How about you, how's your day going?",
    "Doing well on my end! More importantly, how are YOU?",
    "All good here. What about you, how's today been?",
]
FAREWELLS = [
    "Bye! Take care of yourself 💜",
    "Talk soon! Go have a good rest of your day.",
    "See you! I'm here whenever you want to chat.",
    "Night night! Hope you get some good rest. 🌙",
]
THANKS_REPLIES = [
    "Anytime! 💜",
    "Of course! That's what I'm here for.",
    "Aww, you're welcome.",
    "Always. Anything else on your mind?",
]
BORED_REPLIES = [
    "Okay, we cannot let boredom win today 😭 Pick your vibe: a joke, a riddle, or a quick game?",
    "Bored? Not on my watch. Want a joke, a riddle, or a game of would you rather?",
    "Ooh, I can fix that. Joke, riddle, or a little game?",
]
DISTRACT_REPLIES = [
    "Absolutely. We're changing the subject. Would you rather hear a ridiculous hypothetical, or play a quick guessing game?",
    "Done, new topic! Want a riddle, a weird hypothetical, or a fun fact?",
    "Okay, leaving that behind for now. Joke, riddle, or a guessing game?",
]
LISTEN_MODE_REPLIES = [
    "Of course. No fixing mode, promise 💜 I'm listening. Tell me what's on your mind.",
    "Got it, no solutions, just listening. Go ahead, I'm here.",
    "Totally. I'll just listen. Take your time.",
]
STOP_QUESTIONS_REPLIES = [
    "Fair enough, no more questions from me. I'm just here.",
    "Got it. I'll stop asking and just listen.",
    "Okay, no interrogation. Say whatever you want, whenever.",
]
CELEBRATE = [
    "WAIT, REALLY?! THAT'S AMAZING!! 🥹💜 You must be so happy! Tell me everything!",
    "Okay, this is huge! Congratulations!! 🎉 How are you feeling?",
    "Stop, that's so exciting! I'm genuinely so happy for you. What happened?",
    "YESSS! You deserve this! Tell me all about it.",
]
POSITIVE_REPLIES = [
    "Ooh, I love that! What made it so good?",
    "That's honestly so nice to hear 😊 Tell me more!",
    "Yay! Good days deserve to be talked about. What happened?",
    "That's the best. What was the highlight?",
]
PROUD_REPLIES = [
    "As you should be! That's a real win. What did you do?",
    "Yes! Love that for you. Tell me what you're proud of!",
    "Okay, I'm proud of you too 💜 What happened?",
]
ENCOURAGEMENT = [
    "Hey, you've gotten through every hard day so far, and that's not nothing. One small step at a time is still moving forward. You've got this 💜",
    "You don't have to do it perfectly, you just have to start. And honestly? The fact that you care this much says a lot about you.",
    "Little reminder: it's okay to be a work in progress. You're doing better than you think.",
    "You've handled hard things before, and you can handle this too. I'm cheering for you!",
    "Go get it! And if it doesn't go perfectly, that's okay too. Trying counts.",
]
COMPLIMENT_REPLIES = [
    "Aww, stop it 🥹 You're pretty great yourself.",
    "Okay, that just made my day. Thank you!",
    "Hehe, you're too kind. Right back at you 💜",
]
LAUGH_REPLIES = [
    "Haha 😄",
    "Hehe, right?",
    "😂 Okay, I'm glad you're laughing.",
]
CLARIFY = [
    "Hmm, I'm not totally sure what you mean. Can you say it another way?",
    "Wait, I think I lost you there 😅 What do you mean?",
    "I want to get this right. Can you tell me a bit more?",
]
UNKNOWN_QUESTION = [
    "Honestly, I'm not sure about that one, and I'd rather not make something up. I can't browse the internet either, so a quick search would be more reliable. Happy to talk it through though!",
    "Ooh, that's outside what I know well, and I don't want to give you a wrong answer. I don't have internet access, so I'd double-check that one online. Anything else I can help with?",
]
GENERIC_ACK = [
    "Mm, I hear you.",
    "Yeah, that makes sense.",
    "Okay, I'm following.",
    "Right, got it.",
]
GENERIC_PROMPTS = [
    "What's been on your mind today?",
    "Tell me more?",
    "How are you feeling about it?",
    "What happened next?",
]

# Reactions to emotions, by kind. Each reply acknowledges and invites more.
EMOTION_REPLIES = {
    'sad': [
        "Oh no :( I'm sorry. What's been going on?",
        "Aw, that sounds really heavy. Do you want to tell me what happened?",
        "That's a rough feeling. Is it something specific, or more of a general blah day?",
    ],
    'angry': [
        "Ugh, that sounds so frustrating. What happened?",
        "Okay, I can feel the annoyance from here 😤 Tell me everything.",
        "That would make me mad too. What set it off?",
    ],
    'lonely': [
        "That's a really hard feeling. I'm glad you said something. Has it been like that for a while?",
        "Feeling lonely is rough, especially when it sneaks up on you. What's been going on?",
    ],
    'stressed': [
        "Oof, that sounds like a lot at once. What's weighing on you most?",
        "That's so much to juggle. What's the biggest thing on your plate right now?",
        "Stress like that is exhausting. What's going on?",
    ],
    'worried': [
        "That sounds like it's been sitting on your mind. What's the worry?",
        "Ah, the 'what if' spiral. What are you worried might happen?",
    ],
    'tired': [
        "You sound exhausted. Long day, or has it been building up for a while?",
        "Oof, running on empty? What's been draining you?",
    ],
    'hurt': [
        "Ouch, that can really hurt, especially when it's someone you care about. What happened?",
        "That sounds painful. Do you want to talk about it?",
    ],
    'bad_day': [
        "Oh no :( What happened? Was it one of those everything-goes-wrong days?",
        "Ugh, I'm sorry. Tell me about it. What went wrong?",
        "Oof. Bad days are the worst. What happened?",
    ],
    'weak': [
        "That sounds like a really tired, heavy feeling. Is it more that you're drained, or that things feel like too much right now?",
        "I'm sorry you're feeling that way. What's been taking it out of you?",
    ],
    'overwhelmed': [
        "That's a lot to carry at once. If you had to pick, what's the heaviest part?",
        "Okay, that sounds overwhelming. Let's slow down for a sec. What's on your plate?",
    ],
}

# Listening-only reflections (used in "just listen" mode or after details).
LISTENING = [
    "That sounds really hard.",
    "Yeah. That's a lot.",
    "I'm here. Keep going if you want.",
    "Mm. That makes sense that you'd feel that way.",
    "Honestly, I can see why you'd feel that way.",
    "That's so much to deal with.",
]

# Specific reactions to common details people share in a story.
DETAIL_REACTIONS = [
    (['forgot', 'went blank', 'mind blank', 'blanked'],
     ["Ugh, that feeling when your mind suddenly goes blank is awful.", "Oh no, the brain-freeze moment. That's the worst."],
     ["Did you manage to finish it, at least?", "How did everyone react?"]),
    (['ignored', 'left on read', "didn't reply", 'didnt reply', 'no reply', 'ghosted'],
     ["Being ignored stings, especially by someone you care about.", "Ugh, that silence can feel so loud."],
     ["Is that unusual for them?", "How long has it been?"]),
    (['yelled', 'shouted', 'screamed'],
     ["Getting yelled at is so rattling, even when you know it's not all about you.", "Oof, that's a lot to be on the receiving end of."],
     ["What happened after that?", "Are you okay?"]),
    (['failed', 'fail', 'bad grade', 'low marks', 'bad marks'],
     ["Ugh, that's so disappointing, especially if you put the work in.", "Oof. That one stings."],
     ["Do you know what went wrong, or was it a surprise?", "Is there a chance to make it up?"]),
    (['embarrassed', 'embarrassing', 'embarrassment', 'humiliated', 'humiliating', 'everyone laughed', 'cringe', 'cringey', 'stared', 'staring', 'laughed at me'],
     ["Oh no, the embarrassment replay is so real. Honestly, most people forget these moments way faster than we do.", "Ugh, that hot-face feeling. I'm sorry."],
     ["Is it still replaying in your head?", "What happened exactly?"]),
    (['cancelled', 'canceled', 'bailed', 'flaked'],
     ["Aw, that's such a letdown, especially if you were looking forward to it.", "Ugh, last-minute cancellations are the worst."],
     ["Did they say why?", "Were you really looking forward to it?"]),
    (['cried', 'crying', 'tears'],
     ["Sometimes crying is just your body letting it out. That's okay.", "That sounds like it really got to you."],
     ["How are you feeling now?", "Did it help a little, or is it still heavy?"]),
    (['argued', 'argument', 'fight', 'fought'],
     ["Arguments with people you live or spend time with are so draining.", "Ugh, fights leave such a weird feeling afterwards."],
     ["Have you two talked since?", "What was it about?"]),
    (['nobody', 'no one', 'noone'],
     ["That feeling of nobody being there really hurts.", "Ouch. That's a lonely feeling."],
     ["Did something happen that made it feel that way?", "Is there anyone who usually gets it?"]),
    (['late', 'missed'],
     ["Oh no, that rushing panic is the worst.", "Ugh, missing it on top of everything else."],
     ["Did it work out in the end?", "Was it a big deal, or more just annoying?"]),
    (['said i', 'told me', 'said that'],
     ["Oof. Hearing that would be frustrating, especially if you feel it's not fair.", "That's a lot to hear from someone."],
     ["How did you respond?", "Do you think they meant it, or was it said in the heat of the moment?"]),
]

ADVICE_OR_LISTEN = [
    " Do you want advice, or should I just listen?",
    " Want my honest take, or do you just need to get it out?",
]

AGREEMENT_PREFIX = [
    "Right, exactly.",
    "Yeah, that makes total sense.",
    "Mm, I get that.",
]

SAFETY_MESSAGE = (
    "I'm really glad you told me, and I'm taking this seriously. You deserve support right now from a real person. "
    "Please reach out to someone you trust, or contact a crisis line. If you're in India, you can call Tele-MANAS on 14416, free and 24/7. "
    "If you might act on these thoughts or you're in danger, please call your local emergency number (112 in India) right now. "
    "I'm not a therapist and I can't help in an emergency, but I'm still here with you. Are you safe right now?"
)
SAFETY_FOLLOWUP = (
    "I'm still here with you. Please do reach out to someone right now, whether that's a friend, family member, "
    "Tele-MANAS on 14416 if you're in India, or your local emergency number. You don't have to carry this alone."
)
SAFETY_RELIEVED = [
    "Okay. Thank you for telling me, and I'm glad you're safe. I'm here if you want to keep talking, about that or anything else.",
    "I'm really glad. If those feelings come back strongly, please reach out to someone you trust or a crisis line. I'm here to talk whenever.",
]

TEMPLATES['safety_concern'] = [SAFETY_MESSAGE]

STARTER_SUGGESTIONS = [
    "Tell me a joke 😂",
    "I'm bored. Entertain me.",
    "Can I vent for a minute?",
    "Help me think something through.",
    "Let's play a game.",
]
