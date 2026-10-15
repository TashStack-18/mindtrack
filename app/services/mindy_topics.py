"""
Everyday topics Mindy can talk about specifically (instead of generic replies).

Each topic has:
  patterns   regexes matched against the normalised message (lowercase, no apostrophes)
  valence    'hard' (support), 'good' (celebrate), 'mixed' or 'neutral'
  ref        how Mindy refers back to it later ("your period", "being sick")
  openers    first reply when the topic comes up ({thing} = captured detail, if any)
  details    (regex, replies) for things people commonly add while on the topic
  followups  questions Mindy can ask over the next turns (each used once)
  tips       a few practical, non-medical ideas, only given when the user wants advice

Replies are written in Mindy's normal voice; mindy_service adapts casing and
emoji to how the user writes.
"""

TOPICS = [
    {
        'id': 'period',
        'patterns': [r'\bperiods?\b', r'\bcramps?\b', r'\bcramping\b', r'\bpms\b', r'\bmenstrua\w*', r'\bthat time of the month\b'],
        'valence': 'hard',
        'ref': 'your period',
        'openers': [
            "Oh no, period days can be so rough 😣 Are you getting cramps too, or is it more the tiredness?",
            "Ugh, periods. Sending you a virtual hot water bottle 🫶 How bad is it today?",
            "Aw, periods can really take it out of you. How are you holding up, cramps or mostly just drained?",
        ],
        'details': [
            (r'\bcramps?\b|\bcramping\b|\bpain\b|\bhurts?\b|\bstomach\b|\bback\b', [
                "Cramps can be brutal, honestly. Do you have a hot water bottle or heating pad you can use?",
                "Ugh, cramps on a bad day are the worst. Are you able to lie down for a bit?",
            ]),
            (r'\bclass(es)?\b|\bcollege\b|\bschool\b|\bwork\b|\boffice\b|\blecture', [
                "Having to sit through class while dealing with that is genuinely unfair 😭 Can you take it easy once you're home?",
                "Doing a full day on top of period pain deserves an award, honestly. Will you get some rest after?",
            ]),
            (r'\bmood\w*\b|\bcry\w*\b|\birritat\w*\b|\bemotional\b|\bsnappy\b|\bangry\b', [
                "That makes so much sense. Hormones can turn the volume up on every feeling. Go easy on yourself today.",
                "Totally normal to feel more emotional right now. You don't have to have it all together today.",
            ]),
            (r'\btired\b|\bexhausted\b|\bdrained\b|\bsleepy\b|\bweak\b|\bdizzy\b', [
                "That tired, heavy feeling is real. Rest is a very valid plan for today.",
                "Yeah, it can drain your energy so much. Have you eaten something and had enough water?",
            ]),
            (r'\bmedicine\b|\bmeds\b|\btablet\b|\bpainkiller\w*\b|\bpill\b', [
                "Okay good, hopefully that kicks in soon. If the pain is ever way worse than usual for you, it's worth checking with a doctor.",
            ]),
            (r'\bcraving\w*\b|\bchocolate\b|\bsnack\w*\b|\bjunk\b', [
                "Honestly? Eat the chocolate. Period cravings are a whole mood 🍫",
            ]),
        ],
        'followups': [
            "Are you able to rest a bit today?",
            "Do you have something warm to drink nearby?",
            "Is today one of the heavier days?",
        ],
        'tips': "A few things that help a lot of people: a hot water bottle or heating pad on your tummy or lower back, something warm to drink, gentle stretching or a slow walk, and staying hydrated. And if the pain is ever severe or unusual for you, a doctor can genuinely help.",
    },
    {
        'id': 'sick',
        'patterns': [r'\bfever\b', r'\bflu\b', r'\b(have|got|caught) (a )?cold\b', r'\bsick\b(?! of)', r'\bunwell\b', r'\bheadache\b', r'\bmigraine\b',
                     r'\bstomach ?ache\b', r'\b(head|stomach|tummy|throat|body|ear|tooth) (hurts|is hurting|aches|is aching|pain)\b', r'\b(toothache|earache|body ache)\b',r'\bvomit\w*\b', r'\bthrowing up\b', r'\bsore throat\b', r'\bcough\w*\b', r'\bnot feeling (well|good)\b'],
        'valence': 'hard',
        'ref': 'being unwell',
        'openers': [
            "Oh no, being sick is the worst 😣 How are you feeling right now?",
            "Aw, I'm sorry you're unwell. Have you been able to rest at all?",
            "Ugh, that sounds miserable. Are you taking it easy today?",
        ],
        'details': [
            (r'\bcollege\b|\bschool\b|\bclass(es)?\b|\bwork\b|\boffice\b|\bmiss(ed)?\b|\bcouldnt go\b', [
                "Honestly, staying home was the right call. Your body needs the rest more than anything right now.",
                "Missing a day when you're sick is completely okay. You can catch up once you feel better.",
            ]),
            (r'\bdoctor\b|\bmedicine\b|\bmeds\b|\btablet\b|\bhospital\b', [
                "Good that you're looking after it. Hope the medicine helps soon.",
            ]),
            (r'\balone\b|\bno one\b|\bnobody\b|\bhostel\b', [
                "Being sick on your own is extra hard. Is there anyone who can check in on you or bring you food?",
            ]),
            (r'\bbored\b', [
                "Sick-day boredom is real. Want me to tell you a joke or play a gentle little game while you rest?",
            ]),
        ],
        'followups': [
            "Have you been drinking enough water?",
            "Did you manage to eat something?",
            "Is anyone around to help you out?",
        ],
        'tips': "Rest, fluids, something light to eat, and actually letting yourself sleep. If the fever is very high, lasts more than a couple of days, or you're getting worse, please see a doctor.",
    },
    {
        'id': 'family_compare',
        'opener_first': True,
        'patterns': [r'\bcompar\w*\b.*\b(me|cousin|sister|brother|sibling|friend)\b', r'\bwhy cant you be (like|more like)\b',
                     r'\bbe (more )?like (my|her|him|them)\b', r'\b(parents|mom|mum|dad|family)\b.*\b(expect\w*|pressure\w*|disappointed in me)\b'],
        'valence': 'hard',
        'ref': 'being compared',
        'openers': [
            "Ugh, being compared to someone else hurts so much, especially by family. What did they say?",
            "Oof, that comparison thing is so draining. Has it been happening a lot lately?",
        ],
        'details': [
            (r'\bnot enough\b|\bnot good enough\b|\bworthless\b|\bfailure\b|\bdisappoint\w*\b', [
                "I really don't think you're 'not enough'. Being compared says more about their expectations than about your worth.",
                "That feeling makes total sense after hearing that, but it isn't the truth about you. You're your own person, not a copy of anyone.",
            ]),
            (r'\bwhy cant you\b|\bsaid\b|\btold me\b', [
                "Hearing that out loud stings, even if they think they're motivating you.",
                "Oof. Words like that from family can stay in your head for days.",
            ]),
            (r'\bcousin\b|\bsister\b|\bbrother\b|\bsibling\b', [
                "It's hard when it's someone you're close to, because then you can't even fully be annoyed at them. It's not their fault either.",
            ]),
            (r'\balways\b|\bevery time\b|\bagain\b', [
                "When it keeps happening, it really wears you down. That's a lot to carry quietly.",
            ]),
        ],
        'followups': [
            "How did you react when they said it?",
            "Do you feel like you could tell them how it makes you feel?",
            "What's something you're proud of that they might not see?",
        ],
        'tips': "Some people find it helps to tell a parent calmly, at a good moment, 'when you compare me it makes me feel like I'm not enough', rather than arguing in the moment. It can also help to keep a small list of your own wins, so their words aren't the only voice in your head.",
    },
    {
        'id': 'family_fight',
        'opener_first': True,
        'patterns': [r'\b(fight|fought|argu\w*|shout\w*|yell\w*|scold\w*|screamed)\b.*\b(mom|mum|dad|parents|mother|father|sister|brother|family)\b',
                     r'\b(mom|mum|dad|parents|mother|father)\b.*\b(fight|fought|argu\w*|shout\w*|yell\w*|scold\w*|screamed|angry at me|mad at me)\b'],
        'valence': 'hard',
        'ref': 'the fight at home',
        'openers': [
            "Oh no, fights at home are so draining because you can't really get away from it. What happened?",
            "Ugh, I'm sorry. What was it about?",
        ],
        'details': [
            (r'\bunfair\b|\bnot my fault\b|\bdidnt do\b|\bblame\w*\b', [
                "Being blamed for something that doesn't feel fair is so frustrating.",
            ]),
            (r'\bcry\w*\b|\bupset\b|\bhurt\b', [
                "That sounds like it really hurt. It's okay to still feel shaken after.",
            ]),
            (r'\bstill\b|\bnot talking\b|\bsilent\b|\bignor\w*\b', [
                "That awkward silent phase after a fight is the worst.",
            ]),
        ],
        'followups': [
            "Have things calmed down at all since?",
            "How are you feeling about it now?",
            "Do you think they'd be open to talking once everyone's cooled off?",
        ],
        'tips': "Once everyone has cooled down, a short, calm conversation usually goes better than continuing the argument. Starting with how you felt ('I felt hurt when…') tends to land better than what they did wrong.",
    },
    {
        'id': 'friend_moving',
        'opener_first': True,
        'patterns': [r'\b(friend|bestie|bff|best friend)\b.*\b(moving|shifting|leaving|relocating|moved)\b', r'\b(moving|shifting) (away|abroad|to another (city|country|place))\b'],
        'valence': 'hard',
        'ref': 'your friend moving away',
        'openers': [
            "Aw, that's genuinely sad. Even when you know you'll stay in touch, it's a big change. When are they leaving?",
            "Oh no, that's a hard one. How are you feeling about it?",
        ],
        'details': [
            (r'\bsince\b|\byears\b|\bgrade\b|\bchildhood\b|\bforever\b|\blong time\b', [
                "Friends you've had since you were little are so special. That kind of history doesn't disappear with distance.",
                "That's such a long friendship. No wonder this feels big.",
            ]),
            (r'\bmiss\b|\balone\b|\blonely\b|\bwithout (her|him|them)\b', [
                "It makes total sense to miss them already. You're allowed to be sad about it.",
            ]),
            (r'\bcall\b|\btext\b|\bvisit\b|\bstay in touch\b', [
                "That's a really good plan. Lots of friendships stay strong across distance with regular calls and the odd visit.",
            ]),
        ],
        'followups': [
            "Are you planning to do something special before they go?",
            "How long have you two been friends?",
            "Do you think you'll be able to visit each other?",
        ],
        'tips': "Some ideas: plan one proper goodbye day together, set up a regular call or a shared playlist, and pick a date for a first visit so there's something to look forward to.",
    },
    {
        'id': 'friend_conflict',
        'opener_first': True,
        'patterns': [r'\b(friend|friends|bestie|bff)\b.*\b(ignor\w*|fight|fought|argu\w*|mad at me|upset with me|not talking|left me out|ghost\w*|blocked)\b',
                     r'\b(left me out|excluded me|didnt invite me)\b'],
        'valence': 'hard',
        'ref': 'what happened with your friend',
        'openers': [
            "Oh no, friend stuff can hurt so much. What happened?",
            "Ugh, that's such a horrible feeling. Did something happen, or did it just kind of start?",
        ],
        'details': [
            (r'\bignor\w*\b|\bleft on read\b|\bnot replying\b|\bghost\w*\b', [
                "Being ignored by someone you care about stings so much, especially when you don't know why.",
            ]),
            (r'\bleft out\b|\bexcluded\b|\bdidnt invite\b|\bwithout me\b', [
                "Feeling left out is honestly one of the worst feelings. That would hurt anyone.",
            ]),
            (r'\bmy fault\b|\bi said\b|\bi did\b', [
                "It's kind of you to think about your side too. Most fights have a bit on both sides.",
            ]),
        ],
        'followups': [
            "Is this unusual for them?",
            "Have you been able to talk to them about it?",
            "How long have you two been friends?",
        ],
        'tips': "I'd probably give them a little space first, then check in once, calmly, with a one-on-one message instead of lots of texts. Something like 'hey, haven't heard from you, everything okay?' opens the door without blaming.",
    },
    {
        'id': 'breakup',
        'opener_first': True,
        'patterns': [r'\bbroke up\b', r'\bbreak ?up\b', r'\bmy ex\b', r'\bdumped\b', r'\bwe ended (it|things)\b'],
        'valence': 'hard',
        'ref': 'the breakup',
        'openers': [
            "Oh, I'm really sorry. Breakups hurt so much, even when they make sense. How are you doing?",
            "Aw, that's a lot. Was it recent?",
        ],
        'details': [
            (r'\bmiss\b|\bcry\w*\b|\bsad\b', ["Of course you miss them. That doesn't go away overnight, and that's okay."]),
            (r'\bmy fault\b|\bblame\b', ["Breakups are rarely one person's fault. Try not to put all of it on yourself."]),
            (r'\btext\w*\b|\bcall\w*\b|\bunblock\w*\b', ["The urge to text is so real. Maybe wait a day and see if you still want to?"]),
        ],
        'followups': ["How long were you together?", "Do you have friends around you right now?", "How have you been sleeping?"],
        'tips': "Let yourself feel rubbish for a bit, lean on people who make you feel like yourself, and muting their stuff for now isn't dramatic, it's self-protection.",
    },
    {
        'id': 'crush',
        'patterns': [r'\bcrush\b', r'\b(i|i really) like (someone|this (guy|girl|person))\b', r'\basked (him|her|them) out\b', r'\bshe likes me\b', r'\bhe likes me\b'],
        'valence': 'good',
        'ref': 'your crush',
        'openers': ["Ooh, a crush! 👀 Okay, tell me everything. Who is it?", "Wait, spill. How do you know them?"],
        'details': [
            (r'\btalk\w*\b|\btext\w*\b|\bsmiled\b|\bdm\w*\b', ["Okay that's actually so cute. How did it feel?"]),
            (r'\bnervous\b|\bscared\b|\bshy\b', ["Totally normal to be nervous, it means you care. Small steps, like a normal chat, are a great start."]),
            (r'\bdoesnt like me\b|\brejected\b|\bnot interested\b', ["Oof, that stings. It says nothing about your worth though."]),
        ],
        'followups': ["Do they know you like them?", "What do you like about them?", "Are you thinking of saying something?"],
        'tips': "Start small: a normal conversation about something you both like. No pressure to confess anything big right away.",
    },
    {
        'id': 'exam_result',
        'patterns': [r'\b(failed|flunked)\b', r'\b(bad|low|poor) (marks|grades?|score|result)\b', r'\bgot (a )?(bad|low) (mark|grade|score)\b', r'\b(results?) (were|was|came out)\b.*\b(bad|terrible|awful)\b'],
        'valence': 'hard',
        'ref': 'the result',
        'openers': [
            "Ugh, that's so disappointing, especially when you've put work in. How are you feeling about it?",
            "Oh no, I'm sorry. Was it a surprise, or were you half expecting it?",
        ],
        'details': [
            (r'\bparents\b|\bmom\b|\bmum\b|\bdad\b|\bfamily\b', ["Worrying about telling family can feel worse than the mark itself. Do you know how they might react?"]),
            (r'\bstudied\b|\bworked hard\b|\btried\b', ["That makes it sting even more. One result doesn't erase the effort you put in."]),
            (r'\bretake\b|\bresit\b|\bsupplementary\b|\bnext time\b', ["Good that there's another chance. You'll know exactly what to focus on now."]),
        ],
        'followups': ["Do you know which parts went wrong?", "Is there a chance to make it up?", "What would help you feel a bit better tonight?"],
        'tips': "When you feel ready, look at where the marks were lost (it's usually a few specific things), and ask the teacher what to focus on. Tonight, though, just rest. One result is information, not a verdict on you.",
    },
    {
        'id': 'exam',
        'patterns': [r'\bexams?\b', r'\b(test|tests|quiz|midterms?|finals|viva|boards)\b', r'\bstudying for\b', r'\bhavent studied\b'],
        'valence': 'hard',
        'ref': 'the exam',
        'openers': [
            "Ooh, exam time. How are you feeling about it, ready-ish or full panic?",
            "Oof, exams. When is it?",
        ],
        'details': [
            (r'\bhavent (studied|started)\b|\bnot prepared\b|\bnothing\b|\bso much\b|\bsyllabus\b|\bportion\b', [
                "Okay, deep breath. You don't need to cover everything, just the most important bits first.",
                "That panic is so real. Even a couple of focused hours can make a big difference.",
            ]),
            (r'\btomorrow\b|\btonight\b|\btoday\b', ["Tomorrow?! Okay, we're in focus mode. Pick the topics most likely to come up and do those first."]),
            (r'\bcant focus\b|\bdistract\w*\b|\bphone\b', ["Try putting your phone in another room for 25 minutes. It's weirdly powerful."]),
            (r'\bwent (well|good|great)\b|\beasy\b', ["Yesss! That's such a relief. Proud of you!"]),
            (r'\bwent (bad|badly|terribly|horribly)\b|\bhard\b|\bblank\b', ["Ugh, I'm sorry. Exams like that are so draining. It's done now though."]),
        ],
        'followups': ["Which subject is it?", "How much is left to cover?", "Are you studying alone or with friends?"],
        'tips': "Pick the 2–3 topics most likely to come up and do those first. Study in 25-minute bursts with 5-minute breaks, and do a few past questions instead of only re-reading. And sleep counts as revision, honestly.",
    },
    {
        'id': 'assignment',
        'patterns': [r'\bassignments?\b', r'\bdeadlines?\b', r'\bhomework\b', r'\bsubmission\b', r'\bproject (is )?due\b', r'\bdue (tomorrow|tonight|today)\b'],
        'valence': 'hard',
        'ref': 'the assignment',
        'openers': ["Ugh, deadlines. When is it due?", "Oof, how much of it is left?"],
        'details': [
            (r'\btomorrow\b|\btonight\b|\btoday\b', ["Okay, crunch time. What's the smallest part you could finish in the next half hour?"]),
            (r'\bnot started\b|\bhavent started\b|\bprocrastinat\w*\b', ["Starting is always the hardest part. Even writing a rough heading counts as starting."]),
            (r'\bdone\b|\bsubmitted\b|\bfinished\b', ["YES, submitted! That relief is the best feeling. Treat yourself."]),
        ],
        'followups': ["What's it on?", "How much is left?", "Is it a group project or just you?"],
        'tips': "Break it into tiny pieces and start with the easiest one to build momentum. A rough draft first, polishing later.",
    },
    {
        'id': 'presentation',
        'patterns': [r'\bpresentations?\b', r'\bspeech\b', r'\bpublic speaking\b', r'\bpresent(ing)? (in front|tomorrow|today)\b'],
        'valence': 'mixed',
        'ref': 'the presentation',
        'openers': ["Ooh, a presentation. Is it coming up, or did it already happen?", "Presentations can be so nerve-wracking. How's it going?"],
        'details': [
            (r'\bnervous\b|\bscared\b|\banxious\b|\bpanic\w*\b', ["Nerves are so normal, it means you care. Practising your first two lines out loud really helps."]),
            (r'\bforgot\b|\bblank\b|\bblanked\b', ["Ugh, that feeling when your mind suddenly goes blank is awful. Did you manage to finish it, at least?",
                                                   "Oh no, the brain-freeze moment. Most people notice it way less than you think, though."]),
            (r'\bwent (bad|badly|terribly|horribly|wrong)\b|\bmessed up\b|\bdisaster\b', ["Oh no :( What happened? Did something go wrong during the presentation, or does it just feel like it didn't go as well as you hoped?"]),
            (r'\bwent (well|good|great)\b|\bnailed\b|\bclapped\b', ["That's amazing! You should be proud, that takes guts."]),
            (r'\bstared\b|\blaughed\b|\bembarrass\w*\b', ["Oof, that feeling is the worst. Honestly, people forget these moments way faster than we do."]),
        ],
        'followups': ["What's it about?", "Have you practised it out loud yet?", "How many people will be there?"],
        'tips': "Practise out loud a couple of times, ideally once to someone. Know your first two sentences really well; once you're past the opening, the nerves usually settle.",
    },
    {
        'id': 'roommate',
        'patterns': [r'\broommates?\b', r'\bflatmates?\b', r'\bhostel ?mates?\b'],
        'valence': 'mixed',
        'ref': 'your roommate',
        'openers': ["Ah, roommate life. What's going on?", "Oh no, roommate drama? What happened?"],
        'details': [
            (r'\bargu\w*\b|\bfight\b|\bfought\b|\byell\w*\b|\bshout\w*\b', ["Oh no, fights with a roommate are extra hard because you can't really get away from each other. What happened?"]),
            (r'\bclean\w*\b|\bmess\w*\b|\bdishes\b|\bchores?\b', ["The cleaning fights are SO common. It's frustrating when it feels like you're doing more than your share."]),
            (r'\bnoise\b|\bloud\b|\blate\b|\bsleep\b', ["Not being able to rest in your own room is so draining."]),
            (r'\bsaid\b|\btold me\b|\bblamed\b', ["Oof, hearing that would be frustrating, especially if it doesn't feel fair."]),
        ],
        'followups': ["Have you two talked about it?", "Is this a one-off or a pattern?", "Do you usually get along?"],
        'tips': "Pick a calm moment and talk about the specific thing (not who's the worse person). Writing down who does what can take the resentment out of it.",
    },
    {
        'id': 'work',
        'patterns': [r'\bboss\b', r'\bmanager\b', r'\bcoworkers?\b', r'\bcolleagues?\b', r'\b(at|from) (work|the office)\b', r'\bmy (job|shift)\b', r'\binternship\b'],
        'valence': 'mixed',
        'ref': 'work',
        'openers': ["Ah, work stuff. What's going on?", "How's work been treating you?"],
        'details': [
            (r'\bboss\b|\bmanager\b', ["Bosses can make or break a day. What did they do?"]),
            (r'\btoo much\b|\boverload\w*\b|\blate\b|\bovertime\b', ["That sounds like way too much for one person. It's okay to ask what to prioritise."]),
            (r'\bpraised\b|\bpromot\w*\b|\bappreciat\w*\b|\bwent well\b', ["Ooh, that's great! Love that for you."]),
        ],
        'followups': ["Is it more the workload or the people?", "How long has it been like this?", "Do you get some time off soon?"],
        'tips': "If it's workload, it's okay to ask your manager which things matter most right now. That's prioritising, not weakness. And protect a bit of your evening for yourself.",
    },
    {
        'id': 'job_search',
        'patterns': [r'\b(job|internship|placement)\b.*\b(rejected|rejection|interview|applied|applying|offer)\b', r'\bgot rejected\b', r'\bdidnt get (the job|selected|the internship)\b', r'\bplacements?\b'],
        'valence': 'mixed',
        'ref': 'the job hunt',
        'openers': ["Ah, the job hunt is such a rollercoaster. What's the latest?", "How's the search going?"],
        'details': [
            (r'\brejected\b|\brejection\b|\bdidnt get\b', ["Rejections sting, even though they happen to everyone. It's one 'no' on the way to a 'yes'."]),
            (r'\binterview\b', ["Ooh, an interview! Are you feeling ready?"]),
            (r'\boffer\b|\bselected\b|\bgot (it|the job)\b', ["WAIT, really?! That's huge, congratulations!! 🎉"]),
        ],
        'followups': ["What kind of role are you going for?", "How many places have you applied to?", "Is there one you're really hoping for?"],
        'tips': "Ask for feedback when you can, tweak your CV for each role, and track applications in a little list so it feels less endless. Rejections are part of everyone's process.",
    },
    {
        'id': 'lonely',
        'opener_first': True,
        'patterns': [r'\blonely\b', r'\bno one to talk to\b', r'\bno friends\b', r'\balone all the time\b', r'\bfeel (so )?alone\b'],
        'valence': 'hard',
        'ref': 'feeling lonely',
        'openers': ["That's a really hard feeling, and I'm glad you said it out loud. Has it been like this for a while?", "I'm here, and I'm glad you're talking to me. What's been making it feel that way?"],
        'details': [
            (r'\bnew (city|college|school|place)\b|\bmoved\b|\bhostel\b', ["Being somewhere new makes loneliness so much louder. Friendships take time to grow there, it's not you."]),
            (r'\bfriends\b.*\bbusy\b|\bbusy\b', ["It's hard when everyone seems to have their own thing going on."]),
            (r'\bweekend\w*\b|\bnight\w*\b|\bevening\w*\b', ["Those quiet times can feel the heaviest."]),
        ],
        'followups': ["Is there anyone you've been meaning to reach out to?", "Are there any clubs or groups around you that sound even a little fun?", "What usually helps, even a bit?"],
        'tips': "Small steps help: message one person you haven't talked to in a while, or join one regular activity where you'll see the same faces. Regular, low-pressure contact is how friendships grow. And I'm here to chat too.",
    },
    {
        'id': 'homesick',
        'opener_first': True,
        'patterns': [r'\bhomesick\b', r'\bmiss (home|my family|my parents|my mom|my mum|my dad|my home)\b'],
        'valence': 'hard',
        'ref': 'missing home',
        'openers': ["Aw, homesickness is so real. What do you miss the most?", "That's such a heavy feeling. How long have you been away?"],
        'details': [
            (r'\bfood\b|\bcooking\b', ["Home food hits different, honestly. Nothing compares."]),
            (r'\bmom\b|\bmum\b|\bdad\b|\bparents\b|\bfamily\b', ["Have you been able to call them recently? Even a quick call can help."]),
        ],
        'followups': ["When do you get to go home next?", "Have you made any friends where you are?", "What's one comfort thing you could do today?"],
        'tips': "A regular call home, a little piece of home in your room, and building a small routine where you are can make it feel less raw over time.",
    },
    {
        'id': 'money',
        'patterns': [r'\bmoney\b', r'\bbroke\b(?! up)', r'\brent\b', r'\bfees\b', r'\bbudget\b', r'\bcant afford\b', r'\bsalary\b'],
        'valence': 'hard',
        'ref': 'money stress',
        'openers': ["Money stress is so heavy because it touches everything. What's going on?", "Ugh, that's a stressful one. Is it a short-term crunch or an ongoing thing?"],
        'details': [
            (r'\bparents\b|\bfamily\b', ["It's hard when it involves family too."]),
            (r'\bspent\b|\bshopping\b|\bimpulse\b', ["Happens to everyone. A quick look at where it went can help it feel less scary."]),
        ],
        'followups': ["Is it something urgent this month?", "Is there anyone who could help you plan it out?"],
        'tips': "Writing down where money goes for one week can turn a vague worry into something you can plan around. If it's urgent, your college may have hardship support worth asking about.",
    },
    {
        'id': 'sleep',
        'patterns': [r'\b(cant|couldnt|didnt) sleep\b', r'\binsomnia\b', r'\bup all night\b', r'\bno sleep\b', r'\bslept (badly|late|only)\b', r'\bstayed up\b'],
        'valence': 'hard',
        'ref': 'not sleeping',
        'openers': ["Oh no, bad sleep makes everything harder. Was your mind racing, or just couldn't switch off?", "Ugh, running on no sleep is rough. How are you feeling now?"],
        'details': [
            (r'\bthinking\b|\boverthink\w*\b|\bmind\b|\bworr\w*\b', ["That racing-brain thing at night is the worst. Writing the thoughts down before bed can help 'park' them."]),
            (r'\bphone\b|\breels\b|\bscroll\w*\b', ["The 'one more reel' trap is so real 😅"]),
            (r'\bstud\w*\b|\bassignment\b|\bexam\b', ["Staying up to study is sometimes unavoidable, but sleep really helps memory too."]),
        ],
        'followups': ["Has it been like this for a few nights?", "Can you nap or rest today?", "What was keeping you up?"],
        'tips': "Same wake-up time every day, screens down a bit before bed, and jotting down what's on your mind so it's parked for tomorrow. If it goes on for weeks, a doctor can help.",
    },
    {
        'id': 'movie_show',
        'patterns': [r'\b(?:watched|watching|saw|binged|binging|finished) (?:the )?(?P<thing>[a-z0-9 ]{2,40}?)(?: movie| film| series| show| season| episode)?$',
                     r'\b(movie|film|series|episode|anime|kdrama|k drama|netflix|cinema|theatre|theater)\b'],
        'valence': 'good',
        'ref': 'what you watched',
        'openers': ["Ooh, {thing}! How was it?", "Ahh nice, how did you like it?", "Ooh, I love hearing about this stuff. Was it good?"],
        'details': [
            (r'\bso+ good\b|\bamazing\b|\bloved\b|\bbest\b|\bawesome\b|\bfire\b|\bobsessed\b', ["Okay now I'm curious! What was the best part?", "Love that! Would you watch it again?"]),
            (r'\bbad\b|\bboring\b|\bdisappoint\w*\b|\bmid\b|\bslow\b', ["Aw, that's a letdown, especially if you were looking forward to it."]),
            (r'\bcried\b|\bsad\b|\bending\b', ["Oh no, one of those endings! Those stay with you."]),
            (r'\bfriends\b|\bfamily\b|\bwith\b', ["Watching with people makes it so much better."]),
        ],
        'followups': ["Who was your favourite character?", "Would you recommend it?", "What are you watching next?"],
        'tips': None,
    },
    {
        'id': 'music',
        'patterns': [r'\bsongs?\b', r'\balbum\b', r'\bconcert\b', r'\bplaylist\b', r'\blistening to\b', r'\bmusic\b'],
        'valence': 'good',
        'ref': 'the music',
        'openers': ["Ooh, what are you listening to?", "Music talk, yes! What's the song?"],
        'details': [
            (r'\bconcert\b|\blive\b', ["A concert! That energy is unmatched. Who was it?"]),
            (r'\brepeat\b|\bloop\b|\bobsessed\b', ["The on-repeat phase is the best. What's the line you love most?"]),
            (r'\bsad\b|\bcry\w*\b', ["Sometimes a sad song is exactly what you need."]),
        ],
        'followups': ["What genre are you into lately?", "Who's your favourite artist right now?"],
        'tips': None,
    },
    {
        'id': 'gaming',
        'patterns': [r'\bgaming\b', r'\bvideo games?\b', r'\b(playing|played) (valorant|minecraft|bgmi|pubg|fortnite|gta|fifa|cod|roblox|genshin|among us|chess)\b', r'\b(valorant|minecraft|bgmi|fortnite|roblox|genshin)\b'],
        'valence': 'good',
        'ref': 'the game',
        'openers': ["Ooh, a gamer! What are you playing?", "Nice! Are you winning at least? 😄"],
        'details': [
            (r'\bwon\b|\bwin\b|\bclutch\w*\b|\bvictory\b|\brank(ed)? up\b', ["Let's gooo! That feeling is unbeatable."]),
            (r'\blost\b|\blosing\b|\brage\w*\b|\bteammates?\b', ["Ugh, losing streaks (and teammates) can be so frustrating 😭"]),
        ],
        'followups': ["Do you play with friends?", "How long have you been playing it?"],
        'tips': None,
    },
    {
        'id': 'food',
        'patterns': [r'\bjunk food\b', r'\b(ate|eating|cooked|cooking|baked|baking|ordered)\b', r'\bcraving\w*\b', r'\bhungry\b', r'\b(biryani|pizza|maggi|burger|pasta|momos|chocolate|ice cream|cake|dosa)\b'],
        'valence': 'neutral',
        'ref': 'food',
        'openers': ["Ooh, food talk 😄 What did you have?", "Okay, now I'm curious. What are we eating?"],
        'details': [
            (r'\bjunk\b|\bcant stop\b|\btoo much\b|\bbinge\w*\b|\bstress eat\w*\b', [
                "Honestly, that happens to a lot of people, especially when life is stressful or busy. No judgement here.",
                "Being kind to yourself about it matters more than being 'perfect'. Have things been stressful lately?",
            ]),
            (r'\bcooked\b|\bbaked\b|\bmade\b', ["You cooked?! Okay, chef. How did it turn out?"]),
            (r'\bdelicious\b|\bso good\b|\byum\w*\b|\bamazing\b', ["Ahh, nothing beats a really good meal. 😋"]),
            (r'\bdidnt eat\b|\bskipped\b|\bnot hungry\b', ["Try to eat something small, even if you're not very hungry. Your body needs the fuel."]),
        ],
        'followups': ["What's your ultimate comfort food?", "Do you cook much yourself?"],
        'tips': "If it's stress-eating, it can help to notice what's going on right before the craving. Keeping some easy, filling snacks around and eating regular meals helps too. No need to be strict with yourself.",
    },
    {
        'id': 'exercise',
        'patterns': [r'\bgym\b', r'\bworkout\b', r'\bworked out\b', r'\bexercis\w*\b', r'\byoga\b', r'\b(went for a|morning|evening) (run|walk|jog)\b', r'\bjogging\b'],
        'valence': 'good',
        'ref': 'your workout',
        'openers': ["Ooh, nice! How did it feel?", "Love that! What kind of workout?"],
        'details': [
            (r'\bsore\b|\bpain\b|\bcant move\b', ["The day-after soreness is real 😅 Stretch and drink water!"]),
            (r'\bskipped\b|\blazy\b|\bdidnt go\b', ["Rest days count too. One skipped day doesn't undo anything."]),
            (r'\bgreat\b|\bamazing\b|\benergy\b|\bgood\b', ["That post-workout feeling is the best."]),
        ],
        'followups': ["How often do you go?", "Do you work out alone or with someone?"],
        'tips': "Consistency beats intensity. Short, regular sessions you enjoy will do more than occasional exhausting ones.",
    },
    {
        'id': 'weather',
        'patterns': [r'\braining\b', r'\brain\b', r'\b(so|very|too) (hot|cold|humid)\b', r'\bweather\b', r'\bsnow\w*\b', r'\bheat ?wave\b', r'\bstorm\b'],
        'valence': 'neutral',
        'ref': 'the weather',
        'openers': ["Ooh, how's the weather treating you?", "Weather check! Do you love it or hate it?"],
        'details': [
            (r'\brain\w*\b', ["Rain is the perfect excuse for chai and a cosy blanket ☔"]),
            (r'\bhot\b|\bheat\b|\bhumid\b', ["Ugh, the heat makes everything harder. Stay hydrated!"]),
            (r'\bcold\b|\bsnow\b', ["Cosy hoodie weather! Stay warm."]),
        ],
        'followups': ["Are you a rainy-day person or a sunny-day person?"],
        'tips': None,
    },
    {
        'id': 'pet',
        'patterns': [r'\bmy (dog|cat|puppy|kitten|pet|bunny|rabbit|parrot|hamster)\b'],
        'valence': 'good',
        'ref': 'your pet',
        'openers': ["Aww, tell me about them! What's their name?", "A pet! 🥹 What are they like?"],
        'details': [
            (r'\bsick\b|\bvet\b|\bhurt\b|\bdied\b|\bpassed\b|\blost\b', ["Oh no, I'm so sorry. Pets are family. How are you holding up?"]),
            (r'\bcute\b|\bfunny\b|\bdid\b|\bplay\w*\b', ["Okay, that's adorable. Pets are the best."]),
        ],
        'followups': ["How long have you had them?", "What's the funniest thing they do?"],
        'tips': None,
    },
    {
        'id': 'birthday',
        'patterns': [r'\bbirthday\b', r'\bbday\b'],
        'valence': 'good',
        'ref': 'the birthday',
        'openers': ["Ooh, a birthday! Is it yours? 🎂", "Birthday vibes! Whose is it?"],
        'details': [
            (r'\bmy\b|\btoday\b', ["Happy birthday!! 🎉 I hope today is lovely. Doing anything fun?"]),
            (r'\bforgot\b|\bno one\b|\bnobody\b|\balone\b', ["Aw, that really stings on a day that should feel special. I'm glad you told me. Happy birthday from me 💜"]),
            (r'\bgift\b|\bpresent\b|\bparty\b|\bcake\b', ["Ooh, fun! What's the plan?"]),
        ],
        'followups': ["Any plans to celebrate?", "What's the best birthday you've had?"],
        'tips': None,
    },
    {
        'id': 'trip',
        'patterns': [r'\btrip\b', r'\btravel\w*\b', r'\bvacation\b', r'\bholiday\b', r'\bgoing to (goa|manali|kerala|mumbai|delhi|bangalore|the beach|the mountains)\b'],
        'valence': 'good',
        'ref': 'the trip',
        'openers': ["Ooh, a trip! Where to?", "Travel plans! Tell me everything."],
        'details': [
            (r'\bbeach\b|\bmountains?\b|\bhills?\b', ["That sounds so peaceful. Are you more of a beach or mountains person?"]),
            (r'\bfriends\b|\bfamily\b', ["Trips with your people are the best kind."]),
            (r'\bcancel\w*\b|\bdidnt go\b', ["Aw, that's such a letdown when you were looking forward to it."]),
        ],
        'followups': ["When are you going?", "What are you most excited about?"],
        'tips': None,
    },
    {
        'id': 'social_media',
        'patterns': [r'\binstagram\b', r'\binsta\b', r'\bsocial media\b', r'\breels\b', r'\bdoom ?scroll\w*\b', r'\bscrolling\b', r'\bphone all day\b'],
        'valence': 'mixed',
        'ref': 'social media',
        'openers': ["Ah, the scroll. Is it more fun right now, or kind of draining?", "Social media can be such a mixed bag. What's going on?"],
        'details': [
            (r'\bcompar\w*\b|\beveryone else\b|\bperfect\b', ["Comparing yourself to highlight reels is so easy to fall into. Their posts aren't their whole life."]),
            (r'\bhours\b|\btoo much\b|\baddict\w*\b|\bcant stop\b', ["It's literally designed to be hard to put down, so don't be too hard on yourself."]),
        ],
        'followups': ["Does it leave you feeling better or worse after?"],
        'tips': "Some people find it helps to move the apps off the home screen, set a gentle time limit, or unfollow accounts that make them feel bad.",
    },
    {
        'id': 'future',
        'patterns': [r'\bmy future\b', r'\bcareer\b', r'\bwhat to do with my life\b', r'\bafter (college|graduation|school)\b', r'\bwhich (course|branch|field)\b'],
        'valence': 'mixed',
        'ref': 'thinking about the future',
        'openers': ["Future stuff can feel so big. What's on your mind about it?", "Ah, the 'what am I doing with my life' thoughts. Totally normal. What's got you thinking about it?"],
        'details': [
            (r'\bconfused\b|\bdont know\b|\bno idea\b|\blost\b', ["Not knowing yet is honestly so normal. Most people figure it out step by step, not all at once."]),
            (r'\bparents\b|\bfamily\b|\bpressure\b', ["Family expectations can make it so much heavier."]),
            (r'\bbehind\b|\beveryone else\b', ["Everyone moves at their own pace. You're not behind, you're on your own timeline."]),
        ],
        'followups': ["What kinds of things do you enjoy doing?", "Is there something you're curious to try?"],
        'tips': "Instead of deciding your whole life, try picking one small next step: a short course, talking to someone in a field you're curious about, or an internship. Clarity usually comes from trying things.",
    },
    {
        'id': 'appearance',
        'patterns': [r'\b(i look|i feel|feeling) (ugly|fat|gross|bad about (my|how))\b', r'\bbody image\b', r'\bacne\b', r'\bpimples?\b', r'\bbad hair day\b', r'\bhate (my|how i) (body|face|look)\w*\b'],
        'valence': 'hard',
        'ref': 'how you feel about your looks',
        'openers': ["Aw, those days when you don't feel good in your own skin are hard. What's making you feel that way?", "I'm sorry you're feeling like that. Is it something specific today?"],
        'details': [
            (r'\bcompar\w*\b|\binstagram\b|\beveryone\b', ["Comparing yourself to filtered photos is so unfair to yourself. Real people have texture, bumps and bad hair days."]),
            (r'\bsaid\b|\bcomment\w*\b|\bteas\w*\b', ["Comments about how someone looks are never okay. I'm sorry that happened."]),
        ],
        'followups': ["What's one thing you actually like about yourself?", "Is there someone who makes you feel good about yourself?"],
        'tips': "Be as kind to yourself as you'd be to a friend saying the same thing. Wearing something comfortable that you like, and taking a break from comparison-heavy apps, can help on rough days.",
    },
]

TOPIC_BY_ID = {t['id']: t for t in TOPICS}

# Generic, topic-aware lines when a message continues a topic but nothing more
# specific matched. {ref} is the topic's ref phrase.
CONTINUE_HARD = [
    "That's a lot to deal with on top of {ref}.",
    "Yeah, that makes it even harder.",
    "Mm, I hear you. That sounds really tough.",
    "Ugh, that's rough. You're handling a lot right now.",
    "That makes total sense.",
]
CONTINUE_GOOD = [
    "Ahh, I love that!",
    "Okay, that's honestly great.",
    "Haha, love it.",
    "That sounds so fun.",
]
CONTINUE_NEUTRAL = [
    "Oh nice.",
    "Ooh, okay!",
    "Got it.",
    "Mm, makes sense.",
]
