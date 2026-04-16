# pylint: disable=too-many-ancestors
from typing import Any, List, Dict

import numpy as np
import pandas as pd
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema


class ArrayInput(np.ndarray):
    """Pydantic compatible data type for numpy ndarray input."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(cls.validate)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema, handler):
        return {"type": "array", "items": {}}

    @classmethod
    def validate(cls, value: List) -> np.ndarray:
        # Transform input to ndarray
        return np.array(value)


class ArrayOutput(np.ndarray):
    """Pydantic compatible data type for numpy ndarray output."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(cls.validate)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema, handler):
        return {"type": "array", "items": {}}

    @classmethod
    def validate(cls, value: np.ndarray) -> List:
        # Transform ndarray to list for output
        return value.tolist()


class DataFrameInput(pd.DataFrame):
    """Pydantic compatible data type for pandas DataFrame input."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(cls.validate)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema, handler):
        return {"type": "object"}

    @classmethod
    def validate(cls, value: Dict[str, Any]) -> pd.DataFrame:
        # Transform input to DataFrame
        return pd.DataFrame.from_dict(value)


class DataFrameOutput(pd.DataFrame):
    """Pydantic compatible data type for pandas DataFrame output."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(cls.validate)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema, handler):
        return {"type": "object"}

    @classmethod
    def validate(cls, value: pd.DataFrame) -> Dict[str, Any]:
        # Transform DataFrame to dict
        return value.to_dict()
