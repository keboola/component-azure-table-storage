The Azure Table Storage Writer loads Keboola Storage tables into Azure Table Storage, mapping each input row to an entity in a target table.

Key features:

- **Upsert write modes** – choose `upsert_merge` to preserve existing entity properties, or `upsert_replace` to fully overwrite the entity.
- **Automatic table creation** – the target table is created if it does not already exist.
- **Flexible key mapping** – select any input column as the entity `PartitionKey` and any other column as the `RowKey`.
- **Row-based configuration** – write to multiple Azure tables from a single configuration using rows.
- **Connection validation** – built-in **Test Connection** action verifies credentials before running.
- **Table discovery** – **Load tables** action lists existing tables in the storage account directly in the UI.
- **Secure credentials** – the storage account connection string is stored encrypted.
