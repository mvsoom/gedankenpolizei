"""Tile images together in a single image. Code from https://github.com/mapluisch/LLaVA-CLI-with-multiple-images/blob/main/llava-multi-images.py"""

import argparse
from io import BytesIO
from math import ceil, sqrt

import requests
from PIL import Image


def load_image(image_file):
    if image_file.startswith("http://") or image_file.startswith("https://"):
        response = requests.get(image_file)
        image = Image.open(BytesIO(response.content)).convert("RGB")
    else:
        image = Image.open(image_file).convert("RGB")
    return image


def expand_image_range_paths(paths):
    expanded_paths = []
    for path in paths:
        if "{" in path and "}" in path:
            pre, post = path.split("{", 1)
            range_part, post = post.split("}", 1)
            start, end = map(int, range_part.split("-"))

            for i in range(start, end + 1):
                expanded_paths.append(f"{pre}{i}{post}")
        else:
            expanded_paths.append(path)

    return expanded_paths


def parse_resolution(resolution_str):
    try:
        width, height = map(int, resolution_str.split(","))
        return width, height
    except Exception as e:
        raise argparse.ArgumentTypeError("Resolution must be w,h.") from e


def concatenate_images_vertical(images, dist_images):
    width = max(img.width for img in images)
    total_height = sum(img.height for img in images) + dist_images * (len(images) - 1)
    new_img = Image.new("RGB", (width, total_height), (0, 0, 0))
    current_height = 0
    for img in images:
        new_img.paste(img, (0, current_height))
        current_height += img.height + dist_images
    return new_img


def concatenate_images_horizontal(images, dist_images):
    total_width = sum(img.width for img in images) + dist_images * (len(images) - 1)
    height = max(img.height for img in images)
    new_img = Image.new("RGB", (total_width, height), (0, 0, 0))
    current_width = 0
    for img in images:
        new_img.paste(img, (current_width, 0))
        current_width += img.width + dist_images
    return new_img


def concatenate_images_grid(images, dist_images, output_size):
    num_images = len(images)
    grid_size = max(1, ceil(sqrt(num_images)))
    cell_width = (output_size[0] - dist_images * (grid_size - 1)) // grid_size
    cell_height = (output_size[1] - dist_images * (grid_size - 1)) // grid_size
    new_img = Image.new("RGB", output_size, (0, 0, 0))
    for index, img in enumerate(images):
        img_ratio = img.width / img.height
        target_ratio = cell_width / cell_height
        if img_ratio > target_ratio:
            new_width = cell_width
            new_height = int(cell_width / img_ratio)
        else:
            new_width = int(cell_height * img_ratio)
            new_height = cell_height
        resized_img = img.resize((new_width, new_height), Image.LANCZOS)
        row = index // grid_size
        col = index % grid_size
        x_offset = col * (cell_width + dist_images) + (cell_width - new_width) // 2
        y_offset = row * (cell_height + dist_images) + (cell_height - new_height) // 2
        new_img.paste(resized_img, (x_offset, y_offset))
    return new_img


def concatenate_images(images, strategy, dist_images, grid_resolution):
    if strategy == "vertical":
        return concatenate_images_vertical(images, dist_images)
    elif strategy == "horizontal":
        return concatenate_images_horizontal(images, dist_images)
    elif strategy == "grid":
        return concatenate_images_grid(images, dist_images, grid_resolution)
    else:
        raise ValueError("Invalid concatenation strategy specified")


def main(args):
    args.images = expand_image_range_paths(args.images)
    images = [load_image(img_file) for img_file in args.images]

    for img in images:
        print(f"Image size: {img.size[0]}x{img.size[1]}")

    image = (
        concatenate_images(
            images, args.concat_strategy, args.dist_images, args.grid_resolution
        )
        if len(images) > 1
        else images[0]
    )

    print(f"Concatenated image size: {image.size[0]}x{image.size[1]}")

    if args.save_image:
        image.save("concat-image.jpg")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--images",
        type=str,
        nargs="+",
        required=True,
        help="Specify the paths for images to be concatenated. Accepts multiple paths, or range of images in the same location, e.g. img{1-4}.jpg.",
    )

    parser.add_argument(
        "--save-image",
        action="store_true",
        help="If used, stores the resulting concatenated image in the LLaVA directory as 'concat-image.jpg'.",
    )

    parser.add_argument(
        "--concat-strategy",
        type=str,
        default="vertical",
        choices=["vertical", "horizontal", "grid"],
        help="Determines the arrangement strategy for image concatenation. Options: 'vertical', 'horizontal', 'grid'.",
    )

    parser.add_argument(
        "--dist-images",
        type=int,
        default=20,
        help="Sets the spacing (in pixels) between concatenated images.",
    )

    parser.add_argument(
        "--grid-resolution",
        type=parse_resolution,
        default="2560,1440",
        help="Fixed resolution of the resulting grid image. Specify as width, height. Default is 2560,1440.",
    )

    args = parser.parse_args()
    main(args)
