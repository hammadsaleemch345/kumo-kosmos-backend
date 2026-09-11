import zipfile
from dataclasses import dataclass

from sqlalchemy.orm import Session as DBSession

from app.importer.db_import import PostImportSummary, SubscriberImportSummary, import_posts, import_subscribers
from app.importer.posts_csv import parse_posts_csv
from app.importer.subscribers_csv import parse_subscribers_csv


@dataclass
class ImportResult:
    subscribers: SubscriberImportSummary
    posts: PostImportSummary


def run_substack_import(db: DBSession, zip_path: str) -> ImportResult:
    """Entry point for the real workflow: read directly from the ZIP the client exports from
    Substack, no live URL scraping (ruled out as unreliable, per the SOW).
    """
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()

        posts_csv_name = next((n for n in names if n.endswith("posts.csv")), None)
        if posts_csv_name is None:
            raise ValueError("posts.csv not found in export ZIP")
        post_rows = parse_posts_csv(archive.read(posts_csv_name).decode("utf-8"))

        subscriber_csv_name = next((n for n in names if "email_list" in n and n.endswith(".csv")), None)
        if subscriber_csv_name is None:
            raise ValueError("email_list*.csv not found in export ZIP")
        subscriber_rows = parse_subscribers_csv(archive.read(subscriber_csv_name).decode("utf-8"))

        html_by_post_id: dict[str, str] = {}
        slug_by_post_id: dict[str, str] = {}
        for name in names:
            if not name.endswith(".html") or "/posts/" not in f"/{name}":
                continue
            filename = name.rsplit("/", 1)[-1]
            post_id, _, rest = filename.partition(".")
            if not post_id.isdigit():
                continue
            html_by_post_id[post_id] = archive.read(name).decode("utf-8", errors="ignore")
            slug_by_post_id[post_id] = rest.removesuffix(".html")

    subscriber_summary = import_subscribers(db, subscriber_rows)
    post_summary = import_posts(db, post_rows, html_by_post_id, slug_by_post_id)
    return ImportResult(subscribers=subscriber_summary, posts=post_summary)


def run_subscriber_only_import(db: DBSession, csv_text: str) -> SubscriberImportSummary:
    """For re-running just the subscriber list on its own (e.g. Substack export, without the
    full ZIP) — posts only ever need importing once, but subscribers may need re-importing
    any time as a backup path if the client's current platform goes down.
    """
    subscriber_rows = parse_subscribers_csv(csv_text)
    return import_subscribers(db, subscriber_rows)
