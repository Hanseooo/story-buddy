from pipeline.graph import build_graph


def test_stub_graph_runs_all_nodes_in_order():
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
    assert result["caption"] is None
    assert result["image_path"] is None
