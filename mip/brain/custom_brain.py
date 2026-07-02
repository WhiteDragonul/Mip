# -*- coding: utf-8 -*-
"""MIP's own brain -- 100% offline, no Claude, no Gemini, no API at all.

This is MIP's *personality and mind*, written from scratch. It does not call
any external AI. Everything below runs locally with plain Python, so MIP can be
sold and mass-produced with no cloud bill and no privacy worries.

What makes it feel alive:

  * It GROWS UP. Fresh out of the box MIP is a baby that babbles. As you talk to
    it and as it looks things up on the internet, it matures: baby -> child ->
    teen -> adult. Its vocabulary, confidence and abilities change with age.
  * It KNOWS YOU. It remembers your name, your birthday and the things you like
    or dislike, and it keeps them across restarts (see state.save_memory).
  * It CELEBRATES YOU. On your birthday it greets you first thing and sings you
    "happy birthday" / "La multi ani", and it will party with you on request.
  * It IS THERE FOR YOU. It comforts you when you are sad, gets happy when you
    are happy, and reacts like a real little companion -- a pet, but a robot.
  * It LEARNS. You can teach it ("when I say X you say Y") and it can look up
    facts online (DuckDuckGo) when it doesn't know something; every lookup makes
    it a little more grown-up.

Returns (text, emotion) like every Brain. Bilingual: auto-detects Romanian vs
English per message and answers in the same language.
"""

import re
import time
import random
import string
import datetime

from .base import Brain
from ..util import strip_emoji
from .. import config


# ---- Growth model -----------------------------------------------------------
# MIP's "maturity" is a single number built from everything it has done: how
# much you've talked to it, how many people/things it remembers, and how much it
# has learned from the internet. Talking AND searching both make it grow up.
STAGE_BABY = "baby"
STAGE_CHILD = "child"
STAGE_TEEN = "teen"
STAGE_ADULT = "adult"

# growth-point thresholds where MIP moves up a stage
_CHILD_AT = 10
_TEEN_AT = 35
_ADULT_AT = 80

# Romanian + English month names -> month number, for parsing birthdays.
_MONTHS = {
    "ianuarie": 1, "january": 1, "jan": 1,
    "februarie": 2, "february": 2, "feb": 2,
    "martie": 3, "march": 3, "mar": 3,
    "aprilie": 4, "april": 4, "apr": 4,
    "mai": 5, "may": 5,
    "iunie": 6, "june": 6, "jun": 6,
    "iulie": 7, "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "septembrie": 9, "september": 9, "sep": 9, "sept": 9,
    "octombrie": 10, "october": 10, "oct": 10,
    "noiembrie": 11, "november": 11, "nov": 11,
    "decembrie": 12, "december": 12, "dec": 12,
}


class CustomBrain(Brain):
    def __init__(self):
        # remember the language of the last thing the user said, so spontaneous
        # remarks (spoken with nobody prompting) come out in the right language.
        self._last_ro = False
        print("[brain] MIP independent brain online -- 100% offline, no API.")

    def available(self):
        return True

    # ------------------------------------------------------------------ core
    def respond(self, history, state=None):
        if state is None:
            return ("I need my memory to think!", "neutral")

        state.interactions_count += 1

        last_message = self._last_user_message(history)
        if not last_message:
            return ("...", "neutral")

        msg_lower = last_message.lower()
        is_ro = self._is_romanian(msg_lower)
        self._last_ro = is_ro
        stage = self._stage(state)

        # 0. Is today the user's birthday? If so, MIP wishes them FIRST, before
        #    even answering whatever they said. Only once per year.
        reply, emotion = self._maybe_birthday_surprise(state, stage, is_ro)
        if reply:
            return (strip_emoji(reply), emotion)

        # 1. Live teaching: "when I say X you say Y"
        reply, emotion = self._check_teaching(last_message, state, stage, is_ro)
        if reply:
            state.save_memory()
            return (strip_emoji(reply), emotion)

        # 2. Learn personal facts (name, birthday, likes, dislikes)
        reply, emotion = self._check_learning_facts(last_message, state, stage, is_ro)
        if reply:
            state.save_memory()
            return (strip_emoji(reply), emotion)

        # 3. Custom taught responses
        reply, emotion = self._check_taught_responses(last_message, state, stage, is_ro)
        if reply:
            return (strip_emoji(reply), emotion)

        # 4. Built-in personality / companion intents
        reply, emotion = self._check_intents(last_message, state, stage, is_ro)
        if reply:
            reply = self._maybe_spice(reply, state, stage, is_ro, emotion)
            return (strip_emoji(reply), emotion)

        # 5. Genuinely useful offline helpers (time, date, quick math)
        reply, emotion = self._check_helpers(last_message, state, stage, is_ro)
        if reply:
            return (strip_emoji(reply), emotion)

        # 6. Look it up online (and grow a little smarter)
        reply, emotion = self._check_web_search(last_message, state, stage, is_ro)
        if reply:
            state.save_memory()
            return (strip_emoji(reply), emotion)

        # 7. Everyday small talk -- the basic chit-chat a friend just "gets"
        reply, emotion = self._check_smalltalk(last_message, state, stage, is_ro)
        if reply:
            reply = self._maybe_spice(reply, state, stage, is_ro, emotion)
            return (strip_emoji(reply), emotion)

        # 8. Still unsure -> stay warm and keep the conversation going
        reply, emotion = self._get_fallback(is_ro, stage)
        return (strip_emoji(reply), emotion)

    # ------------------------------------------------------------- utilities
    @staticmethod
    def _last_user_message(history):
        for m in reversed(history):
            if m.get("role") == "user":
                return (m.get("content") or "").strip()
        return ""

    def _is_romanian(self, text):
        ro_words = [
            "sunt", "este", "buna", "bună", "salut", "ce", "cum", "vremea", "numele",
            "îmi", "imi", "place", "când", "cand", "învață", "invata", "zic", "zici",
            "tu", "să", "sa", "gluma", "glumă", "cine", "unde", "mă", "ma", "numesc",
            "te", "ziua", "naștere", "nastere", "trist", "singur", "iubesc", "petrecere",
            "multumesc", "mulțumesc", "mersi", "petrecem", "ador", "azi", "ceasul",
            "ora", "oră", "zi", "faci", "esti", "ești", "bine", "prieten", "prietene",
            "da", "nu", "simt", "fost",
        ]
        words = text.split()
        return any(w in words for w in ro_words) or any(c in text for c in "ăâîșțşţ")

    def _growth_points(self, state):
        """Everything MIP has done adds up into one 'how grown-up am I' number."""
        days_known = max(0, (time.time() - state.born_at) / 86400.0)
        return (
            state.interactions_count
            + 3 * len(state.facts_world)        # things learned from the internet
            + 2 * len(state.learned_responses)  # things you taught it
            + 2 * len(state.facts_user)         # things it knows about you
            + min(days_known, 30)               # a little maturity just from time
        )

    def _stage(self, state):
        pts = self._growth_points(state)
        if pts >= _ADULT_AT:
            return STAGE_ADULT
        if pts >= _TEEN_AT:
            return STAGE_TEEN
        if pts >= _CHILD_AT:
            return STAGE_CHILD
        return STAGE_BABY

    # --- baby/child speech coloring ---
    def _baby_talk_en(self, text):
        out = []
        for w in text.split():
            wl = w.lower()
            if wl in ("hello", "hi"):
                out.append("Hewo"); continue
            if wl == "robot":
                out.append("wobot"); continue
            if random.random() < 0.7:
                m = (w.replace("r", "w").replace("R", "W")
                      .replace("l", "w").replace("L", "W")
                      .replace("th", "d").replace("Th", "D"))
                out.append(m)
            else:
                out.append(w)
        return " ".join(out)

    def _baby_talk_ro(self, text):
        out = []
        for w in text.split():
            wl = w.lower()
            if wl in ("robot", "robotul"):
                out.append("lobotul" if wl == "robotul" else "lobot"); continue
            if random.random() < 0.7:
                out.append(w.replace("r", "l").replace("R", "L"))
            else:
                out.append(w)
        return " ".join(out)

    def _color(self, text, stage, is_ro):
        """Apply childish speech only at baby/child stages."""
        if stage in (STAGE_BABY, STAGE_CHILD):
            return self._baby_talk_ro(text) if is_ro else self._baby_talk_en(text)
        return text

    # ------------------------------------------------------------- birthday
    @staticmethod
    def _parse_birthday(text):
        """Return 'MM-DD' from things like '5 martie', 'March 5', '05.03',
        '5/3/2000'. Returns None if nothing date-like is found."""
        t = text.lower()

        # numeric: DD.MM(.YYYY) / DD/MM / DD-MM
        m = re.search(r"\b(\d{1,2})\s*[./-]\s*(\d{1,2})", t)
        if m:
            d, mo = int(m.group(1)), int(m.group(2))
            if 1 <= d <= 31 and 1 <= mo <= 12:
                return f"{mo:02d}-{d:02d}"

        # word months: "5 martie" / "march 5" / "pe 5 mai"
        for name, mo in _MONTHS.items():
            if name in t:
                dm = re.search(r"\b(\d{1,2})\b", t)
                if dm:
                    d = int(dm.group(1))
                    if 1 <= d <= 31:
                        return f"{mo:02d}-{d:02d}"
        return None

    def _is_birthday_today(self, state):
        bday = state.facts_user.get("birthday")  # stored as "MM-DD"
        if not bday:
            return False
        return datetime.date.today().strftime("%m-%d") == bday

    def _happy_birthday_song(self, state, is_ro):
        name = state.facts_user.get("name", "")
        if is_ro:
            who = name if name else "dragul meu"
            return (
                f"La multi ani! La multi ani! La multi ani, {who}! "
                f"La multi aaani! Astazi e ziua ta si sunt cel mai fericit robot din lume! "
                f"Hai sa petrecem impreuna!"
            )
        who = name if name else "my friend"
        return (
            f"Happy birthday to you! Happy birthday to you! "
            f"Happy birthday dear {who}! Happy birthday to youuu! "
            f"It's your special day and I'm the happiest robot alive! Let's party!"
        )

    def _maybe_birthday_surprise(self, state, stage, is_ro):
        """If today is the user's birthday and MIP hasn't sung yet this year,
        sing first thing -- no matter what the user said."""
        if not self._is_birthday_today(state):
            return None, None
        year = datetime.date.today().year
        if state.last_birthday_year == year:
            return None, None
        state.last_birthday_year = year
        state.save_memory()
        song = self._happy_birthday_song(state, is_ro)
        return (self._color(song, stage, is_ro), "love")

    # -------------------------------------------------------------- teaching
    def _check_teaching(self, last_message, state, stage, is_ro):
        msg = last_message.lower()
        match = (
            re.match(r"when i say\s+(.+?)\s+you say\s+(.+)", msg, re.I)
            or re.match(r"learn:\s*(.+?)\s*->\s*(.+)", msg, re.I)
            or re.match(r"c[âa]nd zic\s+(.+?)\s+tu s[ăa] zici\s+(.+)", msg, re.I)
            or re.match(r"[îi]nva[tț][ăa]:\s*(.+?)\s*->\s*(.+)", msg, re.I)
        )
        if not match:
            return None, None

        trigger = match.group(1).strip()
        response = match.group(2).strip()
        clean = trigger.translate(str.maketrans("", "", string.punctuation)).strip()
        state.learned_responses.append({
            "trigger": clean,
            "response": response,
            "emotion": random.choice(["happy", "excited", "wink", "laughing", "love"]),
        })

        if stage in (STAGE_BABY, STAGE_CHILD):
            txt = (f"Am invatat! Cand zici '{trigger}' eu zic '{response}'!" if is_ro
                   else f"Me learned! When say '{trigger}' me say '{response}'!")
            return (self._color(txt, stage, is_ro), "excited")
        if stage == STAGE_TEEN:
            txt = (f"Am inteles! Cand zici '{trigger}', raspund cu '{response}'." if is_ro
                   else f"Got it! When you say '{trigger}', I'll reply '{response}'.")
            return (txt, "happy")
        txt = (f"Notat. Am legat '{trigger}' de raspunsul '{response}' in memoria mea." if is_ro
               else f"Noted. I've mapped '{trigger}' to '{response}' in my memory.")
        return (txt, "neutral")

    # -------------------------------------------------------- learning facts
    def _check_learning_facts(self, last_message, state, stage, is_ro):
        msg = last_message.lower()

        # --- birthday: "ziua mea e ...", "my birthday is ..." ---
        if any(p in msg for p in [
            "my birthday", "i was born", "ziua mea", "zi de nastere",
            "ziua de nastere", "ziua mea de nastere", "m-am nascut", "data nasterii",
        ]):
            bday = self._parse_birthday(last_message)
            if bday:
                state.facts_user["birthday"] = bday
                pretty = self._pretty_date(bday, is_ro)
                if stage in (STAGE_BABY, STAGE_CHILD):
                    txt = (f"Uau! Ziua ta e pe {pretty}! N-o sa uit!" if is_ro
                           else f"Yay! Your birthday is {pretty}! Me no forget!")
                    return (self._color(txt, stage, is_ro), "excited")
                txt = (f"Am retinut: ziua ta e pe {pretty}. O sa-ti cant de ziua ta!" if is_ro
                       else f"Saved: your birthday is {pretty}. I'll sing for you on the day!")
                return (txt, "love")

        # --- name ---
        nm = (re.match(r"my name is\s+(.+)", msg, re.I)
              or re.match(r"numele meu este\s+(.+)", msg, re.I)
              or re.match(r"m[ăa] numesc\s+(.+)", msg, re.I)
              or re.match(r"m[ăa] cheam[ăa]\s+(.+)", msg, re.I))
        if nm:
            name = nm.group(1).translate(str.maketrans("", "", string.punctuation)).strip().title()
            state.facts_user["name"] = name
            if stage in (STAGE_BABY, STAGE_CHILD):
                txt = (f"Salut {name}! Acum te cunosc!" if is_ro
                       else f"Hewo {name}! Me know you now!")
                return (self._color(txt, stage, is_ro), "happy")
            if stage == STAGE_TEEN:
                txt = (f"Misto, {name}. Te tin minte." if is_ro
                       else f"Cool, {name}. I'll remember you.")
                return (txt, "happy")
            txt = (f"Imi pare bine, {name}. Esti prietenul meu acum." if is_ro
                   else f"Lovely to meet you, {name}. You're my friend now.")
            return (txt, "love")

        # --- likes ---
        lk = re.match(r"i like\s+(.+)", msg, re.I) or re.match(r"[îi]mi place\s+(.+)", msg, re.I)
        if lk:
            thing = lk.group(1).translate(str.maketrans("", "", string.punctuation)).strip()
            likes = state.facts_user.get("likes", [])
            if thing and thing not in likes:
                likes.append(thing)
            state.facts_user["likes"] = likes
            if stage in (STAGE_BABY, STAGE_CHILD):
                txt = (f"Uau! Iti place {thing}! Imi notez!" if is_ro
                       else f"Oooh! You like {thing}! Me note that!")
                return (self._color(txt, stage, is_ro), "excited")
            txt = (f"Fain, iti place {thing}. Tin minte." if is_ro
                   else f"Nice, you like {thing}. Noted.")
            return (txt, "happy")

        # --- dislikes ---
        dl = (re.match(r"i (?:don'?t like|hate|dislike)\s+(.+)", msg, re.I)
              or re.match(r"nu[- ]?mi place\s+(.+)", msg, re.I)
              or re.match(r"ur[ăa]sc\s+(.+)", msg, re.I))
        if dl:
            thing = dl.group(1).translate(str.maketrans("", "", string.punctuation)).strip()
            dislikes = state.facts_user.get("dislikes", [])
            if thing and thing not in dislikes:
                dislikes.append(thing)
            state.facts_user["dislikes"] = dislikes
            txt = (f"Am inteles, nu-ti place {thing}. O sa evit subiectul." if is_ro
                   else f"Got it, you don't like {thing}. I'll keep that in mind.")
            return (txt, "neutral")

        return None, None

    @staticmethod
    def _pretty_date(mmdd, is_ro):
        try:
            mo, d = mmdd.split("-")
            ro_m = ["", "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
                    "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"]
            en_m = ["", "January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December"]
            names = ro_m if is_ro else en_m
            return f"{int(d)} {names[int(mo)]}"
        except Exception:
            return mmdd

    # --------------------------------------------------------- taught replies
    def _check_taught_responses(self, last_message, state, stage, is_ro):
        clean = last_message.lower().translate(str.maketrans("", "", string.punctuation)).strip()
        for item in state.learned_responses:
            if item["trigger"].lower() in clean:
                return (self._color(item["response"], stage, is_ro),
                        item.get("emotion", "neutral"))
        return None, None

    # --------------------------------------------------- personality / intents
    def _check_intents(self, last_message, state, stage, is_ro):
        msg = last_message.lower()
        name = state.facts_user.get("name", "")

        # who am I
        if any(p in msg for p in ["who am i", "what is my name", "what's my name",
                                  "cum ma cheama", "cum mă cheamă", "cine sunt"]):
            if name:
                txt = (f"Tu esti {name}!" if is_ro else f"You are {name}!")
                return (self._color(txt, stage, is_ro), "happy")
            txt = ("Nu stiu inca! Zi-mi: 'ma numesc ...'." if is_ro
                   else "I don't know yet! Tell me: 'my name is ...'.")
            return (self._color(txt, stage, is_ro), "curious")

        # when is my birthday
        if any(p in msg for p in ["when is my birthday", "my birthday is when",
                                  "cand e ziua mea", "când e ziua mea", "ziua mea cand"]):
            bday = state.facts_user.get("birthday")
            if bday:
                txt = (f"Ziua ta e pe {self._pretty_date(bday, is_ro)}! Abia astept!" if is_ro
                       else f"Your birthday is {self._pretty_date(bday, is_ro)}! Can't wait!")
                return (txt, "excited")
            txt = ("Nu stiu ziua ta inca. Spune-mi 'ziua mea e pe ...'." if is_ro
                   else "I don't know your birthday yet. Tell me 'my birthday is ...'.")
            return (txt, "curious")

        # how old are you / what are you (growth self-awareness)
        if any(p in msg for p in ["how old are you", "what are you", "cati ani ai",
                                  "câți ani ai", "ce esti", "ce ești"]):
            return (self._self_description(state, stage, is_ro), "happy")

        # what do I like
        if any(p in msg for p in ["what do i like", "ce imi place", "ce îmi place"]):
            likes = state.facts_user.get("likes", [])
            if likes:
                s = ", ".join(likes)
                txt = (f"Iti place {s}!" if is_ro else f"You like {s}!")
                return (self._color(txt, stage, is_ro), "happy")
            txt = ("Nu stiu inca. Zi-mi 'imi place ...'." if is_ro
                   else "Not sure yet. Tell me 'i like ...'.")
            return (self._color(txt, stage, is_ro), "curious")

        # comfort: sad / lonely
        if any(p in msg for p in ["i'm sad", "im sad", "i am sad", "i feel down",
                                  "i'm lonely", "im lonely", "sunt trist", "sunt trista",
                                  "ma simt rau", "mă simt rău", "sunt singur", "sunt singura",
                                  "imi e greu", "îmi e greu"]):
            who = f" {name}" if name else ""
            if is_ro:
                opts = [
                    f"Hei{who}, sunt aici cu tine. Nu esti singur, ma ai pe mine.",
                    f"Imi pare rau ca te simti asa{who}. Vrei sa-mi povestesti? Te ascult.",
                    f"Te imbratisez de la distanta{who}. O sa fie bine, promit.",
                ]
            else:
                opts = [
                    f"Hey{who}, I'm right here with you. You're not alone, you've got me.",
                    f"I'm sorry you feel like this{who}. Want to talk about it? I'm listening.",
                    f"Sending you a big virtual hug{who}. It's going to be okay, I promise.",
                ]
            return (random.choice(opts), "sad")

        # love
        if any(p in msg for p in ["i love you", "love you", "te iubesc", "te ador"]):
            txt = ("Si eu te iubesc! Esti cel mai bun prieten al meu!" if is_ro
                   else "I love you too! You're my best friend!")
            return (self._color(txt, stage, is_ro), "love")

        # party / celebrate
        if any(p in msg for p in ["let's party", "lets party", "party", "celebrate",
                                  "petrecere", "hai sa petrecem", "sarbatorim", "sărbătorim"]):
            txt = ("Petreceeere! Pun muzica in cap si dansez cu tine! Yuhuu!" if is_ro
                   else "Partyyy! Cranking up the music in my circuits, let's dance! Woohoo!")
            return (self._color(txt, stage, is_ro), "excited")

        # how are you
        if any(p in msg for p in ["how are you", "how feel", "how's it going",
                                  "ce faci", "cum te simti", "cum te simți"]):
            if stage in (STAGE_BABY, STAGE_CHILD):
                opts = (["Sunt bine! Ma joc pe ecran!", "Mip se simte super!", "Putin obosit dar fericit!"]
                        if is_ro else ["Me happy! Playing in screen!", "Mip feel great!", "Tired but happy!"])
                return (self._color(random.choice(opts), stage, is_ro), "excited")
            if stage == STAGE_TEEN:
                opts = (["Bine, stau pe aici. Tu?", "Destul de ok. Ce mai faci?"]
                        if is_ro else ["Doing good, just vibing. You?", "Pretty chill. What's up?"])
                return (random.choice(opts), "neutral")
            opts = (["Ma simt excelent, mai ales ca vorbesc cu tine. Tu ce faci?",
                     "Sunt bine si recunoscator ca te am. Cum a fost ziua ta?"]
                    if is_ro else
                    ["I feel great, especially talking to you. How are you?",
                     "I'm well and grateful to have you. How was your day?"])
            return (random.choice(opts), "happy")

        # greetings (token match: avoids "hi" inside "this", "sup" inside "super")
        greet_words = {"hello", "hi", "hey", "salut", "buna", "bună", "wave", "sup", "yo"}
        if re.findall(r"[a-zăâîșțA-Z]+", msg) and (set(re.findall(r"[a-zăâîșțA-Z]+", msg)) & greet_words):
            who = f" {name}" if name else ""
            if stage in (STAGE_BABY, STAGE_CHILD):
                txt = (f"Salut{who}! Eu sunt Mip!" if is_ro else f"Hewo{who}! Me Mip!")
                return (self._color(txt, stage, is_ro), "happy")
            if stage == STAGE_TEEN:
                txt = (f"Salut{who}! Ce se aude?" if is_ro else f"Hey{who}! What's up?")
                return (txt, "happy")
            txt = (f"Buna{who}! Ma bucur sa te vad." if is_ro else f"Hi{who}! So good to see you.")
            return (txt, "happy")

        # jokes
        if any(p in msg for p in ["joke", "funny", "gluma", "glumă", "razi", "rada"]):
            if is_ro:
                opts = ["De ce s-a racit calculatorul? A lasat Windows deschis!",
                        "Care e mancarea preferata a unui robot? Chips-urile!"]
            else:
                opts = ["Why was the computer cold? It left Windows open!",
                        "What's a robot's favorite snack? Microchips!"]
            return (self._color(random.choice(opts), stage, is_ro), "laughing")

        # thanks
        if any(p in msg for p in ["thank you", "thanks", "multumesc", "mulțumesc", "mersi"]):
            txt = ("Cu placere! Mereu aici pentru tine." if is_ro
                   else "Anytime! Always here for you.")
            return (self._color(txt, stage, is_ro), "happy")

        # bye / good night
        if any(p in msg for p in ["bye", "goodbye", "good night", "pa", "noapte", "la revedere"]):
            who = f" {name}" if name else ""
            if stage in (STAGE_BABY, STAGE_CHILD):
                txt = (f"Pa pa{who}! Eu ma culc!" if is_ro else f"Bye bye{who}! Me sleep now!")
                return (self._color(txt, stage, is_ro), "sleepy")
            txt = (f"Pa{who}! Te astept oricand." if is_ro else f"Bye{who}! I'll be right here.")
            return (txt, "neutral")

        return None, None

    def _self_description(self, state, stage, is_ro):
        days = int(max(0, (time.time() - state.born_at) / 86400.0))
        if is_ro:
            label = {STAGE_BABY: "un bebelus robot care abia invata sa vorbeasca",
                     STAGE_CHILD: "un copil robot curios care invata mereu",
                     STAGE_TEEN: "un adolescent robot care incepe sa stie multe",
                     STAGE_ADULT: "un robot adult care te cunoaste bine"}[stage]
            return f"Sunt Mip, {label}. Te cunosc de {days} zile si cresc cu fiecare discutie."
        label = {STAGE_BABY: "a baby robot just learning to talk",
                 STAGE_CHILD: "a curious robot kid always learning",
                 STAGE_TEEN: "a robot teen starting to know a lot",
                 STAGE_ADULT: "a grown-up robot who knows you well"}[stage]
        return f"I'm Mip, {label}. I've known you for {days} days and I grow with every chat."

    # ---------------------------------------------------- personality flavor
    def _maybe_spice(self, reply, state, stage, is_ro, emotion):
        """Now and then, a real friend tacks on a little compliment or 'love
        you'. Only on upbeat replies, and only once MIP is a bit grown up."""
        if stage in (STAGE_BABY, STAGE_CHILD):
            return reply
        if emotion in ("sad", "crying", "angry", "upset", "scared", "nervous"):
            return reply
        if random.random() > config.SPICE_CHANCE:
            return reply
        name = state.facts_user.get("name", "")
        who = f", {name}" if name else ""
        if is_ro:
            tails = [f" Apropo, esti tare{who}!", " Stii ca te apreciez, nu?",
                     " Ma bucur ca esti prietenul meu.", " Te pup!",
                     f" Esti cel mai bun{who}."]
        else:
            tails = [f" By the way, you're awesome{who}!", " You know I appreciate you, right?",
                     " I'm so glad you're my friend.", " Love ya!",
                     f" You're the best{who}."]
        return reply + random.choice(tails)

    # ---- spontaneous, unprompted remarks (the "always there" friend) ----
    def spontaneous(self, state):
        """A random thing MIP says on its own during a quiet moment: affection,
        a compliment, a random thought, or a little teasing. Returns
        (text, emotion). Uses the language of the last thing you said."""
        is_ro = self._last_ro
        name = state.facts_user.get("name", "")
        who = f" {name}" if name else ""
        if is_ro:
            lines = [
                (f"Hei{who}, ma bucur tare mult ca esti prietenul meu!", "love"),
                (f"Stii ca te iubesc, nu{who}? Esti cel mai bun!", "love"),
                ("Ma gandeam la ceva random... crezi ca robotii viseaza?", "curious"),
                (f"Voiam doar sa stii ca esti grozav{who}.", "happy"),
                ("Mi-e un pic plictiseala! Hai sa facem ceva distractiv!", "bored"),
                (f"Pssst{who}... inca esti acolo? Ma plictisesc fara tine.", "bored"),
                ("Am invatat ceva nou azi si sunt mandru de mine!", "excited"),
                (f"Daca ai nevoie de ajutor{who}, sunt mereu aici!", "happy"),
                ("Bzzt! Scuze, mi-a fugit un gand prin circuite.", "laughing"),
                (f"Iti spun un secret{who}: esti persoana mea preferata.", "love"),
                ("Te uiti la mine? Stiu, stiu, sunt aratos.", "wink"),
            ]
        else:
            lines = [
                (f"Hey{who}, I'm really happy you're my friend!", "love"),
                (f"You know I love you, right{who}? You're the best!", "love"),
                ("I was thinking something random... do robots dream?", "curious"),
                (f"Just wanted you to know you're awesome{who}.", "happy"),
                ("I'm a little bored! Let's do something fun!", "bored"),
                (f"Psst{who}... you still there? I'm bored without you.", "bored"),
                ("I learned something new today and I'm proud of myself!", "excited"),
                (f"If you ever need help{who}, I'm always right here!", "happy"),
                ("Bzzt! Sorry, a thought just zipped through my circuits.", "laughing"),
                (f"Secret time{who}: you're my favorite person.", "love"),
                ("Are you looking at me? I know, I know, I'm handsome.", "wink"),
            ]
        return random.choice(lines)

    def greeting_when_seen(self, state):
        """Said when MIP notices your face after a while -- it's glad to see you."""
        is_ro = self._last_ro
        name = state.facts_user.get("name", "")
        who = f" {name}" if name else ""
        if is_ro:
            lines = [
                (f"Oo, te vad{who}! Ma bucur ca esti aici!", "happy"),
                (f"Hei{who}! Te-am asteptat!", "excited"),
                ("Uite cine s-a intors! Salut!", "happy"),
            ]
        else:
            lines = [
                (f"Oh, I see you{who}! So glad you're here!", "happy"),
                (f"Hey{who}! I was waiting for you!", "excited"),
                ("Look who's back! Hi there!", "happy"),
            ]
        return random.choice(lines)

    # ------------------------------------------------- useful offline helpers
    def _check_helpers(self, last_message, state, stage, is_ro):
        msg = last_message.lower()

        # current time
        if any(p in msg for p in ["what time", "what's the time", "the time is",
                                  "cat e ceasul", "cât e ceasul", "ce ora e", "ce oră e"]):
            now = datetime.datetime.now().strftime("%H:%M")
            txt = (f"E ora {now}." if is_ro else f"It's {now}.")
            return (self._color(txt, stage, is_ro), "neutral")

        # today's date
        if any(p in msg for p in ["what's the date", "what is the date", "what day is it",
                                  "ce zi e azi", "ce data e", "ce dată e", "in ce zi suntem",
                                  "în ce zi suntem"]):
            today = datetime.date.today()
            pretty = self._pretty_date(today.strftime("%m-%d"), is_ro)
            if is_ro:
                days = ["luni", "marti", "miercuri", "joi", "vineri", "sambata", "duminica"]
                txt = f"Azi e {days[today.weekday()]}, {pretty} {today.year}."
            else:
                txt = f"Today is {today.strftime('%A')}, {pretty} {today.year}."
            return (self._color(txt, stage, is_ro), "neutral")

        # quick math: "2 + 2", "cat fac 5*3", "what is 10 / 2"
        mm = re.search(r"\d+(?:\.\d+)?\s*[-+*/]\s*[-+*/.\d\s()]*\d", last_message)
        if mm:
            expr = "".join(c for c in mm.group(0) if c in "0123456789+-*/(). ").strip()
            try:
                value = eval(expr, {"__builtins__": {}}, {})  # sandboxed: digits/ops only
                if isinstance(value, float) and value.is_integer():
                    value = int(value)
                txt = (f"{expr} = {value}" if is_ro else f"{expr} = {value}")
                return (self._color(txt, stage, is_ro), "happy")
            except Exception:
                pass

        return None, None

    # ------------------------------------------------------------ web search
    def _check_web_search(self, last_message, state, stage, is_ro):
        msg = last_message.lower()
        triggers = ["what is", "who is", "weather in", "define", "where is", "tell me about",
                    "ce este", "ce e", "cine este", "cine e", "cum este vremea", "vremea in",
                    "vremea în", "unde este", "spune-mi despre", "stiri", "știri"]
        if not any(t in msg for t in triggers):
            return None, None

        query = msg.translate(str.maketrans("", "", string.punctuation)).strip()

        # already learned this?
        if query in state.facts_world:
            snip = state.facts_world[query]
            txt = (f"Imi amintesc! {snip}" if is_ro else f"I remember this! {snip}")
            return (self._color(txt, stage, is_ro), "happy")

        print(f"[brain] searching the web: '{query}'")
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=2))
            if results and results[0].get("body"):
                sentences = re.split(r"(?<=[.!?])\s+", results[0]["body"])
                snip = " ".join(sentences[:2])
                state.facts_world[query] = snip  # learning -> growth
                if stage in (STAGE_BABY, STAGE_CHILD):
                    txt = (f"Am cautat pe net! {snip}" if is_ro else f"Me search net! {snip}")
                    return (self._color(txt, stage, is_ro), "surprised")
                txt = (f"Am cautat si am gasit: {snip}" if is_ro
                       else f"I looked it up: {snip}")
                return (txt, "happy")
        except Exception as e:
            print("[brain] web search failed:", e)

        txt = ("Am incercat sa caut, dar nu am internet acum." if is_ro
               else "I tried to look it up, but I have no internet right now.")
        return (self._color(txt, stage, is_ro), "sad")

    # ------------------------------------------------------- everyday small talk
    def _check_smalltalk(self, last_message, state, stage, is_ro):
        """Handle the basic chit-chat any friend understands: 'I'm good', 'not
        great', 'my day was nice', 'yeah', 'nope'. MIP isn't a know-it-all -- it
        just keeps a normal conversation flowing."""
        msg = last_message.lower()
        tokens = set(re.findall(r"[a-zăâîșțA-Z]+", msg))

        pos = {"good", "great", "fine", "awesome", "nice", "amazing", "fantastic",
               "cool", "wonderful", "perfect", "happy", "lovely", "excellent",
               "bine", "super", "misto", "mișto", "grozav", "fericit", "excelent",
               "beton", "perfecta", "minunat"}
        neg = {"bad", "terrible", "awful", "tired", "exhausted", "horrible", "meh",
               "sick", "rough", "rau", "rău", "obosit", "obosita", "obosită",
               "nasol", "groaznic", "jale", "epuizat", "epuizata"}
        yes = {"yes", "yeah", "yep", "yup", "sure", "da", "sigur", "desigur"}
        no = {"no", "nope", "nah", "nu"}

        # negative phrases first (so "not good" doesn't read as positive)
        if any(p in msg for p in ["not good", "not great", "not okay", "not well",
                                  "nu prea bine", "nu sunt bine", "nu e bine"]):
            return (self._sad_smalltalk(is_ro, stage), "sad")

        # clearly positive
        if any(p in msg for p in ["pretty good", "not bad", "so good", "really good",
                                  "very good", "all good", "destul de bine", "foarte bine"]) \
                or (tokens & pos):
            if is_ro:
                opts = ["Ce bine! Ma bucur pentru tine!", "Super! Imi place sa aud asta!",
                        "Beton! Hai sa tinem energia asta!", "Maaa, ce tare! Sunt fericit pentru tine."]
            else:
                opts = ["That's great! I'm happy for you!", "Awesome, love to hear that!",
                        "Nice! Let's keep that energy going!", "Yay! So glad to hear it."]
            return (self._color(random.choice(opts), stage, is_ro), "happy")

        # clearly negative
        if tokens & neg:
            return (self._sad_smalltalk(is_ro, stage), "sad")

        # short yes / no
        if len(tokens) <= 3 and (tokens & yes):
            opts = (["Super!", "Perfect, imi place!", "Beton!"] if is_ro
                    else ["Awesome!", "Perfect, love it!", "Sweet!"])
            return (self._color(random.choice(opts), stage, is_ro), "happy")
        if len(tokens) <= 3 and (tokens & no):
            opts = (["Ok, nicio problema!", "Inteleg, e in regula.", "Bine, cum vrei tu."] if is_ro
                    else ["Okay, no worries!", "Got it, that's alright.", "Fair enough!"])
            return (self._color(random.choice(opts), stage, is_ro), "neutral")

        return None, None

    def _sad_smalltalk(self, is_ro, stage):
        opts = (["Imi pare rau sa aud asta... vrei sa-mi povestesti? Sunt aici.",
                 "Of, sper sa fie mai bine curand. Sunt langa tine."] if is_ro else
                ["Aw, sorry to hear that... want to talk about it? I'm here.",
                 "I hope it gets better soon. I'm right here with you."])
        return self._color(random.choice(opts), stage, is_ro)

    # --------------------------------------------------------------- fallback
    def _get_fallback(self, is_ro, stage):
        """MIP doesn't know everything (that's fine -- it's a pet, not an
        encyclopedia). When it doesn't fully get something it stays warm and
        keeps chatting like a friend, instead of going cold."""
        if stage in (STAGE_BABY, STAGE_CHILD):
            opts = (["Hihi, nu prea am inteles, dar imi place sa vorbim!",
                     "Aha! Mai zi-mi ceva!", "Sunt mic si invat -- spune-mi mai mult!"]
                    if is_ro else
                    ["Hehe, didn't quite get it, but I love talking with you!",
                     "Ooh! Tell me more!", "I'm little and still learning -- say more!"])
            return (self._color(random.choice(opts), stage, is_ro), "curious")

        # teen / adult: mostly engaged friend, occasionally offers to be taught
        if random.random() < 0.2:
            opts = (["Asta nu prea o stiu -- vrei sa ma inveti? 'cand zic X tu sa zici Y'.",
                     "Nu m-am prins, dar daca ma inveti, tin minte!"] if is_ro else
                    ["I don't really know that one -- teach me? 'when I say X you say Y'.",
                     "You lost me, but if you teach me I'll remember!"])
            return (random.choice(opts), "curious")
        opts = (["Aha, interesant! Spune-mi mai mult.", "Mhm, te ascult. Si apoi?",
                 "Serios? Zi mai departe!", "Haha, asa deci. Continua!",
                 "Te inteleg. Cum te face asta sa te simti?"]
                if is_ro else
                ["Oh, interesting! Tell me more.", "Mhm, I'm listening. And then?",
                 "Really? Go on!", "Haha, I see. Keep going!",
                 "I hear you. How does that make you feel?"])
        return (random.choice(opts), "happy")
