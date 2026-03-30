import logging
from typing import Literal

from keboola.component.exceptions import UserException
from pydantic import BaseModel, Field, ValidationError


class Configuration(BaseModel):
    connection_string: str = Field(alias="#connection_string")
    azure_table_name: str
    partition_key_column: str
    row_key_column: str
    write_mode: Literal["upsert_merge", "upsert_replace"] = "upsert_merge"
    debug: bool = False

    model_config = {"populate_by_name": True}

    def __init__(self, **data):
        try:
            super().__init__(**data)
        except ValidationError as e:
            error_messages = [f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in e.errors()]
            raise UserException(f"Configuration error: {', '.join(error_messages)}")

        if self.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.debug("Component will run in Debug mode")
