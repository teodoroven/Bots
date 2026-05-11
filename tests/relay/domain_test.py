from __future__ import annotations

import unittest
from datetime import datetime
from datetime import timedelta

from relay.domain import Client
from relay.domain import Date
from relay.domain import Element
from relay.domain import Filial
from relay.domain import Folder
from relay.domain import Limit
from relay.domain import NamedElement
from relay.domain import Question
from relay.domain import Root
from relay.domain import SystemContext


class DomainElementTest(unittest.TestCase):

    def test_element_named_element_and_folder_roundtrip(self):
        element: Element = Element(1)
        named: NamedElement = NamedElement(2, "Name")
        folder: Folder[Element] = Folder(3)

        folder.add_element(element)
        folder.add_element(named)
        removed: bool = folder.remove_id(element.id)

        self.assertTrue(removed)
        self.assertEqual([named.dumps()], [item.dumps() for item in folder.elements])
        loaded_named: NamedElement = NamedElement.loads(named.dumps())

        self.assertEqual(named.id, loaded_named.id)
        self.assertEqual(named.name, loaded_named.name)
        self.assertEqual(0, Root().id)

    def test_folder_rejects_duplicate_ids(self):
        folder: Folder[Element] = Folder(1)
        folder.add_element(Element(2))

        folder.add_element(Element(2))

        self.assertEqual(2, len(folder.elements))


class DomainCatalogTest(unittest.TestCase):

    def test_filial_date_and_question_models_dump_public_data(self):
        date: Date = Date(1, datetime(2026, 5, 7, 12, 0, 0))
        filial: Filial = Filial(2, "Central")
        question: Question = Question(3, "Q?", ["A"])

        filial.add_element(date)

        self.assertTrue(filial.has_date(date.get_answer()))
        self.assertEqual("Q?", question.get_answer(cut_string = False))
        self.assertEqual(3, question.dumps()["id"])

    def test_system_context_injects_questions_into_template(self):
        context: SystemContext = SystemContext(1, "Base{}")
        question: Question = Question(2, "Question?", ["Answer"])

        result: str = context.get_context([question])

        self.assertIn("Base", result)
        self.assertIn("Question?", result)


class DomainLimitClientTest(unittest.TestCase):

    def test_limit_debit_reset_and_client_multiple_limits(self):
        limit: Limit = Limit(1, 60, 100, datetime.now() - timedelta(seconds = 120), 100, False)
        shared: Limit = Limit(2, 3600, 1000, datetime.now(), 1000, True)
        client: Client = Client(10)
        client.add_limit(limit)
        client.add_limit(shared)

        client.debit_tokens(25)
        limit.check_reset()

        self.assertEqual(100, limit.left)
        self.assertEqual(975, shared.left)
        self.assertIs(shared, client.find_limit(3600))
        self.assertTrue(client.remove_id(shared.id))
        self.assertIsNone(client.find_limit(3600))


if __name__ == "__main__":
    unittest.main()
