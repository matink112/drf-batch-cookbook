"""12. derived_from a model column that is not on the serializer."""

from __future__ import annotations

from _support import client
from saas.models import Subscription, Workspace

URL = "/subscriptions/batch/"


def seed() -> None:
    small = Workspace.objects.create(id=1, name="Small team")
    big = Workspace.objects.create(id=2, name="Big team")
    Subscription.objects.create(id=1, workspace=small, plan_code="starter", seats=3)
    Subscription.objects.create(id=2, workspace=big, plan_code="team", seats=20)


def walk() -> None:
    api = client()

    # --8<-- [start:patch]
    response = api.patch(URL, [{"id": 1, "seats": 8}, {"id": 2, "seats": 40}])
    assert response.status_code == 400
    assert response.json() == [{"seats": ["The starter plan allows 5 seats."]}, {}]
    # --8<-- [end:patch]

    # --8<-- [start:plan_ignored]
    # plan_code is not a serializer field: DRF drops it from the row, and the
    # stored plan still decides.
    response = api.patch(URL, [{"id": 1, "seats": 8, "plan_code": "team"}])
    assert response.status_code == 400
    assert Subscription.objects.get(id=1).plan_code == "starter"
    # --8<-- [end:plan_ignored]

    # --8<-- [start:post]
    response = api.post(URL, [{"seats": 1}])
    assert response.status_code == 405  # batch_actions = ("update",)
    # --8<-- [end:post]
