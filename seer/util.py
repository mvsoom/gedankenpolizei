import logging
from copy import deepcopy
from time import time

from dateutil.relativedelta import relativedelta


def epoch_url(epoch):
    """Generate a URL to epochconverter.com for a given epoch time()."""
    # Uses an undocumented feature: http://disq.us/p/2h5flyd
    return f"https://www.epochconverter.com/?q={epoch}"


def human_readable(delta, _attrs=["days", "hours", "minutes", "seconds"]):
    delta.seconds = round(delta.seconds, 3)
    return "".join(
        [
            "%.3g%s" % (getattr(delta, attr), attr[0])
            for attr in _attrs
            if getattr(delta, attr)
        ]
    )


def markdown_link(text, url):
    return f"[{text}]({url})"


class TimeFilter(logging.Filter):
    def __init__(self, starttime):
        super().__init__()
        self.last = starttime

    def filter(self, record):
        last = self.last
        t = time()
        delta = relativedelta(seconds=t - last)

        s = human_readable(delta)
        record.relative = markdown_link(f"+{s}", epoch_url(t))

        self.last = t
        return True


def mask_base64_messages(message):
    """Mask base64 data in the Claude API messages"""
    masked_message = deepcopy(message)
    for message in masked_message:
        if message["role"] == "user":
            for content in message["content"]:
                if content["type"] == "image":
                    content["source"]["data"] = "<base64>"
    return masked_message