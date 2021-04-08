import logging
from typing import List

import pandas as pd
from daeploy import service
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DataForm(BaseModel):
    col1: List[float]
    col2: List[float]
    col3: List[float]


@service.entrypoint
def calculate(data: DataForm) -> list:
    df = pd.DataFrame.from_dict(data.dict())
    logger.info(f"Recieved data: \n{df}")
    row_sum = df.sum(axis=1)
    logger.info(f"Row sums: {row_sum}")
    return row_sum.to_list()


if __name__ == "__main__":
    service.run()
