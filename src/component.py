import csv
import logging
import sys
from typing import Generator

from keboola.component.base import ComponentBase, sync_action
from keboola.component.exceptions import UserException

from azure_client import AzureTableStorageClient
from configuration import Configuration


class Component(ComponentBase):
    def __init__(self):
        super().__init__()
        self.params = Configuration(**self.configuration.parameters)
        self.client = AzureTableStorageClient(self.params.connection_string)

    def run(self):
        input_table = self._get_single_input_table()
        self._validate_key_columns(input_table.columns, self.params)
        entities = self._build_entities(input_table.full_path, self.params)
        self._write_entities_to_azure(self.client, self.params, entities)

    @sync_action("testConnection")
    def test_connection(self):
        self.client.test_connection()
        return {"status": "success", "message": "Connection successful."}

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
        params: Configuration,
        entities: Generator[dict, None, None],
    ) -> None:
        client.ensure_table_exists(params.azure_table_name)
        mode = "merge" if params.write_mode == "upsert_merge" else "replace"
        total = client.upsert_entities(params.azure_table_name, entities, mode)
        logging.info("Written %d entities to Azure table '%s'", total, params.azure_table_name)


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
