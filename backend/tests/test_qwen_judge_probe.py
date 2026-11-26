from scripts.qwen_judge_probe import ModelResult, exit_code

LISTED = {"Qwen/Qwen3.5-9B", "seed2_checkpoint140"}


def test_both_models_listed_and_parsed_passes():
    results = [
        ModelResult("Qwen/Qwen3.5-9B", 12.0, True, ""),
        ModelResult("seed2_checkpoint140", 30.0, True, ""),
    ]
    assert exit_code(LISTED, results) == 0


def test_an_unparsed_answer_or_a_missing_adapter_fails():
    parsed = [
        ModelResult("Qwen/Qwen3.5-9B", 12.0, True, ""),
        ModelResult("seed2_checkpoint140", 30.0, True, ""),
    ]
    unparsed = [parsed[0], ModelResult("seed2_checkpoint140", 30.0, False, "LengthFinishReasonError")]
    assert exit_code(LISTED, unparsed) == 1
    assert exit_code({"Qwen/Qwen3.5-9B"}, parsed) == 1


def test_a_timed_out_model_is_reported_not_parsed_and_the_probe_goes_on():
    import httpx
    from openai import OpenAI

    from scripts.qwen_judge_probe import _probe

    def hang(request):
        raise httpx.ReadTimeout("timed out", request=request)

    client = OpenAI(
        base_url="http://qwen.test.invalid/v1", api_key="k", timeout=5.0, max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(hang)),
    )

    result = _probe(client, "seed2_checkpoint140", [{"type": "text", "text": "x"}])

    assert (result.model, result.parsed, result.detail) == ("seed2_checkpoint140", False, "TIMEOUT after 5s")
    assert exit_code(LISTED, [ModelResult("Qwen/Qwen3.5-9B", 12.0, True, ""), result]) == 1
