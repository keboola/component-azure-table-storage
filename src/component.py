import csv
import logging
import sys
from typing import Generator

from keboola.component.base import ComponentBase, sync_action
from keboola.component.exceptions import UserException
from keboola.component.sync_actions import SelectElement

from azure_client import AzureTableStorageClient
from configuration import Configuration

# Azure SDK HTTP logs contain dynamic UUIDs and multipart boundaries; suppressing them
# keeps logs clean and avoids leaking auth-adjacent headers.
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)


class Component(ComponentBase):
    def __init__(self):
        super().__init__()
        self.params = Configuration(**self.configuration.parameters)
        self.client = AzureTableStorageClient(self.params.connection_string)

    def run(self):
        table_name = self._require_row_params(self.params)
        input_table = self._get_single_input_table()
        self._validate_key_columns(input_table.column_names, self.params)
        entities = self._build_entities(input_table.full_path, self.params)
        self._write_entities_to_azure(self.client, table_name, self.params.write_mode, entities)

    @staticmethod
    def _require_row_params(params: Configuration) -> str:
        missing = [
            name
            for name in ("azure_table_name", "partition_key_column", "row_key_column")
            if getattr(params, name) is None
        ]
        if missing:
            raise UserException(f"Missing required configuration fields: {', '.join(missing)}")
        assert params.azure_table_name is not None
        return params.azure_table_name

    def _get_single_input_table(self):
        tables = self.get_input_tables_definitions()
        if not tables:
            raise UserException("No input table found. Please map an input table in the component configuration.")
        if len(tables) > 1:
            logging.warning("Multiple input tables found; only the first one will be processed.")
        table = tables[0]
        logging.info("Processing input table: %s", table.name)
        return table

    @staticmethod
    def _validate_key_columns(columns: list[str], params: Configuration) -> None:
        if params.partition_key_column == params.row_key_column:
            raise UserException(
                f"Partition key column and row key column must be different, "
                f"but both are set to '{params.partition_key_column}'."
            )
        if params.partition_key_column not in columns:
            raise UserException(
                f"Partition key column '{params.partition_key_column}' not found in input table. "
                f"Available columns: {columns}"
            )
        if params.row_key_column not in columns:
            raise UserException(
                f"Row key column '{params.row_key_column}' not found in input table. Available columns: {columns}"
            )

    @staticmethod
    def _build_entities(csv_path: str, params: Configuration) -> Generator[dict, None, None]:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entity = dict(row)
                entity["PartitionKey"] = entity.pop(params.partition_key_column)
                entity["RowKey"] = entity.pop(params.row_key_column)
                yield entity

    @staticmethod
    def _write_entities_to_azure(
        client: AzureTableStorageClient,
        table_name: str,
        write_mode: str,
        entities: Generator[dict, None, None],
    ) -> None:
        client.ensure_table_exists(table_name)
        mode = "merge" if write_mode == "upsert_merge" else "replace"
        total = client.upsert_entities(table_name, entities, mode)
        logging.info("Written %d entities to Azure table '%s'", total, table_name)

    @sync_action("testConnection")
    def test_connection(self):
        self.client.test_connection()
        return {"status": "success", "message": "Connection successful."}

    @sync_action("list_tables")
    def list_tables(self):
        tables = self.client.list_tables()
        return [SelectElement(t) for t in tables]


if __name__ == "__main__":
    try:
        comp = Component()
        comp.execute_action()
    except UserException as exc:
        logging.exception(exc)
        sys.exit(1)
    except Exception as exc:
        logging.exception(exc)
        sys.exit(2)
