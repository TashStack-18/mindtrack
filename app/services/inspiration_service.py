"""
Daily inspirational photo for the dashboard.

The photo is picked from a fixed, curated list using the calendar date, so it
stays the same all day (across refreshes) and changes the next day. No
randomness, database writes or network requests are involved.

The server picks using its own date; static/js/daily_photo.js re-applies the
same formula with the visitor's local date, so the switch happens at the
user's local midnight. Both use "days since 0001-01-01" (Python's
date.toordinal()), modulo the number of images.
"""
from datetime import date
from typing import Optional

INSPIRATION_DIR = 'img/inspiration/'

# Bundled, optimised (720px) images. Order matters: it defines the rotation.
INSPIRATION_IMAGES = [
    'pink-roses-garden.jpg',
    'lavender-misty-hills.jpg',
    'golden-sea-sunset.jpg',
    'soft-blue-clouds.jpg',
    'lavender-field-sunrise.jpg',
    'calm-lake-reflection.jpg',
    'sunrise-above-clouds.jpg',
    'green-fern-morning.jpg',
    'pastel-sky-river-valley.jpg',
    'lilac-evening-sky.jpg',
    'misty-rolling-hills.jpg',
    'violet-sunset-clouds.jpg',
]

FALLBACK_IMAGE = 'pink-roses-garden.jpg'


def image_for_date(day: Optional[date] = None) -> str:
    """Return the static path (relative to /static) of the photo for a date."""
    day = day or date.today()
    return INSPIRATION_DIR + INSPIRATION_IMAGES[day.toordinal() % len(INSPIRATION_IMAGES)]


def all_image_paths():
    return [INSPIRATION_DIR + name for name in INSPIRATION_IMAGES]
