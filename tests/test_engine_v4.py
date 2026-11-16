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


if __name__ == "__main__":
    unittest.main()
