import pytest
from django.db import transaction

from config import celery_app


def test_tasks_only_accept_json():
    conf = celery_app.conf
    assert conf.task_serializer == "json"
    assert conf.accept_content == ["json"]
    assert conf.task_acks_late is True
    assert conf.task_ignore_result is True


def test_broker_is_redis():
    assert celery_app.conf.broker_url.startswith("redis://")


@celery_app.task(name="tests.double_number")
def double_number(n: int) -> int:
    return n * 2


def test_tasks_run_eagerly_in_tests():
    assert double_number.delay(21).get() == 42


@celery_app.task(name="tests.fail_task")
def fail_task() -> None:
    raise ValueError("boom")


def test_eager_errors_propagate():
    with pytest.raises(ValueError, match="boom"):
        fail_task.delay()


@pytest.mark.django_db
def test_enqueue_waits_for_commit(django_capture_on_commit_callbacks):
    calls: list[int] = []
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        transaction.on_commit(lambda: calls.append(double_number.delay(2).get()))
        assert calls == []
    assert len(callbacks) == 1
    assert calls == [4]
