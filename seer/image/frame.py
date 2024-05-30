import base64
import datetime
from io import BytesIO

import cv2
from PIL import Image, ImageDraw, ImageFont


def raw_to_image(cv_matrix):
    a = cv2.cvtColor(cv_matrix, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(a)
    return image


def sample_frames(ts, frames, n):
    """Use uniform sampling that always includes the last frame"""
    length = len(ts)
    assert length == len(frames), "Timestamps and frames must have the same length"

    if n >= length or n <= 0:
        return (ts, frames)

    step = length / n
    indices = [round(step * i) for i in range(n - 1)]
    indices.append(length - 1)

    return [ts[i] for i in indices], [frames[i] for i in indices]


def format_time(t):
    """Put a timestamp on the frame"""
    reference_time = datetime.datetime.fromtimestamp(t)
    formatted_time = reference_time.strftime("%H:%M:%S.%f")[:-4]
    return formatted_time


def timestamp(t, frame):
    """Put a timestamp on the frame"""
    formatted_time = format_time(t)
    fontsize = 0.075 * min(frame.size)
    draw = ImageDraw.Draw(frame)
    font = ImageFont.load_default(size=fontsize)
    text_color = "#66FF00"
    draw.text((10, 10), formatted_time, font=font, fill=text_color)


def encode_image(image, max_size=None):
    """Encode an image to JPEG in base64 format"""
    if max_size:
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)

    image_data = BytesIO()
    image.save(image_data, format="JPEG")
    image_data.seek(0)
    base64_encoded = base64.b64encode(image_data.getvalue()).decode("utf-8")

    return base64_encoded