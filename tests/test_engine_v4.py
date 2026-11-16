import unittest

from nexus_video.engine_v4 import image_difference, render_frame


class EngineV4VisualTests(unittest.TestCase):
    def test_landline_and_mobile_call_are_distinct_compositions(self):
        landline = {
            "scene": "phone_room",
            "action": "phone_ring",
            "transition": "fade",
        }
        mobile = {
            "scene": "mobile_close",
            "action": "screen_call",
            "transition": "fade",
        }
        frame_landline = render_frame(landline, 0.5, 7, 15, 7019)
        frame_mobile = render_frame(mobile, 0.5, 7, 15, 7019)
        self.assertGreater(
            image_difference(frame_landline, frame_mobile),
            7.0,
            "The mobile-call shot must be visually distinct from the landline shot",
        )

    def test_receiver_close_and_floor_cable_are_distinct_compositions(self):
        receiver = {
            "scene": "receiver_close",
            "action": "receiver_lift",
            "transition": "fade",
        }
        floor = {
            "scene": "floor_cable",
            "action": "cable_crawl",
            "transition": "fade",
        }
        receiver_frame = render_frame(receiver, 0.5, 7, 15, 7019)
        floor_frame = render_frame(floor, 0.5, 7, 15, 7019)
        self.assertGreater(
            image_difference(receiver_frame, floor_frame),
            7.0,
            "The receiver macro shot must be visually distinct from the floor cable shot",
        )

    def test_receiver_close_regeneration_changes_rendered_composition(self):
        event = {
            "scene": "receiver_close",
            "action": "receiver_lift",
            "transition": "fade",
        }
        first = render_frame(event, 0.5, 7, 15, 7019)
        regenerated = render_frame(event, 0.5, 7, 15, 8028)
        self.assertGreater(
            image_difference(first, regenerated),
            1.25,
            "A receiver regeneration must alter visible composition, not only metadata",
        )

    def test_floor_cable_regeneration_changes_rendered_composition(self):
        event = {
            "scene": "floor_cable",
            "action": "cable_crawl",
            "transition": "fade",
        }
        first = render_frame(event, 0.5, 7, 15, 7019)
        regenerated = render_frame(event, 0.5, 7, 15, 8028)
        self.assertGreater(
            image_difference(first, regenerated),
            1.25,
            "A floor-cable regeneration must alter visible composition, not only metadata",
        )


if __name__ == "__main__":
    unittest.main()
