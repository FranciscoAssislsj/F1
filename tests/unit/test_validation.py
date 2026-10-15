import pandas as pd
import pytest

from f1.core.exceptions import SchemaValidationError
from f1.core.schemas import SCHEMAS
from f1.transformation.entities import transform
from f1.validation.checks import validate
from tests.conftest import load_fixture


@pytest.fixture
def stints() -> pd.DataFrame:
    return transform("stints", load_fixture("stints.json"))[0]


def test_valid_frame_passes(stints: pd.DataFrame) -> None:
    validate(stints, SCHEMAS["stints"])


def test_missing_column_fails(stints: pd.DataFrame) -> None:
    with pytest.raises(SchemaValidationError, match="colunas ausentes"):
        validate(stints.drop(columns=["compound"]), SCHEMAS["stints"])


def test_wrong_dtype_fails(stints: pd.DataFrame) -> None:
    broken = stints.assign(lap_start=stints.lap_start.astype("Float64"))
    with pytest.raises(SchemaValidationError, match="tipo inesperado em lap_start"):
        validate(broken, SCHEMAS["stints"])


def test_null_key_fails(stints: pd.DataFrame) -> None:
    broken = stints.copy()
    broken.loc[0, "driver_number"] = pd.NA
    with pytest.raises(SchemaValidationError, match="chave com nulos"):
        validate(broken, SCHEMAS["stints"])


def test_duplicate_key_fails(stints: pd.DataFrame) -> None:
    with pytest.raises(SchemaValidationError, match="chave duplicada"):
        validate(pd.concat([stints, stints]), SCHEMAS["stints"])
