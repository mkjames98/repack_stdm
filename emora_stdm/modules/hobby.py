from emora_stdm import DialogueFlow, KnowledgeBase, Macro
from enum import Enum, auto
import random

TRANSITION_OUT = ["movies", "music", "sports"]
NULL = "NULL TRANSITION"

class IsHobby(Macro):
    def run(self, ngrams, vars, args):
        if "hobby" in vars and len(args) > 0:
            if vars["hobby"] == args[0]:
                return True
        return False

class IsNoInfoHobby(Macro):
    def __init__(self, d):
        self.onte = d._macros["ONTE"]

    def run(self, ngrams, vars, args):
        if "hobby" in vars and vars["hobby"] in self.onte(None, vars, ["unknown_hobby"]):
            return True
        return False

class TryGetHobby(Macro):
    def run(self, ngrams, vars, args):
        if "hobby" in vars and vars["hobby"] is not None:
            return vars["hobby"]
        else:
            return "it"

class ResetHobby(Macro):
    def run(self, ngrams, vars, args):
        if "hobby" in vars:
            vars["hobby"] = None

class ResetLoop(Macro):
    def run(self, ngrams, vars, args):
        if "loop_count" in vars:
            vars["loop_count"] = 0

class UpdateCoveredHobbies(Macro):
    def run(self, ngrams, vars, args):
        if "covered_hobbies" not in vars:
            vars["covered_hobbies"] = set()
        if "hobby" in vars and vars["hobby"] is not None:
            vars["covered_hobbies"].add(vars["hobby"])
        return None

class UpdateLikedHobbies(Macro):
    def run(self, ngrams, vars, args):
        if "liked_hobbies" not in vars:
            vars["liked_hobbies"] = set()
        if "hobby" in vars and vars["hobby"] is not None:
            liked = vars["hobby"]
            vars["liked_hobbies"].add(liked)
            if "covered_hobbies" not in vars:
                vars["covered_hobbies"] = set()
            if liked not in vars["covered_hobbies"]:
                vars["covered_hobbies"].add(liked)
        return None

class UnCoveredHobby(Macro):
    def __init__(self, d):
        self.ontn = d._macros["ONTN"]
    def run(self, ngrams, vars, args):
        hobbies = self.ontn(None, vars, ["known_hobby"])
        if "covered_hobbies" in vars:
            covered = vars["covered_hobbies"]
            uncovered = hobbies - covered
            if len(uncovered) > 0:
                return uncovered
            hobbies = self.ontn(None, vars, ["unknown_hobby"])
            return hobbies - covered
        if len(hobbies) == 0:
            hobbies = self.ontn(None, vars, ["unknown_hobby"])
        return hobbies

class CoveredHobbySent(Macro):
    def run(self, ngrams, vars, args):
        num = int(args[0])
        if "liked_hobbies" in vars:
            hobs = random.sample(vars["liked_hobbies"], num)
            return ', and '.join(hobs)
        return 'different hobbies'

class Check(Macro):
    def run(self, ngrams, vars, args):
        var = args[0]
        val = args[1]
        if val.isdigit():
            val = int(val)
        if var in vars and vars[var] == val:
            return True
        return False

class Increment(Macro):
    def run(self, ngrams, vars, args):
        var = args[0]
        if var not in vars or vars[var] is None:
            vars[var] = 0
        vars[var] += 1
        return None

class State(Enum):
    START = auto()
    FIRST_ASK_HOBBY = auto()
    GEN_ASK_HOBBY = auto()
    REC_HOBBY = auto()
    RECOG_NO_INFO_HOBBY = auto()
    ASK_FAVE_THING = auto()
    EXPERIENCE = auto()
    CHALLENGE = auto()
    UNSURE = auto()
    NO_RECOG_FAVE = auto()
    NO_RECOG_HOBBY = auto()
    PROMPT_HOBBY = auto()
    READING_GENRE = auto()
    LIKE_READING = auto()
    ACK_NO_LIKE = auto()
    ACK_NEVER_TRIED = auto()
    PROMPT_RES_ERR = auto()
    LIKE_HOBBY = auto()
    LIKE_HOBBY_ERR = auto()
    ASK_GENRE = auto()
    UNRECOG_GENRE = auto()
    REDIRECT = auto()
    CONTINUE = auto()
    ACK_END = auto()
    END = auto()

hobby_opinion = {
    "cooking",
    "programming",
    "reading",
    "running",
    "writing"
}

knowledge = KnowledgeBase()
knowledge.load_json_file("hobbies.json")
df = DialogueFlow(State.START, DialogueFlow.Speaker.USER,
                  kb=knowledge)
macros = {"IsHobby": IsHobby(), "IsNoInfoHobby": IsNoInfoHobby(df),
          "UpdateCoveredHobbies": UpdateCoveredHobbies(), "UpdateLikedHobbies": UpdateLikedHobbies(),
          "TryGetHobby": TryGetHobby(), "ResetHobby": ResetHobby(), "UnCoveredHobby": UnCoveredHobby(df),
          "CoveredHobbySent": CoveredHobbySent(), "Check":Check(), "Increment":Increment(), "ResetLoop":ResetLoop()}
df._macros.update(macros)

### if user initiates
request_hobby_nlu = '[#EXP(chat)? {hobby,hobbies,activity,activities,fun things,things to do,pasttimes}]'
df.add_user_transition(State.START, State.FIRST_ASK_HOBBY, request_hobby_nlu)
df.set_error_successor(State.START, State.START)
df.add_system_transition(State.START, State.START, NULL)

### (SYSTEM) TWO OPTIONS FOR STARTING HOBBY COMPONENT - what hobby do you like vs ive heard of hobby, do you like it

first_ask_hobby_nlg = ['"So, it seems like you want to talk about some activities. There are so many choices of what to do these days for fun. I never know what to choose. What is your favorite hobby?"',
                 '"I see. It seems like you want to talk about different pasttimes. Im always looking for new activities to try out. Tell me, what is your favorite hobby these days?"',
                 '"So, I think you want to talk about some hobbies. Do you have an activity you like to do in your free time? I like learning new things to try out based on what other people like."',
                 '"I see. Lets talk about hobbies then. Everyone has such different answers to this, but I was wondering what you like to do to relax and have fun? "',
                 ]
df.add_system_transition(State.FIRST_ASK_HOBBY, State.REC_HOBBY, first_ask_hobby_nlg)

gen_ask_hobby_nlg = ['[!"What is another hobby you like?" #Increment(loop_count)]',
                        '"Tell me, what is another one of your favorite hobbies?"',
                        '"Do you have a different activity you like to do in your free time?"',
                         '"What do you like to do to have fun?"',
                     '"Are there any other activities that you enjoy as well?"',
                     '"What else do you enjoy doing?"',
                     '"Do you have any other things that you would consider to be your hobbies?"']
df.add_system_transition(State.GEN_ASK_HOBBY, State.REC_HOBBY, gen_ask_hobby_nlg)

first_prompt_hobby_nlg = ['[!So"," it seems like you want to talk about some activities"." One activity that a lot of people have mentioned to me is $hobby=#UnCoveredHobby()"." Is this something you like to do"?"]',
                    '[!I see"." It seems like you want to talk about hobbies"." Ive been hearing a bit about $hobby"." Do you like $hobby"?"]'
                    ]
gen_prompt_hobby_nlg = ['[!"Another activity that a lot of people have mentioned to me is " $hobby=#UnCoveredHobby() ". Is this something you like to do?" #Increment(loop_count)]',
                    '[!"You know, I have also been hearing a bit about " $hobby ". Do you like " $hobby "?"]'
                    ]
df.add_system_transition(State.FIRST_ASK_HOBBY, State.PROMPT_HOBBY, first_prompt_hobby_nlg)
df.add_system_transition(State.GEN_ASK_HOBBY, State.PROMPT_HOBBY, gen_prompt_hobby_nlg)

redirect_nlg = ['[!#Check(loop_count,3) "We seem to have been talking about hobbies for a bit. Do you want to talk about something else?"]',
                '[!#Check(loop_count,3) "I am really enjoying talking to you about all of these different activities, but if you want to be done, we can move on to something else. Do you want to stop talking about hobbies?"]']
df.add_system_transition(State.GEN_ASK_HOBBY, State.REDIRECT, redirect_nlg, score=1.1)

### (USER) ANSWERING REDIRECTION QUESTION
talk_something_else_nlu = '{{talk,chat,conversation,discussion,discuss,move on} -{hobbies,activities,pasttimes,hobby,activity,pasttime}}'
df.add_user_transition(State.REDIRECT, State.ACK_END, '[{#EXP(yes),%s} #ResetLoop()]'%talk_something_else_nlu)

no_nlu = '{[#EXP(no)], [!{i dont, i do not, no i dont, no i do not}]}'
continue_nlu = '[{keep {talking,going}, continue, not {done,finished,completed}}]'
df.add_user_transition(State.REDIRECT, State.CONTINUE, '[{%s,%s} #ResetLoop()]'%(continue_nlu,no_nlu))

### (SYSTEM) CONTINUING
df.add_system_transition(State.CONTINUE, State.GEN_ASK_HOBBY, ['"ok, so, "', '"let us continue then."'])

### (USER) ANSWERING YES TO PROMPT HOBBY
yes_nlu = '[[! -not {#EXP(yes),#ONT(yes_qualifier)}]]'
df.add_user_transition(State.PROMPT_HOBBY, State.LIKE_HOBBY, yes_nlu)
df.update_state_settings(State.LIKE_HOBBY, user_multi_hop=True)
df.add_user_transition(State.LIKE_HOBBY, State.LIKE_READING, "[!#IsHobby(reading)]")
df.add_user_transition(State.LIKE_HOBBY, State.RECOG_NO_INFO_HOBBY, "[!#IsNoInfoHobby()]")
like_hobby_err_nlg = ['"Sorry, I dont seem to have understood your answer very well. Lets try something else."',
                     '[!"Im glad you like" #TryGetHobby() ". Now I am curious."]'
                     ]
df.set_error_successor(State.LIKE_HOBBY, State.LIKE_HOBBY_ERR)
df.add_system_transition(State.LIKE_HOBBY_ERR, State.GEN_ASK_HOBBY, like_hobby_err_nlg)

### (USER) ANSWERING NO TO PROMPT HOBBY
df.add_user_transition(State.PROMPT_HOBBY, State.ACK_NO_LIKE, no_nlu)

### (USER) ANSWERING NEVER TRIED TO PROMPT HOBBY
never_tried_nlu = '{[! -you [never] [{tried, heard, done}]], [#ONT(uncertain_expression)]}'
df.add_user_transition(State.PROMPT_HOBBY, State.ACK_NEVER_TRIED, never_tried_nlu)

### (USER) ERROR TO PROMPT HOBBY
prompt_hobby_err_nlg = ['[!"Sorry, I dont seem to have understood your answer very well. Lets try something else." #UpdateCoveredHobbies()]',
                        '[!"You have provided an interesting answer to whether you like" #TryGetHobby() ", but I am still learning about it. "]'
                     ]
df.set_error_successor(State.PROMPT_HOBBY, State.PROMPT_RES_ERR)
df.add_system_transition(State.PROMPT_RES_ERR, State.GEN_ASK_HOBBY, prompt_hobby_err_nlg)

### (SYSTEM) RESPONDING TO USERS NO TO LIKE HOBBY PROMPT
df.update_state_settings(State.GEN_ASK_HOBBY, system_multi_hop=True)
ack_no_like_nlg = ['[!"I see. Im glad to learn that you dont really care for" #TryGetHobby() "." #UpdateCoveredHobbies()]',
                    '[!"Really? Thats very interesting to hear that you dont like" #TryGetHobby() "."]'
                    ]
df.add_system_transition(State.ACK_NO_LIKE, State.GEN_ASK_HOBBY, ack_no_like_nlg)

### (SYSTEM) RESPONDING TO NEVER TRIED TO LIKE HOBBY PROMPT
ack_never_tried_nlg = ['[!"Oh. It sounds like you have never tried" #TryGetHobby() ". Thats ok." #UpdateCoveredHobbies()]',
                        '[!"Wow, youve never done it? I find it fascinating to see the diversity in everyones life, since others have mentioned" $hobby "to me before."]'
                        ]
df.add_system_transition(State.ACK_NEVER_TRIED, State.GEN_ASK_HOBBY, ack_never_tried_nlg)

### (USER) RECEIVING SPECIFIC HOBBY USER LIKES WHERE HOBBY HAS INFO FOR EMORA

### (USER) RECEIVING SPECIFIC HOBBY USER LIKES WHERE HOBBY HAS NO INFO FOR EMORA

init_noinfo_hobby_nlu = ["[[! #ONT(also_syns)?, i, #ONT(also_syns)?, like, $hobby=#ONT(unknown_hobby), #ONT(also_syns)?]]",
                  "[$hobby=#ONT(unknown_hobby)]"]
df.add_user_transition(State.REC_HOBBY, State.RECOG_NO_INFO_HOBBY, init_noinfo_hobby_nlu)
init_info_hobby_nlu = ["[[! #ONT(also_syns)?, i, #ONT(also_syns)?, like, $hobby=#ONT(known_hobby), #ONT(also_syns)?]]",
                        "[$hobby=#ONT(known_hobby)]"]
df.add_user_transition(State.REC_HOBBY, State.LIKE_HOBBY, init_info_hobby_nlu)
decline_share = "{" \
                "[#ONT(ont_negation), {talk, talking, discuss, discussing, share, sharing, tell, telling, say, saying, remember}]," \
                "<{dont,do not}, {know, want to, [have, {idea,answer,response,any,anything,one}]}>," \
                "<not, sure>" \
                "}"
no_more_hobbies_nlu = '{["no more"], [i, dont, have, more], [i, do, not, have, more], ' \
                      '[thats it], [that is it], [nothing], [all done], [im, done], [i, am, done], %s, %s}'%(no_nlu,decline_share)
df.add_user_transition(State.REC_HOBBY, State.ACK_END, no_more_hobbies_nlu)
df.set_error_successor(State.REC_HOBBY, State.NO_RECOG_HOBBY)

### (SYSTEM) END CONVO AFTER USER INDICATES NO MORE HOBBIES
end_nlg = ['"It has been fun talking about these different activities with you. But lets move on to something else. %s are on my mind. Which would you like to talk about?"'%(', and '.join(TRANSITION_OUT)),
            '[!"I have enjoyed learning about your opinions on " #CoveredHobbySent(2) ". Right now, I am also interested in %s. What topic do you want to talk about next?"]'%(', and '.join(TRANSITION_OUT)),
           '"This has been great. Ive learned some new things and some new activities I may end up trying. But until then, what would you like to chat about next? I think %s would be good."'%(', or '.join(TRANSITION_OUT))
            ]
df.add_system_transition(State.ACK_END, State.END, end_nlg)
df.add_user_transition(State.END, State.GEN_ASK_HOBBY, request_hobby_nlu)
df.set_error_successor(State.END, State.END)
df.add_system_transition(State.END, State.END, NULL)

### (SYSTEM) ACKNOWLEDING IT HAS NEVER HEARD OF SUCH HOBBY
# todo - save utterance into user attributes
no_recog_hobby_nlg = ['[!"Ive never heard that one. What is your favorite thing about it?" #ResetHobby]',
                        '[!"Im not very familiar with that. What would you say you enjoy the most about it?"]',
                        '[!"Wow, it is not every day that I hear about a brand new activity for me. What is your favorite thing about it?"]',
                        '[!"I dont remember if I have ever heard of that activity before. What do you enjoy the most about it?"]'
                      ]
df.add_system_transition(State.NO_RECOG_HOBBY, State.ASK_FAVE_THING, no_recog_hobby_nlg)

### (SYSTEM) ASKING FOR FAVORITE THING ABOUT NO INFO HOBBY

ask_fave_thing_nlg = ['[!You like $hobby"?" I dont know much about it"." What is your favorite thing about $hobby"?" #UpdateLikedHobbies()]',
                        '[!Wow"," you do like $hobby"?" Im interested in learning more about it"." What would you say you enjoy the most about $hobby"?"]',
                        '[! Ive never done $hobby"." What is your favorite thing about $hobby"?"]',
                        '[!"Im glad to learn more about the activities that you like. What do you enjoy the most about" $hobby"?"]'
                      ]
df.add_system_transition(State.RECOG_NO_INFO_HOBBY, State.ASK_FAVE_THING, ask_fave_thing_nlg)

### (USER) RECEIVING FAVORITE THING ABOUT NO INFO HOBBY

pos_exp_nlu = ["[#ONT(pos_experience)]"]
df.add_user_transition(State.ASK_FAVE_THING, State.EXPERIENCE, pos_exp_nlu)
challenge_exp_nlu = ["[#ONT(challenge_experience)]"]
df.add_user_transition(State.ASK_FAVE_THING, State.CHALLENGE, challenge_exp_nlu)
uncertain_expression_nlu = ["[#ONT(uncertain_expression)]"]
df.add_user_transition(State.ASK_FAVE_THING, State.UNSURE, uncertain_expression_nlu)

df.add_state(State.NO_RECOG_FAVE)
df.set_error_successor(State.ASK_FAVE_THING, State.NO_RECOG_FAVE)

### (SYSTEM) RESPONDING TO FAVORITE THING ABOUT NO INFO HOBBY

ack_experience_nlg = ['[! its great to find something that you enjoy"."]',
                      '[! having fun experiences is important for everyone"," im glad you enjoy #TryGetHobby() "."]'
                      '[! sometimes just enjoying yourself is exactly what you need "."]'
                     ]
df.add_system_transition(State.EXPERIENCE, State.GEN_ASK_HOBBY, ack_experience_nlg)

ack_challenge_nlg = ['[! pursuing personal growth is an admirable trait"." it sounds like you embody this and i am impressed"."]',
                      '[! it always feels great to overcome a challenge"," im glad you find #TryGetHobby() so rewarding"."]'
                      '[! i see"." i do think working hard at something is sometimes just as fun as doing more relaxing activities"."]'
                        ]
df.add_system_transition(State.CHALLENGE, State.GEN_ASK_HOBBY, ack_challenge_nlg)

ack_unsure_nlg = ['[! i understand"." sometimes it is hard to put your reasons into words"."]',
                      '[! ok"," well"," you dont always need to have an explicit reason for liking something "."]'
                      '[! i see"." i do think that sometimes we just enjoy things so completely that we do not need to have a reason for it"."]'
                        ]
df.add_system_transition(State.UNSURE, State.GEN_ASK_HOBBY, ack_unsure_nlg)

no_recog_fave_nlg = ['[!I dont think I understood all of that"," but Im glad to hear more about your opinions"."]',
                     '[!You are so knowledgeable about #TryGetHobby()"." I am hoping to learn all sorts of things like this"," so I am very happy to be talking to you"."]',
                     '[!Thanks for sharing that with me"." I am very interested in learning about your opinions"." It is so much fun to see what people like"!"]']

df.add_system_transition(State.NO_RECOG_FAVE, State.GEN_ASK_HOBBY, no_recog_fave_nlg)


### (SYSTEM) ASKING ABOUT FAVE GENRE OF BOOK

reading_ask_genre_nlg = ['[!"Oh, you like reading? What kind of books do you enjoy the most?" #UpdateLikedHobbies()]',
                        '[!"Im so glad you like reading. Books are a great way to explore imaginary worlds and characters. What type of books do you like reading?"]',
                         '[!"Reading can be so much fun. What stories do you find the most enjoyable?"]'
                        ]

df.add_system_transition(State.LIKE_READING, State.ASK_GENRE, reading_ask_genre_nlg)


### (USER) SHARING FAVE GENRE OF BOOK
df.set_error_successor(State.ASK_GENRE, State.UNRECOG_GENRE)
fave_genre_error_nlg = ['"I dont know if I know of any books like that, but that is something I will think about."',
                        '"Huh, what a unique answer. Im not sure what kinds of books those are, but I am looking forward to looking into this more."'
                        ]
df.add_system_transition(State.UNRECOG_GENRE, State.GEN_ASK_HOBBY, fave_genre_error_nlg)

if __name__ == '__main__':
    # automatic verification of the DialogueFlow's structure (dumps warnings to stdout)
    df.check()
    # run the DialogueFlow in interactive mode to test
    df.run(debugging=True)