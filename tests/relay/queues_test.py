from __future__ import annotations

import unittest
from datetime import datetime
from threading import Event

from bots import Bot
from bots import Message
from relay.queues import ProcessTask
from relay.queues import QueuedMessage
from relay.queues import SavingOrder


class FakeBot:

    def get_bot_key(self) -> str:
        return "telebot"


class QueuesTest(unittest.TestCase):

    def test_queued_message_dumps_and_status_transitions(self):
        wrapper: Message = Message(1, "hello")
        queued: QueuedMessage = QueuedMessage(5, wrapper, "telebot", 123)

        self.assertTrue(queued.check_pending())
        queued.mark(QueuedMessage.STATUS_FAILED, "temporary")
        self.assertTrue(queued.check_pending())
        queued.mark(QueuedMessage.STATUS_SENT)

        self.assertEqual("sent", queued.dumps()["status"])
        self.assertEqual(123, queued.dumps()["chat_id"])

    def test_process_task_priority_for_admins(self):
        event: Bot.Event = Bot.Event(1, 2, "text", datetime.now())
        admin_task: ProcessTask = ProcessTask(10, FakeBot(), event, admin_priority = True)
        user_task: ProcessTask = ProcessTask(11, FakeBot(), event, admin_priority = False)

        self.assertLess(admin_task.get_queue_item(), user_task.get_queue_item())

    def test_saving_order_processes_each_item_once(self):
        processed: list[int] = []
        processed_event: Event = Event()

        def process(item: dict[str, int]):
            processed.append(item["id"])
            if len(processed) == 2:
                processed_event.set()

        order: SavingOrder = SavingOrder(process, max_parallel = 1)
        order.add({"id": 1})
        order.add({"id": 2})

        self.assertTrue(processed_event.wait(2))

        for thread in list(order.threads):
            if thread.ident is not None:
                thread.join(timeout = 2)

        self.assertEqual([1, 2], processed)
        self.assertFalse(order.check_working())


if __name__ == "__main__":
    unittest.main()
