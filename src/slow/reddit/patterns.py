import re


REDACTED_KEYWORDS = [
    "redacted",
    "removed",
    "edit",
    "edited",
    "modified",
    "updated",
    "fixed",
    "resolved",
    "deleted",
    "censored",
    "hidden",
    "blocked",
    "unavailable",
    "banned",
    "expired",
    "archived",
    "locked",
    "quarantined",
    "private",
    "restricted",
    "suspended",
    "filtered",
    "erased",
    "omitted",
    "withdrawn",
    "retracted",
    "unpublished",
    "inaccessible",
]

# Matches [redacted], [removed by mod], [deleted], etc.
REDACTED = (
    r"\[[^\[\]]*(?:" + "|".join(map(re.escape, REDACTED_KEYWORDS)) + r")[^\[\]]*\]"
)

# From https://stackoverflow.com/a/48689681/6783015
URL = r"((http|https)\:\/\/)?[a-zA-Z0-9\/\?\:@\-_=#]+(\.[a-zA-Z0-9\/\?\:@\-_=#]+)*\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*"

# Matches r/subreddit, u/username, reddit, etc.
REDDITLIKE = r"\b\w*reddit\w*\b|\br/\w+|\bu/\w+"

# Matches @mentions and #hashtags (sloppily)
TWITTER = r"\B(@[A-Za-z0-9_]{4,15}|#[A-Za-z0-9_]{4,})\b"


def word_boundaries(*args):
    return [rf"\b{a}\b" for a in args]


AUTOVET_PATTERNS = {
    "PERSONAL": [
        *word_boundaries(
            "marriage",
            "mom(s)?",
            "dad(s)?",
            "mommy",
            "mum",
            "daddy",
            "my family",
            "my mother",
            "my father",
            "my parents",
            "my son",
            "my daughter",
            "my brother(s)?",
            "my sister(s)?",
            "my ex(-wife)?",
            "my (ex-)?husband",
            "my child(ren)?",
            "my kid(s)?",
            "my uncle",
            "my aunt",
            "my grandma",
            "my friend(s)?",
            "my home",
            "my appartment",
            "my house",
            "my country",
            "my pet",
            "my dog",
            "my cat",
            "my roommate(s)?",
            "my housemate(s)?",
            "my car",
            "boyfriend",
            "girlfriend",
            "bff",
            "bf",
            "gf",
            "(high)?school",
            "college",
            "undergrad",
        )
    ],
    "SEXUAL": [
        *word_boundaries(
            "cock",
            "fap(ping)?",
            "my dick",
            "my balls",
            "anal",
            "blowjobs(s)?",
            "virgin",
            "dating",
        )
    ],
    "SOCIAL_MEDIA": [
        *word_boundaries(
            "(sub)?reddit",
            "moderator(s)?",
            "redditor(s)?",
            "comment(s)?",
            "front page",
            "upvote",
            "downvote",
            "post(s)?",
            "posted by",
            "repost(s)?",
            "posting",
            "discord",
            "4chan",
            "/rant",
            "s/o",
            "nsfw",
            "my username",
            "hello everyone",
            "read on to",
            "readers",
            "tl;dr",
            "poll",
            "my writing",
            "thank you",
            "this video",
            "soundcloud",
            "podcast",
            "you guys",
            "admin",
        ),
        REDACTED,
        URL,
        REDDITLIKE,
        TWITTER,
        r"\bedit:\B",  # Needs special care (\B) due to colon
    ],
    "AGE": [
        r"\b\d\d\s*\(?[fFmM]\)?\b",  # 28m/28f/28 f/28 (m) (but also 28m $)
        r"\b\d\dyo\b",  # 28yo
        r"\bi(\')?m (a )?\d\d\b",  # I'm/Im/im (a) 28 (but also I'm 28% sure)
        r"\b\d\d year old (fe)?male\b",
    ],
    "MISC": [
        *word_boundaries(
            "spencer",
            "courtney",
            "sileo",
            "parker",
        )
    ],
}
