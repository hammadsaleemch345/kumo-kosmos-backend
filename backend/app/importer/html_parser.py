import re
from dataclasses import dataclass

_DYNAMIC_BLOCK_RE = re.compile(
    r'<div class="dynamic-content-block"[^>]*data-dynamic-audiences="([^"]*)"[^>]*>'
)
_PAYWALL_JUMP_RE = re.compile(r'<div class="paywall-jump"[^>]*>\s*</div>')
_MATCH_WRAPPER_RE = re.compile(r'^<div class="dynamic-content-match"[^>]*>')


@dataclass
class TierSplit:
    """The three audience-gated sections of a post, as found in the raw Substack export HTML."""

    non_sub_html: str
    free_sub_html: str
    paid_html: str
    paid_marker: str  # "dynamic_block", "paywall_jump", or "none"


def _find_balanced_div_end(html: str, content_start: int) -> int:
    """Given an index just past a <div ...> opening tag, return the index where its matching </div> starts.

    Substack's export nests plain <div> tags inside these audience blocks (paragraphs, dividers, etc.),
    so a naive regex for the next </div> would cut content off at the first nested divider instead of
    the actual end of the section. This walks tag-by-tag tracking depth to find the real boundary.
    """
    depth = 1
    i = content_start
    while depth > 0:
        next_open = html.find("<div", i)
        next_close = html.find("</div>", i)
        if next_close == -1:
            raise ValueError("Unbalanced <div> in post HTML, cannot locate section boundary")
        if next_open != -1 and next_open < next_close:
            depth += 1
            i = next_open + 4
        else:
            depth -= 1
            i = next_close + len("</div>")
    return i - len("</div>")


def _unwrap_match_div(content: str) -> str:
    """Strip Substack's inner `dynamic-content-match` wrapper div, which carries no meaning of its own."""
    wrapper_match = _MATCH_WRAPPER_RE.match(content)
    if wrapper_match is None:
        return content
    inner_end = _find_balanced_div_end(content, wrapper_match.end())
    return content[wrapper_match.end() : inner_end]


def _extract_audience_block(html: str, audience: str) -> str:
    for match in _DYNAMIC_BLOCK_RE.finditer(html):
        audiences = [a.strip() for a in match.group(1).split(",")]
        if audience in audiences:
            content_end = _find_balanced_div_end(html, match.end())
            return _unwrap_match_div(html[match.end() : content_end])
    return ""


def parse_tiers(html: str) -> TierSplit:
    """Detect the non-subscriber / free-subscriber / paid-subscriber split in one post's raw HTML.

    Two paid-content patterns are both live in the actual export (confirmed by inspection, not assumed):
    an explicit `paid_sub` dynamic-content-block, or a bare `paywall-jump` marker after which everything
    to the end of the post is paid. Posts with neither (polls, Q&A, free-only oneshots) have no paid tier.
    """
    non_sub_html = _extract_audience_block(html, "non_sub")
    free_sub_html = _extract_audience_block(html, "free_sub")

    for match in _DYNAMIC_BLOCK_RE.finditer(html):
        audiences = [a.strip() for a in match.group(1).split(",")]
        if "paid_sub" in audiences:
            content_end = _find_balanced_div_end(html, match.end())
            paid_html = _unwrap_match_div(html[match.end() : content_end])
            return TierSplit(non_sub_html, free_sub_html, paid_html, "dynamic_block")

    jump_match = _PAYWALL_JUMP_RE.search(html)
    if jump_match:
        return TierSplit(non_sub_html, free_sub_html, html[jump_match.end() :], "paywall_jump")

    return TierSplit(non_sub_html, free_sub_html, "", "none")
