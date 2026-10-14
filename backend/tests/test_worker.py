"""Exercise the same settings extraction that arq uses at startup."""

from arq.connections import RedisSettings
from arq.worker import get_kwargs

from app.corpus.tasks import WorkerSettings
from app.kernel.config import settings
from app.kernel.worker import startup


def test_corpus_worker_retains_connection_and_startup() -> None:
    options = get_kwargs(WorkerSettings)
    assert options["redis_settings"] == RedisSettings.from_dsn(settings.redis_url)
    assert options["on_startup"] is startup
    assert any(function.__name__ == "ingest_pdf" for function in options["functions"])
