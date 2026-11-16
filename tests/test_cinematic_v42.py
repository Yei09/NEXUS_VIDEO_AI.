import unittest
from PIL import Image, ImageChops, ImageDraw, ImageStat

from nexus_video.cinematic_v42 import cinematic_camera, cinematic_finish


class CinematicV42Tests(unittest.TestCase):
    def setUp(self):
        self.base = Image.new("RGBA", (540, 960), (18, 22, 29, 255))
        draw = ImageDraw.Draw(self.base, "RGBA")
        for y in range(0, 960, 32):
            shade = 12 + y // 40
            draw.rectangle((0, y, 540, y+32), fill=(shade, shade+5, shade+11, 255))
        draw.polygon([(40, 120), (490, 120), (380, 850), (130, 850)],
                     fill=(36, 42, 52, 255), outline=(110, 118, 128, 255), width=5)
        draw.line((270, 120, 270, 850), fill=(140, 120, 95, 180), width=6)

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
        same = cinematic_camera(self.base, dolly, 0.6, 40, 90, 7019)
        self.assertIsNone(ImageChops.difference(a, same).getbbox())
        self.assertGreater(ImageStat.Stat(ImageChops.difference(a, b)).mean[0], 0.1)


if __name__ == "__main__":
    unittest.main()
