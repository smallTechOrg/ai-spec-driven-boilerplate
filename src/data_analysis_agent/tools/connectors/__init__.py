"""Dataset connectors: abstract dataset access behind a ``DatasetConnector`` protocol.

A dataset (the agent's "tool") is addressed by a URI; a connector knows how to validate the
connection, discover its tables, and build the dataset's in-process MCP server. ``ParquetConnector``
(internal) is fully implemented; ``PostgresConnector`` (external) is BETA and flag-gated.
"""
