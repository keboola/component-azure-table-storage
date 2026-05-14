import io
import os
import unittest
from unittest.mock import MagicMock, patch

from component import Component
from configuration import Configuration

VALID_PARAMS = {
    "#connection_string": "UseDevelopmentStorage=true",
    "azure_table_name": "orders",
    "partition_key_column": "region",
    "row_key_column": "order_id",
    "write_mode": "upsert_merge",
    "debug": False,
}


class TestConfiguration(unittest.TestCase):
    def test_valid_config_parses(self):
        config = Configuration(**VALID_PARAMS)
        self.assertEqual(config.azure_table_name, "orders")
        self.assertEqual(config.partition_key_column, "region")
        self.assertEqual(config.row_key_column, "order_id")
        self.assertEqual(config.write_mode, "upsert_merge")

    def test_connection_only_config_parses(self):
        # Sync actions on the root config form (e.g. testConnection) only send
        # the connection string; Configuration must accept that without raising.
        config = Configuration(**{"#connection_string": "x"})
        self.assertEqual(config.connection_string, "x")
        self.assertIsNone(config.azure_table_name)
        self.assertIsNone(config.partition_key_column)
        self.assertIsNone(config.row_key_column)

    def test_run_requires_row_params(self):
        from keboola.component.exceptions import UserException

        config = Configuration(**{"#connection_string": "x"})
        with self.assertRaises(UserException) as ctx:
            Component._require_row_params(config)
        self.assertIn("azure_table_name", str(ctx.exception))
        self.assertIn("partition_key_column", str(ctx.exception))
        self.assertIn("row_key_column", str(ctx.exception))

    def test_invalid_write_mode_raises_user_exception(self):
        from keboola.component.exceptions import UserException

        bad_params = {**VALID_PARAMS, "write_mode": "delete_all"}
        with self.assertRaises(UserException):
            Configuration(**bad_params)


class TestBuildEntities(unittest.TestCase):
    def _make_params(self, **overrides) -> Configuration:
        return Configuration(**{**VALID_PARAMS, **overrides})

    def test_maps_partition_and_row_keys(self):
        params = self._make_params()
        csv_content = "region,order_id,amount\nEU,ORD-001,100\nUS,ORD-002,200\n"
        with patch("builtins.open", return_value=io.StringIO(csv_content)):
            entities = list(Component._build_entities("dummy.csv", params))

        self.assertEqual(len(entities), 2)
        self.assertEqual(entities[0]["PartitionKey"], "EU")
        self.assertEqual(entities[0]["RowKey"], "ORD-001")
        self.assertEqual(entities[0]["amount"], "100")
        self.assertNotIn("region", entities[0])
        self.assertNotIn("order_id", entities[0])

    def test_missing_partition_key_column_raises(self):
        from keboola.component.exceptions import UserException

        params = self._make_params(partition_key_column="nonexistent")
        with self.assertRaises(UserException):
            Component._validate_key_columns(["region", "order_id", "amount"], params)

    def test_missing_row_key_column_raises(self):
        from keboola.component.exceptions import UserException

        params = self._make_params(row_key_column="nonexistent")
        with self.assertRaises(UserException):
            Component._validate_key_columns(["region", "order_id", "amount"], params)

    def test_same_partition_and_row_key_column_raises(self):
        from keboola.component.exceptions import UserException

        params = self._make_params(partition_key_column="region", row_key_column="region")
        with self.assertRaises(UserException) as ctx:
            Component._validate_key_columns(["region", "order_id", "amount"], params)
        self.assertIn("must be different", str(ctx.exception))


class TestComponentRun(unittest.TestCase):
    @patch.dict(os.environ, {"KBC_DATADIR": "./non-existing-dir"})
    def test_run_no_cfg_fails(self):
        with self.assertRaises(ValueError):
            comp = Component()
            comp.run()

    def test_missing_input_table_raises_user_exception(self):
        from keboola.component.exceptions import UserException

        comp = Component.__new__(Component)
        comp.get_input_tables_definitions = MagicMock(return_value=[])
        with self.assertRaises(UserException):
            comp._get_single_input_table()


if __name__ == "__main__":
    unittest.main()
