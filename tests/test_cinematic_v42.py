import unittest
from PIL import Image, ImageChops, ImageStat

from nexus_video.cinematic_v42 import cinematic_camera, cinematic_finish


class CinematicV42Tests(unittest.TestCase):
    def setUp(self):
        self.base = Image.new("RGBA", (540, 960), (18, 22, 29, 255))

    def test_cinematic_finish_preserves_frame_dimensions(self):
        event = {"scene": "hallway", "action": "shadow_cross"}
        result = cinematic_finish(self.base, event, 0.45, 30, 90, 7019)
        self.assertEqual(result.size, self.base.size)

    def test_cinematic_finish_is_deterministic_for_same_seed_and_frame(self):
        event = {"scene": "phone_room", "action": "phone_ring"}
        a = cinematic_finish(self.base, event, 0.4, 24, 90, 7019)
        b = cinematic_finish(self.base, event, 0.4, 24, 90, 7019)
        self.assertEqual(ImageChops.difference(a, b).getbbox(), None)

    def test_cinematic_finish_adds_visible_lighting_and_atmosphere(self):
        event = {"scene": "stairs", "action": "walk_down"}
        result = cinematic_finish(self.base, event, 0.5, 40, 90, 7019)
        self.assertGreater(ImageStat.Stat(ImageChops.difference(
            result.convert("RGB"), self.base.convert("RGB"))).mean[0], 1.25)

    def test_shadow_action_changes_visual_result(self):
        plain = {"scene": "hallway", "action": "walk_down"}
        haunted = {"scene": "hallway", "action": "shadow_cross"}
        a = cinematic_finish(self.base, plain, 0.5, 40, 90, 7019)
        b = cinematic_finish(self.base, haunted, 0.5, 40, 90, 7019)
        self.assertGreater(ImageStat.Stat(ImageChops.difference(a, b)).mean[0], 0.1)

    def test_camera_paths_are_narrative_and_deterministic(self):
        dolly = {"camera": "slow_dolly", "action": "phone_ring"}
        track = {"camera": "lateral_track", "action": "walk_down"}
        a = cinematic_camera(self.base, dolly, 0.6, 40, 90, 7019)
        b = cinematic_camera(self.base, track, 0.6, 40, 90, 7019)
        self.assertEqual(a.size, self.base.size)
        self.assertEqual(a, cinematic_camera(self.base, dolly, 0.6, 40, 90, 7019))
        self.assertGreater(ImageStat.Stat(ImageChops.difference(a, b)).mean[0], 0.1)


if __name__ == "__main__":
    unittest.main()
