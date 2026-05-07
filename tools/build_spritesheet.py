#!/usr/bin/env python3
"""Build the Haengseongi Codex pet spritesheet from authorized references."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


CELL_WIDTH = 192
CELL_HEIGHT = 208
COLUMNS = 8
ROWS = 9
ATLAS_SIZE = (CELL_WIDTH * COLUMNS, CELL_HEIGHT * ROWS)


@dataclass(frozen=True)
class Pose:
    name: str
    image: Image.Image


@dataclass(frozen=True)
class Placement:
    pose: str
    scale: float = 1.0
    rotate: float = 0.0
    offset_x: int = 0
    offset_y: int = 0
    mirror: bool = False


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return (0, 0, image.width, image.height)
    return bbox


def tight_crop(image: Image.Image, padding: int = 4) -> Image.Image:
    image = image.convert("RGBA")
    left, top, right, bottom = alpha_bbox(image)
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(image.width, right + padding)
    bottom = min(image.height, bottom + padding)
    return image.crop((left, top, right, bottom))


def white_background_to_alpha(image: Image.Image) -> Image.Image:
    """Remove the outer white background while preserving enclosed white fills."""

    image = image.convert("RGBA")
    rgb = image.convert("RGB")
    width, height = image.size

    barrier = Image.new("L", image.size, 0)
    source = rgb.load()
    barrier_pixels = barrier.load()
    for y in range(height):
        for x in range(width):
            red, green, blue = source[x, y]
            if min(red, green, blue) < 225:
                barrier_pixels[x, y] = 255

    barrier = barrier.filter(ImageFilter.MaxFilter(5))
    barrier_pixels = barrier.load()
    visited = Image.new("1", image.size, 0)
    visited_pixels = visited.load()
    stack: list[tuple[int, int]] = []

    def enqueue(x: int, y: int) -> None:
        if x < 0 or y < 0 or x >= width or y >= height:
            return
        if visited_pixels[x, y]:
            return
        if barrier_pixels[x, y]:
            return
        red, green, blue = source[x, y]
        if red < 235 or green < 235 or blue < 235:
            return
        visited_pixels[x, y] = 1
        stack.append((x, y))

    for x in range(width):
        enqueue(x, 0)
        enqueue(x, height - 1)
    for y in range(height):
        enqueue(0, y)
        enqueue(width - 1, y)

    while stack:
        x, y = stack.pop()
        enqueue(x + 1, y)
        enqueue(x - 1, y)
        enqueue(x, y + 1)
        enqueue(x, y - 1)

    result = image.copy()
    pixels = result.load()
    for y in range(height):
        for x in range(width):
            if visited_pixels[x, y]:
                red, green, blue, _alpha = pixels[x, y]
                pixels[x, y] = (red, green, blue, 0)
    return tight_crop(result)


def load_transparent(path: Path) -> Image.Image:
    return tight_crop(Image.open(path).convert("RGBA"))


def load_sheet_pose(sheet: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    return white_background_to_alpha(sheet.crop(box))


def fit_into_cell(
    image: Image.Image,
    *,
    scale: float = 1.0,
    rotate: float = 0.0,
    offset_x: int = 0,
    offset_y: int = 0,
    mirror: bool = False,
    padding: int = 10,
) -> Image.Image:
    sprite = image.convert("RGBA")
    if mirror:
        sprite = ImageOps.mirror(sprite)
    if rotate:
        sprite = sprite.rotate(
            rotate,
            resample=Image.Resampling.BICUBIC,
            expand=True,
            fillcolor=(255, 255, 255, 0),
        )
        sprite = tight_crop(sprite, padding=2)

    max_width = CELL_WIDTH - padding * 2
    max_height = CELL_HEIGHT - padding * 2
    ratio = min(max_width / sprite.width, max_height / sprite.height) * scale
    new_size = (
        max(1, round(sprite.width * ratio)),
        max(1, round(sprite.height * ratio)),
    )
    sprite = sprite.resize(new_size, Image.Resampling.LANCZOS)

    cell = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (255, 255, 255, 0))
    x = (CELL_WIDTH - sprite.width) // 2 + offset_x
    y = (CELL_HEIGHT - sprite.height) // 2 + offset_y
    cell.alpha_composite(sprite, (x, y))
    return cell


def checkerboard(size: tuple[int, int], block: int = 16) -> Image.Image:
    image = Image.new("RGBA", size, (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], block):
        for x in range(0, size[0], block):
            shade = 238 if (x // block + y // block) % 2 == 0 else 255
            draw.rectangle((x, y, x + block - 1, y + block - 1), fill=(shade, shade, shade, 255))
    return image


def draw_pose_preview(poses: dict[str, Pose], output_path: Path) -> None:
    names = list(poses)
    tile_width = 220
    tile_height = 220
    columns = 4
    rows = (len(names) + columns - 1) // columns
    preview = checkerboard((tile_width * columns, tile_height * rows), 14)
    draw = ImageDraw.Draw(preview)
    font = ImageFont.load_default()
    for index, name in enumerate(names):
        col = index % columns
        row = index // columns
        left = col * tile_width
        top = row * tile_height
        cell = fit_into_cell(poses[name].image, padding=16)
        preview.alpha_composite(cell, (left + 14, top + 4))
        draw.text((left + 8, top + tile_height - 18), name, fill=(0, 0, 0), font=font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    preview.save(output_path)


def build_contact_sheet(atlas: Image.Image, row_defs: list[tuple[str, int]], output_path: Path) -> None:
    row_header = 24
    width = ATLAS_SIZE[0]
    height = ROWS * (CELL_HEIGHT + row_header)
    sheet = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    for row_index, (state, frames) in enumerate(row_defs):
        top = row_index * (CELL_HEIGHT + row_header)
        draw.rectangle((0, top, width, top + row_header - 1), fill=(0, 0, 0))
        draw.text((6, top + 6), f"row {row_index}: {state}", fill=(255, 255, 255), font=font)
        draw.text((width - 72, top + 6), f"{frames} frames", fill=(255, 255, 255), font=font)

        row_bg = checkerboard((width, CELL_HEIGHT), 16)
        row_crop = atlas.crop((0, row_index * CELL_HEIGHT, width, (row_index + 1) * CELL_HEIGHT))
        row_bg.alpha_composite(row_crop, (0, 0))
        sheet.alpha_composite(row_bg, (0, top + row_header))

        for col in range(COLUMNS):
            left = col * CELL_WIDTH
            color = (12, 176, 96) if col < frames else (230, 32, 48)
            draw.rectangle(
                (left, top + row_header, left + CELL_WIDTH - 1, top + row_header + CELL_HEIGHT - 1),
                outline=color,
                width=2,
            )
            draw.text((left + 4, top + row_header + 4), str(col), fill=(0, 0, 0), font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(output_path)


def build_atlas(poses: dict[str, Pose]) -> tuple[Image.Image, list[tuple[str, int]]]:
    row_defs: list[tuple[str, int]] = [
        ("idle", 6),
        ("running-right", 8),
        ("running-left", 8),
        ("waving", 4),
        ("jumping", 5),
        ("failed", 8),
        ("waiting", 6),
        ("running", 6),
        ("review", 6),
    ]
    frames: dict[str, list[Placement]] = {
        "idle": [
            Placement("basic", scale=0.95, offset_y=2),
            Placement("basic", scale=0.96, offset_y=0),
            Placement("basic", scale=0.95, offset_y=-2),
            Placement("basic", scale=0.96, offset_y=0),
            Placement("basic", scale=0.95, offset_y=2),
            Placement("basic", scale=0.96, offset_y=0),
        ],
        "running-right": [
            Placement("one_leg", scale=0.90, rotate=-4, offset_x=-2, offset_y=4),
            Placement("fire", scale=0.92, rotate=-2, offset_x=3, offset_y=1),
            Placement("one_leg", scale=0.90, rotate=1, offset_x=2, offset_y=5),
            Placement("fire", scale=0.91, rotate=2, offset_x=5, offset_y=3),
            Placement("one_leg", scale=0.90, rotate=4, offset_x=1, offset_y=4),
            Placement("fire", scale=0.92, rotate=-2, offset_x=4, offset_y=1),
            Placement("one_leg", scale=0.90, rotate=-1, offset_x=2, offset_y=6),
            Placement("fire", scale=0.91, rotate=2, offset_x=5, offset_y=3),
        ],
        "running-left": [
            Placement("one_leg", scale=0.90, rotate=4, offset_x=2, offset_y=4, mirror=True),
            Placement("fire", scale=0.92, rotate=2, offset_x=-3, offset_y=1, mirror=True),
            Placement("one_leg", scale=0.90, rotate=-1, offset_x=-2, offset_y=5, mirror=True),
            Placement("fire", scale=0.91, rotate=-2, offset_x=-5, offset_y=3, mirror=True),
            Placement("one_leg", scale=0.90, rotate=-4, offset_x=-1, offset_y=4, mirror=True),
            Placement("fire", scale=0.92, rotate=2, offset_x=-4, offset_y=1, mirror=True),
            Placement("one_leg", scale=0.90, rotate=1, offset_x=-2, offset_y=6, mirror=True),
            Placement("fire", scale=0.91, rotate=-2, offset_x=-5, offset_y=3, mirror=True),
        ],
        "waving": [
            Placement("basic", scale=0.92, offset_y=4),
            Placement("manse", scale=0.91, offset_y=2),
            Placement("clap", scale=0.90, rotate=-1, offset_y=2),
            Placement("manse", scale=0.91, rotate=2, offset_y=3),
        ],
        "jumping": [
            Placement("basic", scale=0.90, offset_y=12),
            Placement("superman", scale=0.89, rotate=-4, offset_y=-2),
            Placement("party", scale=0.90, rotate=-5, offset_y=-14),
            Placement("superman", scale=0.89, rotate=3, offset_y=-4),
            Placement("basic", scale=0.90, offset_y=9),
        ],
        "failed": [
            Placement("panic", scale=0.78, offset_y=6),
            Placement("coffee", scale=0.90, rotate=3, offset_y=2),
            Placement("panic", scale=0.78, rotate=-2, offset_y=8),
            Placement("coffee", scale=0.90, rotate=-3, offset_y=4),
            Placement("panic", scale=0.78, offset_y=7),
            Placement("coffee", scale=0.90, rotate=3, offset_y=3),
            Placement("panic", scale=0.78, rotate=-2, offset_y=9),
            Placement("coffee", scale=0.90, rotate=-3, offset_y=4),
        ],
        "waiting": [
            Placement("coffee", scale=0.88, offset_y=4),
            Placement("coffee", scale=0.89, offset_y=5),
            Placement("coffee", scale=0.88, rotate=1, offset_y=2),
            Placement("coffee", scale=0.89, rotate=-1, offset_y=4),
            Placement("coffee", scale=0.88, offset_y=4),
            Placement("coffee", scale=0.89, offset_y=5),
        ],
        "running": [
            Placement("coding", scale=0.93, offset_y=5),
            Placement("coding", scale=0.94, rotate=-1, offset_y=4),
            Placement("coding", scale=0.93, rotate=1, offset_y=6),
            Placement("coding", scale=0.94, rotate=1, offset_y=4),
            Placement("coding", scale=0.93, offset_y=5),
            Placement("coding", scale=0.93, rotate=-1, offset_y=6),
        ],
        "review": [
            Placement("coding", scale=0.90, offset_y=7),
            Placement("coding", scale=0.91, rotate=-2, offset_y=6),
            Placement("coding", scale=0.90, rotate=1, offset_y=5),
            Placement("coding", scale=0.91, rotate=2, offset_y=6),
            Placement("coding", scale=0.90, rotate=-1, offset_y=5),
            Placement("coding", scale=0.90, offset_y=7),
        ],
    }

    atlas = Image.new("RGBA", ATLAS_SIZE, (255, 255, 255, 0))
    for row_index, (state, frame_count) in enumerate(row_defs):
        for column, placement in enumerate(frames[state]):
            cell = fit_into_cell(
                poses[placement.pose].image,
                scale=placement.scale,
                rotate=placement.rotate,
                offset_x=placement.offset_x,
                offset_y=placement.offset_y,
                mirror=placement.mirror,
            )
            atlas.alpha_composite(cell, (column * CELL_WIDTH, row_index * CELL_HEIGHT))
        if len(frames[state]) != frame_count:
            raise ValueError(f"{state} expected {frame_count} frames, got {len(frames[state])}")
    return atlas, row_defs


def load_poses(source_dir: Path) -> dict[str, Pose]:
    sheet = Image.open(source_dir / "planet_resource.png").convert("RGBA")
    poses = {
        "basic": load_transparent(source_dir / "기본 행성.png"),
        "manse": load_transparent(source_dir / "만세하는 행성.png"),
        "superman": load_transparent(source_dir / "슈퍼맨 포즈 행성 2.png"),
        "coffee": load_transparent(source_dir / "커피 수혈중인 행성.png"),
        "coding": load_transparent(source_dir / "프로그래밍을 하는 행성.png"),
        "one_leg": load_transparent(source_dir / "한쪽 다리를 든 행성.png"),
        "fire": load_sheet_pose(sheet, (430, 70, 725, 430)),
        "clap": load_sheet_pose(sheet, (1080, 55, 1405, 430)),
        "panic": load_sheet_pose(sheet, (1760, 55, 2210, 440)),
        "party": load_sheet_pose(sheet, (1820, 590, 2205, 1010)),
    }
    return {name: Pose(name, image) for name, image in poses.items()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--pet-dir", required=True, type=Path)
    parser.add_argument("--preview-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    poses = load_poses(args.source_dir)
    atlas, row_defs = build_atlas(poses)

    args.pet_dir.mkdir(parents=True, exist_ok=True)
    args.preview_dir.mkdir(parents=True, exist_ok=True)

    atlas.save(args.pet_dir / "spritesheet.webp", format="WEBP", lossless=True)
    draw_pose_preview(poses, args.preview_dir / "source-poses.png")
    build_contact_sheet(atlas, row_defs, args.preview_dir / "contact-sheet.png")

    print(f"wrote {args.pet_dir / 'spritesheet.webp'}")
    print(f"wrote {args.preview_dir / 'contact-sheet.png'}")
    print(f"wrote {args.preview_dir / 'source-poses.png'}")


if __name__ == "__main__":
    main()
