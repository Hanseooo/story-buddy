import pytest
from pydantic import ValidationError

from contracts.job_state import SceneCaption


def test_scene_caption_accepts_valid_shape():
    result = SceneCaption.model_validate({"caption": "A dog runs through a sunny field."})
    assert result.caption == "A dog runs through a sunny field."


def test_scene_caption_rejects_missing_field():
    with pytest.raises(ValidationError):
        SceneCaption.model_validate({})
