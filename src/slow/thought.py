from src.slow.df import SLOWDF  # Takes a while
from src.slow.embed import embed  # Takes a while


def random_thought():
    return SLOWDF.sample().iloc[0].thought


class SlowThought:
    def __init__(self, id=None, text=None, embedding=None):
        if text is not None:
            self.text = text
            self.embedding = embedding or embed(text)
        elif embedding is not None:
            self.text = None
            self.embedding = embedding
        else:
            self
