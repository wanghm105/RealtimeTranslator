import unittest
from unittest.mock import patch

from core.sentence_merge import SentenceMerger


class SentenceMergerTests(unittest.TestCase):
    def test_merges_incomplete_fragment_with_next_fragment(self):
        merger = SentenceMerger()
        self.assertEqual(merger.add("This is an unfinished"), [])
        self.assertEqual(merger.add("sentence."), ["This is an unfinished sentence."])

    def test_preserves_common_abbreviations(self):
        merger = SentenceMerger()
        self.assertEqual(merger.add("Dr. Smith arrived. Next point."),
                         ["Dr. Smith arrived.", "Next point."])

    def test_flushes_stale_fragment(self):
        merger = SentenceMerger(max_wait=3)
        with patch('core.sentence_merge.time.time', return_value=100):
            self.assertEqual(merger.add("Incomplete fragment"), [])
        with patch('core.sentence_merge.time.time', return_value=104):
            self.assertEqual(merger.flush_if_stale(), "Incomplete fragment")
            self.assertIsNone(merger.flush_if_stale())


if __name__ == '__main__':
    unittest.main()
