import unittest
from nexus_video.story_v4 import STORIES, generate_story

class StoryV4Tests(unittest.TestCase):
    def test_all_categories_produce_six_structured_beats(self):
        for category in STORIES:
            story = generate_story(category, "test-seed-" + category)
            self.assertEqual(story["category"], category)
            self.assertEqual(len(story["events"]), 6)
            for event in story["events"]:
                for key in ("event_id", "scene", "action", "sfx", "transition", "text", "camera"):
                    self.assertIn(key, event)
                    self.assertTrue(event[key])

    def test_each_story_uses_distinct_scene_types(self):
        for category in STORIES:
            story = generate_story(category, "distinct-" + category)
            scenes = [event["scene"] for event in story["events"]]
            self.assertEqual(len(scenes), len(set(scenes)), category)

    def test_generation_is_deterministic_for_request_seed(self):
        a = generate_story("paranormal", "same-request-id")
        b = generate_story("paranormal", "same-request-id")
        self.assertEqual(a, b)

    def test_unknown_category_falls_back_to_known_category(self):
        story = generate_story("not-a-category", "fallback-seed")
        self.assertIn(story["category"], STORIES)

if __name__ == "__main__":
    unittest.main()
