"""Unit tests for GraphSleuth's investigator.py.

These tests use mocked FalkorDB responses. They do not modify or connect to
real graph data. Run with: python -m unittest -v test_investigator.py
"""

import unittest
from unittest.mock import MagicMock, patch

import investigator


class FakeQueryResult:
    def __init__(self, rows):
        self.result_set = rows


class ServiceChainTests(unittest.TestCase):
    def test_upstream_query_follows_outgoing_depends_on_edges(self):
        graph = MagicMock()
        graph.query.return_value = FakeQueryResult(
            [["Payment Database", "Healthy", 1]]
        )

        result = investigator.get_service_chain(graph, "Payment API", "upstream")

        query = graph.query.call_args.args[0]
        self.assertIn("(s:Service {name: $service})", query)
        self.assertIn("-[:DEPENDS_ON*1..10]->(d:Service)", query)
        self.assertEqual(
            result,
            [{"name": "Payment Database", "status": "Healthy", "depth": 1}],
        )
        self.assertEqual(graph.query.call_args.args[1], {"service": "Payment API"})

    def test_downstream_query_follows_incoming_depends_on_edges(self):
        graph = MagicMock()
        graph.query.return_value = FakeQueryResult(
            [["Notification Service", "Healthy", 1], ["Customer Portal", "Healthy", 2]]
        )

        result = investigator.get_service_chain(graph, "Payment API", "downstream")

        query = graph.query.call_args.args[0]
        self.assertIn("(d:Service)", query)
        self.assertIn("-[:DEPENDS_ON*1..10]->", query)
        self.assertEqual([item["depth"] for item in result], [1, 2])
        self.assertEqual([item["name"] for item in result], ["Notification Service", "Customer Portal"])

    def test_invalid_direction_raises_value_error(self):
        with self.assertRaises(ValueError):
            investigator.get_service_chain(MagicMock(), "Payment API", "sideways")


class IncidentInvestigationTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.graph = MagicMock()
        self.db.select_graph.return_value = self.graph

    @patch.object(investigator, "connect_db")
    def test_unknown_incident_returns_not_found_and_closes_db(self, connect_db_mock):
        connect_db_mock.return_value = (self.db, self.graph)
        self.graph.query.return_value = FakeQueryResult([])

        result = investigator.investigate_incident("INC-NOT-REAL", display=False)

        self.assertFalse(result["found"])
        self.assertEqual(result["incident_id"], "INC-NOT-REAL")
        self.assertIn("No incident found", result["message"])
        self.db.close.assert_called_once()

    @patch.object(investigator, "get_service_chain")
    @patch.object(investigator, "connect_db")
    def test_known_incident_returns_expected_facts(self, connect_db_mock, chain_mock):
        connect_db_mock.return_value = (self.db, self.graph)
        self.graph.query.return_value = FakeQueryResult([
            [
                "INC001",
                "Payment API latency spike",
                "High",
                "Investigating",
                "Payment API",
                "Degraded",
                "HighLatency",
                "Payment API latency exceeded threshold.",
            ]
        ])
        chain_mock.side_effect = [
            [{"name": "Payment Database", "status": "Healthy", "depth": 1}],
            [
                {"name": "Notification Service", "status": "Healthy", "depth": 1},
                {"name": "Customer Portal", "status": "Healthy", "depth": 2},
            ],
        ]

        result = investigator.investigate_incident("INC001", display=False)

        self.assertTrue(result["found"])
        self.assertEqual(result["incident_id"], "INC001")
        self.assertEqual(result["affected_service"], "Payment API")
        self.assertEqual(result["service_status"], "Degraded")
        self.assertEqual(result["dependencies"], ["Payment Database"])
        self.assertEqual(result["downstream_services"][0]["depth"], 1)
        self.assertEqual(result["downstream_services"][1]["depth"], 2)
        self.assertFalse(result["root_cause_confirmed"])
        self.db.close.assert_called_once()

    @patch.object(investigator, "get_service_chain")
    @patch.object(investigator, "connect_db")
    def test_missing_alert_fields_are_allowed(self, connect_db_mock, chain_mock):
        connect_db_mock.return_value = (self.db, self.graph)
        self.graph.query.return_value = FakeQueryResult([
            ["INC002", "Test incident", "Low", "Open", "Isolated Service", "Healthy", None, None]
        ])
        chain_mock.side_effect = [[], []]

        result = investigator.investigate_incident("INC002", display=False)

        self.assertTrue(result["found"])
        self.assertIsNone(result["alert_type"])
        self.assertIsNone(result["alert_message"])
        self.assertEqual(result["upstream_services"], [])
        self.assertEqual(result["downstream_services"], [])


class DependencyEdgeTests(unittest.TestCase):
    @patch.object(investigator, "get_service_chain")
    @patch.object(investigator, "connect_db")
    def test_returns_only_edges_within_connected_service_set(self, connect_db_mock, chain_mock):
        db = MagicMock()
        graph = MagicMock()
        connect_db_mock.return_value = (db, graph)
        graph.query.side_effect = [
            FakeQueryResult([["Payment API"]]),  # Selected service exists.
            FakeQueryResult([  # All graph edges returned by the mocked database.
                ["Notification Service", "Payment API"],
                ["Customer Portal", "Notification Service"],
                ["Unrelated Service A", "Unrelated Service B"],
            ]),
        ]
        chain_mock.side_effect = [
            [{"name": "Payment Database", "status": "Healthy", "depth": 1}],
            [
                {"name": "Notification Service", "status": "Healthy", "depth": 1},
                {"name": "Customer Portal", "status": "Healthy", "depth": 2},
            ],
        ]

        edges = investigator.get_dependency_edges("Payment API")

        self.assertEqual(
            {(edge["source"], edge["target"]) for edge in edges},
            {
                ("Notification Service", "Payment API"),
                ("Customer Portal", "Notification Service"),
            },
        )
        db.close.assert_called_once()

    @patch.object(investigator, "connect_db")
    def test_missing_service_returns_no_edges_and_closes_db(self, connect_db_mock):
        db = MagicMock()
        graph = MagicMock()
        connect_db_mock.return_value = (db, graph)
        graph.query.return_value = FakeQueryResult([])

        result = investigator.get_dependency_edges("Missing Service")

        self.assertEqual(result, [])
        db.close.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
