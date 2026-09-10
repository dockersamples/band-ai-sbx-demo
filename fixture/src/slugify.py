"""Turn arbitrary text into a URL slug.

Deliberately broken for the Repo Doctor demo: run scripts/reset-fixture.sh to
restore this exact content between runs.
"""


def slugify(text: str) -> str:
    return text.strip().lower().replace(" ", "-")
