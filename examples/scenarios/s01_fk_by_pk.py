"""1. FK by primary key: BatchRelatedField with no options."""

from __future__ import annotations

from _support import client, queries, reads
from library.models import Author, Book

URL = "/books/batch/"
TOLKIEN = "6f1c4c1e-3b51-4d0a-9a43-0c7d1b5a2e01"
LE_GUIN = "0b9f9d3e-8a7e-4c1f-b0a5-5d2e7c6f4a02"


def seed() -> None:
    Author.objects.create(id=TOLKIEN, name="J. R. R. Tolkien")
    Author.objects.create(id=LE_GUIN, name="Ursula K. Le Guin")


def walk() -> None:
    api = client()

    # --8<-- [start:post]
    with queries() as captured:
        response = api.post(
            URL,
            [
                {"author": TOLKIEN, "title": "The Hobbit", "pages": 310},
                {"author": LE_GUIN.upper(), "title": "Earthsea", "pages": 205},
            ],
        )
    assert response.status_code == 201
    assert response.json() == {"count": 2}
    assert reads(captured, "library_author") == 1  # both authors, one query
    # --8<-- [end:post]

    # --8<-- [start:miss]
    response = api.post(
        URL,
        [
            {"author": TOLKIEN, "title": "Silmarillion", "pages": 365},
            {
                "author": "11111111-2222-4333-8444-555555555555",
                "title": "?",
                "pages": 1,
            },
        ],
    )
    assert response.status_code == 400
    assert response.json() == [
        {},
        {"author": ["Object '11111111-2222-4333-8444-555555555555' not found."]},
    ]
    # --8<-- [end:miss]

    # --8<-- [start:malformed]
    response = api.post(URL, [{"author": "tolkien", "title": "?", "pages": 1}])
    assert response.status_code == 400
    assert response.json() == [
        {"author": ["Invalid value for 'author': expected a UUID, got str."]}
    ]
    # --8<-- [end:malformed]

    # --8<-- [start:patch]
    hobbit = Book.objects.get(title="The Hobbit")
    with queries() as captured:
        response = api.patch(URL, [{"id": hobbit.pk, "pages": 320}])
    assert response.status_code == 200
    assert reads(captured, "library_author") == 0  # author not sent: no lookup
    # --8<-- [end:patch]

    # --8<-- [start:delete]
    response = api.delete(URL, list(Book.objects.values_list("pk", flat=True)))
    assert response.status_code == 200
    assert response.json() == {"count": 2}
    # --8<-- [end:delete]
