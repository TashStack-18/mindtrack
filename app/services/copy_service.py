import hashlib
from datetime import datetime, timezone

def get_time_of_day(hour):
    if 5 <= hour < 12: return "morning"
    if 12 <= hour < 17: return "afternoon"
    if 17 <= hour < 21: return "evening"
    return "night"

class CopyService:
    def __init__(self, user_id=None, name=None, local_hour=None, local_date_str=None, entry_count=0, latest_mood=None, gap_days=0, theme=None):
        self.user_id = str(user_id) if user_id else "guest"
        self.name = name.split()[0].title() if name else ""
        self.local_hour = local_hour if local_hour is not None else datetime.now(timezone.utc).hour
        self.tod = get_time_of_day(self.local_hour)
        self.date_str = local_date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        self.is_new = entry_count < 5
        self.latest_mood = latest_mood
        self.gap_days = gap_days
        self.theme = theme
        self.name_used = False

    def _hash_choice(self, pool, slot, offset=0):
        if not pool: return ""
        base_str = f"{self.user_id}_{self.date_str}_{slot}_{offset}"
        h = int(hashlib.md5(base_str.encode('utf-8')).hexdigest(), 16)
        return pool[h % len(pool)]

    def _get_pool(self, slot):
        if slot == "greeting":
            if self.gap_days >= 3:
                return ["Good to see you again{name_comma}. Start wherever feels easy.", "Welcome back{name_comma}. Take your time settling in.", "It is good to see you{name_comma}. There is no rush.", "Hello again{name_comma}. Begin whenever you are ready."]
            if self.tod == "morning":
                return ["Good morning{name_comma}. Take a gentle breath.", "A new morning{name_comma}. Start at your own pace.", "Good morning{name_comma}. A quiet moment for yourself.", "Morning{name_comma}. Take time to gather your thoughts."]
            if self.tod == "afternoon":
                return ["Good afternoon{name_comma}. Pause for a moment.", "Afternoon{name_comma}. A small break in your day.", "Good afternoon{name_comma}. Take a breath right here.", "Hello{name_comma}. Time for a quiet check-in."]
            if self.tod == "evening":
                return ["Good evening{name_comma}. The day is winding down.", "Evening{name_comma}. A moment to reflect.", "Good evening{name_comma}. Let the day settle.", "Hello{name_comma}. Take a calm breath this evening."]
            return ["Good night{name_comma}. The world is quiet.", "Late hours{name_comma}. A gentle moment before rest.", "Nighttime{name_comma}. Let your mind settle.", "Good night{name_comma}. A quiet space for your thoughts."]

        if slot == "subline":
            if self.latest_mood in [1, 2]:
                return ["Take it one small step at a time.", "Be gentle with yourself right now.", "It is okay to rest and just be.", "Give yourself permission to pause.", "You do not have to carry everything at once."]
            if self.latest_mood in [4, 5]:
                return ["I hope you can hold on to this feeling.", "Take a moment to enjoy this space.", "It is nice to have lighter days.", "Savour the quiet moments of clarity."]
            return ["Check in with how you are feeling right now.", "Take a moment to reflect on your day.", "A quiet place to gather your thoughts.", "Notice what is present for you today."]

        if slot == "checkin_prompt":
            return ["How are you feeling right now?", "What is on your mind today?", "Take a breath. How is today going?", "Check in with yourself.", "What is present for you right now?"]

        if slot == "day_card_caption":
            return ["Today's check-in", "How is today?", "A moment for today", "Your daily pause"]

        if slot == "quick_reflection":
            return ["Write a quick thought...", "Jot down what is on your mind...", "A space for your thoughts...", "Capture a moment from today..."]

        if slot == "reflect_card_intro":
            return ["A moment to pause on {theme}.", "Reflecting on {theme}.", "Thoughts on {theme}.", "Looking closer at {theme}."]

        if slot == "history_recap":
            return ["Your recent moments.", "Looking back at your days.", "Your gathered thoughts.", "A quiet record of your days."]

        if slot == "writing_placeholder":
            return ["Start writing here...", "What is on your mind?", "Let your thoughts flow naturally...", "Take your time writing..."]

        if slot == "post_save_note":
            return ["Your thoughts are safely stored.", "Thank you for checking in.", "Moment captured.", "Your entry has been saved quietly."]

        if slot == "empty_state_recent":
            return ["No recent moments found.", "Your recent check-ins will appear here.", "This space is waiting for your thoughts.", "Start a new check-in when you are ready."]

        if slot == "empty_state_chart":
            return ["Not enough data yet.", "Your journey will take shape here.", "Check in more to see your pattern.", "Your chart will appear after a few entries."]

        if slot == "empty_state_search":
            return ["No moments matched that search.", "Try looking for something else.", "We couldn't find anything matching.", "Nothing found for that search."]

        if slot == "affirmation":
            if self.latest_mood in [1, 2]:
                return ["It is okay if today is hard.", "Rest is a valid choice.", "You are allowed to feel this way.", "Small steps are enough."]
            return ["You are doing fine.", "Take things as they come.", "Every moment is a new start.", "Trust your own pace."]

        if slot == "line_for_today":
            if self.tod == "morning":
                return ["Start softly.", "Breathe in the new day.", "Take it gently.", "A fresh page."]
            if self.tod == "night":
                return ["Let it go for now.", "Time for rest.", "The day is done.", "Close your eyes."]
            return ["Find a small joy.", "Pause and breathe.", "You are right here.", "Take your time."]

        if slot == "week_caption":
            return ["Your week at a glance", "This week's moments", "Looking at your week", "Moments from the last seven days"]

        if slot == "sprig_line":
            return ["A quiet place to check in with yourself.", "Take a gentle breath.", "Small moments matter.", "Your space to just be."]

        if slot == "mindy_note_fallback":
            return ["Your patterns will appear here as you write.", "Keep checking in to discover patterns.", "I am learning how you feel over time.", "More insights will appear soon."]

        return ["Just a quiet moment.", "Take a gentle breath."]

    def get(self, slot, **kwargs):
        pool = self._get_pool(slot)
        
        y_date = (datetime.strptime(self.date_str, "%Y-%m-%d").timestamp() - 86400)
        y_date_str = datetime.fromtimestamp(y_date).strftime("%Y-%m-%d")
        
        y_base = f"{self.user_id}_{y_date_str}_{slot}_0"
        y_h = int(hashlib.md5(y_base.encode('utf-8')).hexdigest(), 16)
        y_choice = pool[y_h % len(pool)] if pool else ""
        
        choice = self._hash_choice(pool, slot, offset=0)
        if choice == y_choice and len(pool) > 1:
            choice = self._hash_choice(pool, slot, offset=1)
            
        name_comma = f", {self.name}" if self.name and not self.name_used else ""
        if name_comma:
            self.name_used = True
            
        return choice.format(name_comma=name_comma, name=self.name, theme=self.theme or "things")
