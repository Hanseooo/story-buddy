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
