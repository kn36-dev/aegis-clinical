from unittest.mock import MagicMock

from aegis.indexing.pipeline import IndexingPipeline


def test_run_executes_pipeline_in_order():
    repository = MagicMock()
    builder = MagicMock()
    embedder = MagicMock()
    uploader = MagicMock()

    repository.list_all.return_value = ["record"]

    builder.build_many.return_value = ["representation"]

    embedder.embed_many.return_value = ["vector"]

    pipeline = IndexingPipeline(
        repository=repository,
        builder=builder,
        embedder=embedder,
        uploader=uploader,
    )

    pipeline.run()

    repository.list_all.assert_called_once()

    builder.build_many.assert_called_once_with(["record"])

    embedder.embed_many.assert_called_once_with(["representation"])

    uploader.upload_many.assert_called_once_with(["vector"])
