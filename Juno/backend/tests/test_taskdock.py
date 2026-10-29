import unittest
from urllib.parse import parse_qs, urlsplit

from juno.taskdock import TaskDockError, TaskDockReader


class TaskDockTests(unittest.TestCase):
    def page(self, ids, *, offset=0, total=None, more=False, revision="r1"):
        return dict(items=[{"id": ident} for ident in ids], offset=offset,
                    total=len(ids) if total is None else total,
                    has_more=more, snapshot=revision)

    def test_workspace_includes_native_and_imported_and_checks_revision(self):
        calls = []
        pages = [self.page(["native-1"], total=2, more=True),
                 self.page(["imported-1"], offset=1, total=2)]
        def transport(url, headers):
            calls.append((url, headers))
            return pages.pop(0)
        snapshot = TaskDockReader("http://127.0.0.1:8100", "secret", transport).fetch()
        self.assertEqual([r["id"] for r in snapshot.items], ["native-1", "imported-1"])
        self.assertEqual(urlsplit(calls[0][0]).path, "/workspace/tasks")
        query = parse_qs(urlsplit(calls[1][0]).query)
        self.assertEqual(query["expected_snapshot"], ["r1"])
        self.assertEqual(query["include_completed"], ["true"])
        self.assertEqual(calls[0][1]["Authorization"], "Bearer secret")
        self.assertNotIn("secret", repr(snapshot))

    def test_partial_or_changed_snapshots_are_rejected(self):
        for second in [self.page(["b"], offset=1, total=2, revision="r2"),
                       self.page(["a"], offset=1, total=2),
                       self.page([], offset=1, total=2)]:
            with self.subTest(second=second):
                pages = [self.page(["a"], total=2, more=True), second]
                reader = TaskDockReader("http://localhost:8100", transport=lambda *_: pages.pop(0))
                with self.assertRaises(TaskDockError):
                    reader.fetch()

    def test_empty_workspace_is_valid(self):
        reader = TaskDockReader("http://localhost:8100", transport=lambda *_: self.page([]))
        self.assertEqual(reader.fetch().items, ())

    def test_insecure_or_credential_bearing_origins_are_rejected(self):
        for origin in ["http://example.com", "https://user:secret@example.com",
                       "https://example.com?token=secret", "file:///tmp/tasks"]:
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                TaskDockReader(origin)

    def test_page_limit_does_not_return_partial_success(self):
        reader = TaskDockReader("http://localhost:8100",
                                transport=lambda *_: self.page(["a"], total=2, more=True))
        with self.assertRaises(TaskDockError):
            reader.fetch(max_pages=1)


if __name__ == "__main__":
    unittest.main()
