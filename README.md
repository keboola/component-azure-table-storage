Azure Table Storage Writer
==========================

Keboola writer component that loads tables into [Azure Table Storage](https://learn.microsoft.com/azure/storage/tables/).

Functionality
=============

- Writes rows from a single input table as entities into a target Azure table.
- Upsert semantics with two write modes:
  - `upsert_merge` – keeps existing entity properties not present in the input row.
  - `upsert_replace` – overwrites the whole entity.
- Creates the target table if it does not exist.
- Sync actions:
  - **Test Connection** – validates the connection string.
  - **Load tables** – lists existing tables in the storage account.

Prerequisites
=============

An Azure Storage account [connection string](https://learn.microsoft.com/azure/storage/common/storage-account-keys-manage) with permissions to read/write tables.

Configuration
=============

Configuration (account-level)
-----------------------------
- **Connection String** (`#connection_string`, required, encrypted) – Azure Storage account connection string.
- **Debug Mode** (`debug`) – enables verbose logging. Azure SDK HTTP logs are suppressed to avoid leaking auth headers.

Row Configuration (per table)
-----------------------------
- **Azure Table Name** (`azure_table_name`, required) – target table; pick from existing tables or type a new name.
- **Partition Key Column** (`partition_key_column`, required) – input column mapped to `PartitionKey`.
- **Row Key Column** (`row_key_column`, required) – input column mapped to `RowKey`. Must differ from the partition key column.
- **Write Mode** (`write_mode`) – `upsert_merge` (default) or `upsert_replace`.

Input
=====

Exactly one input table mapping per row. If multiple tables are mapped, only the first is processed. The partition and row key columns must exist in the input table.

Development
-----------

Customize the local data folder by replacing `CUSTOM_FOLDER` in `docker-compose.yml`:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    volumes:
      - ./:/code
      - ./CUSTOM_FOLDER:/data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clone and run:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
git clone https://github.com/keboola/component-azure-table-storage component-azure-table-storage
cd component-azure-table-storage
docker-compose build
docker-compose run --rm dev
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run tests and lint:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
docker-compose run --rm test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Integration
===========

See the [Keboola developer documentation](https://developers.keboola.com/extend/component/deployment/) for deployment details.