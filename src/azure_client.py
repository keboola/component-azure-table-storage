import logging
from collections.abc import Iterable

from azure.core.exceptions import HttpResponseError, ResourceExistsError
from azure.data.tables import TableServiceClient, UpdateMode
from keboola.component.exceptions import UserException

# Azure Table Storage limits a single transaction to 100 operations of the same PartitionKey
BATCH_SIZE = 100


class AzureTableStorageClient:
    def __init__(self, connection_string: str) -> None:
        self._service_client = TableServiceClient.from_connection_string(connection_string)

    def test_connection(self) -> None:
        """List tables to verify the connection string is valid and has access."""
        try:
            next(self._service_client.list_tables(), None)
        except HttpResponseError as e:
            raise UserException(f"Connection failed: {e.message}") from e

    def list_tables(self) -> list[str]:
        """Return names of all tables in the storage account."""
        try:
            return [t.name for t in self._service_client.list_tables()]
        except HttpResponseError as e:
            raise UserException(f"Failed to list tables: {e.message}") from e

    def ensure_table_exists(self, table_name: str) -> None:
        try:
            self._service_client.create_table(table_name)
            logging.info("Created Azure table '%s'", table_name)
        except ResourceExistsError:
            logging.debug("Azure table '%s' already exists", table_name)
        except HttpResponseError as e:
            if e.status_code == 409:
                logging.debug("Azure table '%s' already exists", table_name)
            else:
                raise UserException(f"Failed to create table '{table_name}': {e.message or str(e)}") from e

    def upsert_entities(
        self,
        table_name: str,
        entities: Iterable[dict],
        mode: str,
    ) -> int:
        """Upsert entities grouped by PartitionKey, batched up to BATCH_SIZE.

        Entities are buffered per-partition so that each batch submitted to Azure
        contains only a single PartitionKey (Azure requirement). Each partition buffer
        is flushed as soon as it reaches BATCH_SIZE, keeping memory bounded to
        BATCH_SIZE * number_of_distinct_partitions in the worst case.

        Returns total entity count.
        """
        update_mode = UpdateMode.MERGE if mode == "merge" else UpdateMode.REPLACE
        table_client = self._service_client.get_table_client(table_name)

        # Buffer per PartitionKey — each buffer is flushed at BATCH_SIZE
        partitions: dict[str, list[dict]] = {}
        total = 0

        for entity in entities:
            pk = entity["PartitionKey"]
            buf = partitions.setdefault(pk, [])
            buf.append(entity)

            if len(buf) == BATCH_SIZE:
                self._submit_batch(table_client, buf, update_mode)
                total += BATCH_SIZE
                partitions[pk] = []

        # Flush remaining entities per partition
        for batch in partitions.values():
            if batch:
                self._submit_batch(table_client, batch, update_mode)
                total += len(batch)

        return total

    @staticmethod
    def _submit_batch(table_client, batch: list[dict], update_mode: UpdateMode) -> None:
        operations = [("upsert", entity, {"mode": update_mode}) for entity in batch]
        try:
            table_client.submit_transaction(operations)
        except HttpResponseError as e:
            pk = batch[0]["PartitionKey"]
            raise UserException(f"Failed to write batch for PartitionKey '{pk}': {e.message}") from e
        logging.debug("Submitted batch of %d entities (partition: %s)", len(batch), batch[0]["PartitionKey"])
