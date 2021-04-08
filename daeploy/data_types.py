# pylint: disable=too-many-ancestors
from typing import Any, List, Dict

import numpy as np
import pandas as pd


class ArrayInput(np.ndarray):
    """Pydantic compatible data type for numpy ndarray input."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="array", items={})

    @classmethod
    def validate(cls, value: List) -> np.ndarray:
        # Transform input to ndarray
        return np.array(value)


class ArrayOutput(np.ndarray):
    """Pydantic compatible data type for numpy ndarray output."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="array", items={})

    @classmethod
    def validate(cls, value: np.ndarray) -> List:
        # Transform ndarray to list for output
        return value.tolist()


class DataFrameInput(pd.DataFrame):
    """Pydantic compatible data type for pandas DataFrame input."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="object")

    @classmethod
    def validate(cls, value: Dict[str, Any]) -> pd.DataFrame:
        # Transform input to ndarray
        return pd.DataFrame.from_dict(value)


class DataFrameOutput(pd.DataFrame):
    """Pydantic compatible data type for pandas DataFrame output."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="object")

    @classmethod
    def validate(cls, value: pd.DataFrame) -> Dict[str, Any]:
        # Transform input to ndarray
        return value.to_dict()
