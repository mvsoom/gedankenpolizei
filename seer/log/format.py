import logging
from pathlib import Path
from time import time

from dateutil.relativedelta import relativedelta

from seer import env

IMAGE_LOG_PATH = Path(env.LOG_DIR) / "images"
IMAGE_LOG_PATH.mkdir(parents=True, exist_ok=True)


def dump_image(image, extension="jpg"):
    file = IMAGE_LOG_PATH / (f"%.8f.{extension}" % time())
    image.save(file)
    return file


def markdown_image(image, extension="jpg"):
    file = dump_image(image, extension)
    relative_path = file.relative_to(Path("."))
    return f"![]({relative_path})"


def epoch_url(epoch):
    """Generate a URL to epochconverter.com for a given epoch time()."""
    # Uses an undocumented feature: http://disq.us/p/2h5flyd
    return f"https://www.epochconverter.com/?q={epoch}"


def markdown_link(text, url):
    return f"[{text}]({url})"


def human_readable(delta, _attrs=["days", "hours", "minutes", "seconds"]):
    delta.seconds = round(delta.seconds, 3)
    return "".join(
        [
            "%.3g%s" % (getattr(delta, attr), attr[0])
            for attr in _attrs
            if getattr(delta, attr)
        ]
    )


def indent_lines(lines, nindent=2):
    return "\n".join([" " * nindent + line for line in lines])


class MarkdownFormatter(logging.Formatter):
    def __init__(self, starttime):
        super().__init__()
        self.last = starttime

    def get_relative_time_url(self, record):
        last = self.last
        t = record.created
        delta = relativedelta(seconds=t - last)

        s = human_readable(delta)
        relative_time_url = markdown_link(f"+{s}", epoch_url(t))

        self.last = t
        return relative_time_url

    def get_images(self, record):
        images = [getattr(record, "image", None)]
        images += getattr(record, "images", [])
        return [image for image in images if image]

    def format(self, record):
        levelcode = record.levelname[0]
        relative_time_url = self.get_relative_time_url(record)
        preamble = f"- {levelcode} {relative_time_url}"

        message = preamble

        # Add images if present
        images = self.get_images(record)
        if images:
            message += "  \n"  # Hard break
            lines = [markdown_image(image) + "  " for image in images]
            message += indent_lines(lines)

        # Handle line breaks in the message if present
        msg = str(record.msg)
        lines = msg.split("\n")
        if len(lines) == 1:
            text = "```" + msg + "```"
            if not images:
                message += " " + text
            else:
                message += "\n" + indent_lines([text])
        else:
            indented_text = indent_lines(["```"] + lines + ["```"])
            message += "\n" + indented_text

        return message