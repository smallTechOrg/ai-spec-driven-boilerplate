"""Boot path == run path: the app must import and construct the way `python -m src`
does (src/ on sys.path, bare imports)."""


def test_app_imports_and_has_routes():
    from api import create_app

    app = create_app()
    paths = set(app.openapi()["paths"].keys())
    assert "/health" in paths
    assert "/api/datasets" in paths
    assert "/api/analyses" in paths
    assert "/api/analyses/{analysis_id}" in paths


def test_uvicorn_target_importable():
    # `python -m src` runs uvicorn.run("api:app", ...). Confirm that target resolves.
    import importlib

    module = importlib.import_module("api")
    assert hasattr(module, "app")
