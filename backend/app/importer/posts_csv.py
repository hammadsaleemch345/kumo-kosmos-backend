import csv
from dataclasses import dataclass
from io import StringIO

# Titles matching these are almost certainly not stories (polls, Q&A, announcements), but there's
# no tags column anywhere in the export to confirm this cleanly, so these are flagged for a human
# to confirm rather than silently excluded, per the SOW's "confirm before excluding" instruction.
_NON_STORY_TITLE_HINTS = ("poll", "vote", "voting", "q&a", "q & a", "announcement", "update", "discount")


@dataclass
class PostRow:
    post_id: str
    is_published: bool
    post_type: str
    audience: str
    title: str
    subtitle: str
    likely_story: bool  # False means the title suggests this isn't a story; needs human confirmation


def parse_posts_csv(csv_text: str) -> list[PostRow]:
    """Parse posts.csv, excluding type=page rows outright (confirmed static pages, safe to drop).

    Rows that survive still need a `likely_story` check before import, since there's no tags column
    to reliably separate stories from misc posts (polls, Q&A, announcements).
    """
    reader = csv.DictReader(StringIO(csv_text))
    rows = []
    for row in reader:
        if row["type"] == "page":
            continue
        title_lower = row["title"].lower()
        likely_story = not any(hint in title_lower for hint in _NON_STORY_TITLE_HINTS)
        rows.append(
            PostRow(
                post_id=row["post_id"],
                is_published=row["is_published"].strip().lower() == "true",
                post_type=row["type"],
                audience=row["audience"],
                title=row["title"],
                subtitle=row["subtitle"],
                likely_story=likely_story,
            )
        )
    return rows
