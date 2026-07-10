from pipeline.graph import build_graph


def test_stub_graph_runs_all_nodes_in_order(monkeypatch):
    monkeypatch.setattr("pipeline.analyze.caption_for", lambda text: "stub caption")
    monkeypatch.setattr(
        "pipeline.generate_scene.generate_and_store",
        lambda prompt, job_id: "stub/path.png",
    )

    app_graph = build_graph()
    initial_state = {
        "job_id": "test-job",
        "input_text": "A dog runs in a field.",
        "caption": None,
        "image_path": None,
        "stage": "queued",
    }
    result = app_graph.invoke(initial_state, config={"configurable": {"thread_id": "test-job"}})

    assert result["stage"] == "compose"


def test_stub_graph_full_run_with_real_call_points_mocked(monkeypatch):
    monkeypatch.setattr("pipeline.analyze.caption_for", lambda text: "stub caption")
    monkeypatch.setattr(
        "pipeline.generate_scene.generate_and_store",
        lambda prompt, job_id: "stub/path.png",
    )

    app_graph = build_graph()
    initial_state = {
        "job_id": "test-job-2",
        "input_text": "A dog runs in a field.",
        "caption": None,
        "image_path": None,
        "stage": "queued",
    }
    result = app_graph.invoke(initial_state, config={"configurable": {"thread_id": "test-job-2"}})

    assert result["stage"] == "compose"
    assert result["caption"] == "stub caption"
    assert result["image_path"] == "stub/path.png"
