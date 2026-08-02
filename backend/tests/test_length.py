from app.config import MAX_STORY_WORDS, MIN_STORY_WORDS
from app.length import clamp_story, word_count


def _words(n: int) -> str:
    return " ".join(f"w{i}" for i in range(n))


def test_under_cap_returned_unchanged():
    text = _words(10)
    result, truncated = clamp_story(text)
    assert result == text
    assert truncated is False


def test_exactly_max_words_unchanged():
    text = _words(MAX_STORY_WORDS)
    result, truncated = clamp_story(text)
    assert result == text
    assert truncated is False
    assert word_count(result) == MAX_STORY_WORDS


def test_over_cap_with_blank_line_in_range_cuts_at_paragraph():
    # Two paragraphs; the first ends well past the floor (half of MAX_STORY_WORDS).
    first_paragraph = _words(600)
    second_paragraph = _words(300)
    text = f"{first_paragraph}\n\n{second_paragraph}"

    result, truncated = clamp_story(text)

    assert truncated is True
    assert result == first_paragraph
    assert word_count(result) == 600


def test_over_cap_no_blank_line_sentence_punctuation_present_cuts_at_sentence():
    # One long paragraph, sentences long enough that the last sentence-end before
    # the cap keeps at least the floor (400 words).
    sentence_a = _words(600) + "."
    sentence_b = _words(300) + "."
    text = f"{sentence_a} {sentence_b}"

    result, truncated = clamp_story(text)

    assert truncated is True
    assert result == sentence_a
    assert result.endswith(".")


def test_floor_guard_fires_when_blank_line_is_too_early():
    # Blank line at word 10 — a paragraph cut there would keep far less than the
    # floor (400 words), so it must fall through to the sentence/hard cut instead.
    early_paragraph = _words(10)
    rest = _words(1000)  # no further blank line, no punctuation
    text = f"{early_paragraph}\n\n{rest}"

    result, truncated = clamp_story(text)

    assert truncated is True
    assert word_count(result) == MAX_STORY_WORDS
    assert "\n\n" not in result


def test_over_cap_no_punctuation_no_blank_lines_hard_cuts_at_max():
    text = _words(1000)  # one run-on, no ".", no "\n\n"
    result, truncated = clamp_story(text)
    assert truncated is True
    assert word_count(result) == MAX_STORY_WORDS


def test_crlf_paragraph_break_is_treated_as_paragraph():
    first_paragraph = _words(600)
    second_paragraph = _words(300)
    text = f"{first_paragraph}\r\n\r\n{second_paragraph}"

    result, truncated = clamp_story(text)

    assert truncated is True
    assert word_count(result) == 600
    assert "\r" not in result


def test_paragraph_cut_never_runs_on_a_rejoined_string():
    # If clamp_story rejoined " ".join(words[:cap]) instead of slicing the
    # original string, this \n\n would already be destroyed before the paragraph
    # rule ever sees it. Assert the actual blank line survives into the result.
    first_paragraph = _words(600)
    second_paragraph = _words(300)
    text = f"{first_paragraph}\n\n{second_paragraph}"

    result, _ = clamp_story(text)

    assert "\n\n" not in result  # the cut is *at* the boundary, not straddling it
    assert result == first_paragraph


def test_word_count_counts_whitespace_separated_tokens():
    assert word_count("one two three") == 3
    assert word_count("") == 0
    assert word_count("   ") == 0


def test_min_story_words_is_reachable_via_word_count():
    assert word_count(_words(MIN_STORY_WORDS)) == MIN_STORY_WORDS
