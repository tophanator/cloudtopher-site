import os
import glob
import re
from datetime import datetime
from collections import defaultdict

# Config
POSTS_DIR = "posts"
BLOG_TEMPLATE = "blog-template.html"
BLOG_OUTPUT = "blog.html"
RSS_OUTPUT = "feed.xml"
SITE_BASE_URL = "https://cloudtopher.com"
AUTHOR_NAME = "Chris"
POST_TEMPLATE = "blog-post-template.html"
POSTS_OUTPUT_DIR = "blog"  # folder where individual post pages will go
ARCHIVE_TEMPLATE = "blog-archive-template.html"
ARCHIVE_OUTPUT_DIR = "blog/archive"
TAG_TEMPLATE = "blog-tag-template.html"
TAG_OUTPUT_DIR = "blog/tag"


def parse_post(path):
    """Parse a post file into metadata + HTML body."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    parts = text.split("---")
    if len(parts) < 3:
        raise ValueError(f"Post {path} missing front matter delimiters '---'")

    meta_block = parts[1].strip()
    body_html = "---".join(parts[2:]).strip()

    meta = {}
    for line in meta_block.splitlines():
        if not line.strip():
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()

    # Required fields
    title = meta.get("title")
    date_str = meta.get("date")
    slug = meta.get("slug")

    if not title or not date_str:
        raise ValueError(f"Post {path} missing title or date")

    if not slug:
        # derive slug from filename if not provided
        basename = os.path.basename(path)
        slug = os.path.splitext(basename)[0]

    # tags are optional
    tags_raw = meta.get("tags", "")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    # parse date
    date = datetime.fromisoformat(date_str)

    return {
        "title": title,
        "date": date,
        "date_str": date_str,
        "slug": slug,
        "tags": tags,
        "body_html": body_html,
    }

def load_posts():
    files = sorted(glob.glob(os.path.join(POSTS_DIR, "*.html")))
    posts = [parse_post(p) for p in files]
    # newest first
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def slugify_tag(tag):
    # simple slug: lowercase, spaces->-, drop non-alphanum/- 
    tag = tag.lower().strip()
    tag = re.sub(r"\s+", "-", tag)
    tag = re.sub(r"[^a-z0-9\-]", "", tag)
    return tag

def render_tag_links(tags):
    if not tags:
        return ""
    parts = []
    for tag in tags:
        slug = slugify_tag(tag)
        href = f"/blog/tag/{slug}.html"
        parts.append(f'<a href="{href}">{tag}</a>')
    return ", ".join(parts)

def render_post_card(post):
    """HTML for a post on the blog index / archives / tag pages."""
    date_display = post["date"].strftime("%b %d, %Y")
    permalink = f"/blog/{post['slug']}.html"
    tags_html = render_tag_links(post["tags"])  # assuming you already have this helper

    # Use preview instead of full body
    preview_html = build_preview_html(post["body_html"], max_words=80)

    return f"""
    <article id="post-{post['slug']}" class="content-section">
      <div class="content-header">
        <div class="content-title">{post['title']}</div>
        <div class="content-date">{date_display}</div>
      </div>
      <div class="content-body">
        {preview_html}

        <p class="blog-meta">
          Posted by {AUTHOR_NAME}
          {'&bull; Tags: ' + tags_html if tags_html else ''}
          &bull; <a class="read-more-btn" href="{permalink}">Read More &raquo;</a>
        </p>
      </div>
    </article>
    """

def render_recent_posts(posts, limit=5, current_slug=None):
    items = []
    for i, post in enumerate(posts[:limit], start=1):
        permalink = f"/blog/{post['slug']}.html"
        # Add 'current' class if this is the active post
        current_class = " current" if current_slug and post["slug"] == current_slug else ""
        items.append(f"""
        <a href="{permalink}">
          <div class="side-item{current_class}">
            <div class="side-icon">{i:02d}</div>
            <div class="side-text">
              <div class="side-text-title">{post['title']}</div>
              <div class="side-text-sub">{post['date'].strftime('%b %d, %Y')}</div>
            </div>
          </div>
        </a>
        """)
    return "\n".join(items)

def render_archives(posts):
    groups = defaultdict(list)
    for post in posts:
        key = (post["date"].year, post["date"].month)
        groups[key].append(post)

    keys_sorted = sorted(groups.keys(), reverse=True)

    items = []
    for year, month in keys_sorted:
        month_name = datetime(year, month, 1).strftime("%B")
        out_name = f"archive-{year}-{month:02d}.html"
        permalink = f"/blog/archive/{out_name}"

        items.append(f"""
        <a href="{permalink}">
          <div class="side-item">
            <div class="side-icon">{str(year)[-2:]}</div>
            <div class="side-text">
              <div class="side-text-title">{month_name} {year}</div>
              <div class="side-text-sub">{len(groups[(year, month)])} post(s)</div>
            </div>
          </div>
        </a>
        """)

    return "\n".join(items)

def build_preview_html(body_html, max_words=80):
    """
    Create a short preview from the post body.

    - Strips HTML tags to count words
    - If under the limit, returns the original HTML
    - If over, returns a simple <p> with truncated text + "..."
    """
    # Strip HTML tags for counting
    text = re.sub(r"<[^>]+>", "", body_html)
    words = text.split()

    if len(words) <= max_words:
        # Short post, just show the full body on index/archives
        return body_html

    preview_words = words[:max_words]
    preview_text = " ".join(preview_words) + "..."
    return f"<p>{preview_text}</p>"


def build_blog_html(posts):
    with open(BLOG_TEMPLATE, "r", encoding="utf-8") as f:
        template = f.read()

    posts_html = "\n".join(render_post_card(p) for p in posts)
    recent_html = render_recent_posts(posts, current_slug=None)
    archives_html = render_archives(posts)

    output = (
        template
        .replace("<!-- POSTS_GO_HERE -->", posts_html)
        .replace("<!-- RECENT_POSTS_GO_HERE -->", recent_html)
        .replace("<!-- ARCHIVES_GO_HERE -->", archives_html)
    )

    with open(BLOG_OUTPUT, "w", encoding="utf-8") as f:
        f.write(output)

def build_post_pages(posts):
    """Generate individual HTML pages for each blog post."""
    os.makedirs(POSTS_OUTPUT_DIR, exist_ok=True)

    with open(POST_TEMPLATE, "r", encoding="utf-8") as f:
        base_template = f.read()

    # Sidebar HTML is shared, but we’ll recompute for each post to highlight current
    archives_html_all = render_archives(posts)

    for idx, post in enumerate(posts):
        date_display = post["date"].strftime("%b %d, %Y")
        tags_html_links = render_tag_links(post["tags"])
        if tags_html_links:
          tags_html = f"&bull; Tags: {tags_html_links} "
        else:
          tags_html = ""

        recent_html = render_recent_posts(posts, current_slug=post["slug"])
        prev_next_html = build_prev_next_nav(posts, idx)

        html = (
            base_template
            .replace("{{POST_TITLE}}", post["title"])
            .replace("{{POST_DATE}}", date_display)
            .replace("{{POST_BODY}}", post["body_html"])
            .replace("{{AUTHOR_NAME}}", AUTHOR_NAME)
            .replace("{{POST_TAGS}}", tags_html)
            .replace("{{PREV_NEXT_NAV}}", prev_next_html)
            .replace("<!-- RECENT_POSTS_GO_HERE -->", recent_html)
            .replace("<!-- ARCHIVES_GO_HERE -->", archives_html_all)
        )

        out_path = os.path.join(POSTS_OUTPUT_DIR, f"{post['slug']}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Wrote {out_path}")

def build_archive_pages(posts):
    """Generate monthly archive pages."""
    os.makedirs(ARCHIVE_OUTPUT_DIR, exist_ok=True)

    # Group posts by year/month
    groups = defaultdict(list)
    for post in posts:
        key = (post["date"].year, post["date"].month)
        groups[key].append(post)

    with open(ARCHIVE_TEMPLATE, "r", encoding="utf-8") as f:
        base_template = f.read()

    # Shared sidebar content
    recent_html_all = render_recent_posts(posts, current_slug=None)
    archives_html_all = render_archives(posts)

    for (year, month), group_posts in groups.items():
        month_name = datetime(year, month, 1).strftime("%B")
        page_title = f"Archive: {month_name} {year}"
        page_subtitle = f"{len(group_posts)} post(s)"
        page_description = f"Posts from {month_name} {year}."

        posts_html = "\n".join(render_post_card(p) for p in group_posts)

        html = (
            base_template
            .replace("{{PAGE_TITLE}}", page_title)
            .replace("{{PAGE_SUBTITLE}}", page_subtitle)
            .replace("{{PAGE_DESCRIPTION}}", page_description)
            .replace("<!-- POSTS_GO_HERE -->", posts_html)
            .replace("<!-- RECENT_POSTS_GO_HERE -->", recent_html_all)
            .replace("<!-- ARCHIVES_GO_HERE -->", archives_html_all)
        )

        out_name = f"archive-{year}-{month:02d}.html"
        out_path = os.path.join(ARCHIVE_OUTPUT_DIR, out_name)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Wrote {out_path}")


def build_tag_pages(posts):
    """Generate pages listing posts per tag."""
    os.makedirs(TAG_OUTPUT_DIR, exist_ok=True)

    # Collect posts by tag
    tag_map = defaultdict(list)
    for post in posts:
        for tag in post["tags"]:
            tag_map[tag].append(post)

    if not tag_map:
        return

    with open(TAG_TEMPLATE, "r", encoding="utf-8") as f:
        base_template = f.read()

    # Shared sidebar
    recent_html_all = render_recent_posts(posts, current_slug=None)
    archives_html_all = render_archives(posts)

    for tag, tag_posts in tag_map.items():
        tag_slug = slugify_tag(tag)
        page_title = f"Tag: {tag}"
        page_subtitle = f"{len(tag_posts)} post(s)"
        page_description = f"Posts tagged with “{tag}”."

        posts_html = "\n".join(render_post_card(p) for p in tag_posts)

        html = (
            base_template
            .replace("{{PAGE_TITLE}}", page_title)
            .replace("{{PAGE_SUBTITLE}}", page_subtitle)
            .replace("{{PAGE_DESCRIPTION}}", page_description)
            .replace("<!-- POSTS_GO_HERE -->", posts_html)
            .replace("<!-- RECENT_POSTS_GO_HERE -->", recent_html_all)
            .replace("<!-- ARCHIVES_GO_HERE -->", archives_html_all)
        )

        out_path = os.path.join(TAG_OUTPUT_DIR, f"{tag_slug}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Wrote {out_path}")


def build_prev_next_nav(posts, index):
    """Return HTML with prev/next links for the post at posts[index]."""
    prev_html = ""
    next_html = ""

    # Newest post is index 0
    if index < len(posts) - 1:
        newer = posts[index - 1] if index > 0 else None
        older = posts[index + 1]
    else:
        newer = posts[index - 1] if index > 0 else None
        older = None

    # Note: because posts are sorted newest->oldest, "older" = index+1
    if older:
        older_link = f"/blog/{older['slug']}.html"
        prev_html = f'<a href="{older_link}">&laquo; Previous Post: {older["title"]}</a>'

    if newer:
        newer_link = f"/blog/{newer['slug']}.html"
        next_html = f'<a href="{newer_link}">Next Post: {newer["title"]} &raquo;</a>'

    if prev_html and next_html:
        return prev_html + " &nbsp;|&nbsp; " + next_html
    elif prev_html:
        return prev_html
    elif next_html:
        return next_html
    else:
        return ""


def build_rss(posts):
    """Generate a very simple RSS 2.0 feed."""
    if not posts:
        return

    last_build = posts[0]["date"].strftime("%a, %d %b %Y %H:%M:%S +0000")
    items_xml = []
    for post in posts:
        pub_date = post["date"].strftime("%a, %d %b %Y %H:%M:%S +0000")
        link = f"{SITE_BASE_URL}/blog/{post['slug']}.html"

        description = post["body_html"].replace("\n", " ")

        items_xml.append(f"""
        <item>
          <title>{post['title']}</title>
          <link>{link}</link>
          <guid>{link}</guid>
          <pubDate>{pub_date}</pubDate>
          <description><![CDATA[{description}]]></description>
        </item>
        """)

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Cloud Resume Dev Log</title>
        <link>{SITE_BASE_URL}/blog.html</link>
        <description>Updates and notes from building my AWS Cloud Resume.</description>
        <lastBuildDate>{last_build}</lastBuildDate>
        {''.join(items_xml)}
      </channel>
    </rss>
    """

    with open(RSS_OUTPUT, "w", encoding="utf-8") as f:
        f.write(rss.strip())

    print(f"Wrote {RSS_OUTPUT}.")

def main():
    posts = load_posts()
    build_blog_html(posts)
    build_post_pages(posts)
    build_archive_pages(posts)
    build_tag_pages(posts)
    build_rss(posts)


if __name__ == "__main__":
    main()
