import unittest
from PIL import Image, ImageChops, ImageDraw

from nexus_video.cinematic_depth_v421 import (
    SceneLayer, compose_scene_layers, render_depth_scene
)
from nexus_video.story_v4 import STORIES


class CinematicDepthV421Tests(unittest.TestCase):
    def setUp(self):
        self.base = Image.new("RGBA", (270, 480), (12, 15, 22, 255))

    def test_layers_have_independent_depth_and_transforms(self):
        a = Image.new("RGBA", (30, 30), (255, 0, 0, 255))
        b = Image.new("RGBA", (30, 30), (0, 255, 0, 255))
        layers = [SceneLayer("far", a, .2, x=20), SceneLayer("near", b, .9, x=120)]
        result = compose_scene_layers(self.base, layers)
        self.assertEqual(result.getpixel((25, 5)), (255, 0, 0))
        self.assertEqual(result.getpixel((125, 5)), (0, 255, 0))

    def test_camera_parallax_scales_with_depth(self):
        sprite = Image.new("RGBA", (12, 12), (255, 255, 255, 255))
        near = SceneLayer("near", sprite, .9, x=80, camera_weight=1)
        far = SceneLayer("far", sprite, .2, x=80, camera_weight=1)
        a = compose_scene_layers(self.base, [near], camera_target=(20, 0))
        b = compose_scene_layers(self.base, [far], camera_target=(20, 0))
        bounds = ImageChops.difference(a, b).getbbox()
        self.assertIsNotNone(bounds)
        self.assertGreater(bounds[2] - bounds[0], 0)

    def test_door_leaf_is_an_independent_animated_layer(self):
        event = {"action": "door_open", "camera": "locked_reveal"}
        a, layers_a = render_depth_scene(self.base, event, .1, 3, 90, 7019)
        b, layers_b = render_depth_scene(self.base, event, .9, 80, 90, 7019)
        self.assertIn("door_leaf", [x["name"] for x in layers_a])
        door_a = next(x for x in layers_a if x["name"] == "door_leaf")
        door_b = next(x for x in layers_b if x["name"] == "door_leaf")
        self.assertNotEqual(door_a["rotation_degrees"], door_b["rotation_degrees"])
        self.assertIsNotNone(ImageChops.difference(a, b).getbbox())

    def test_character_animation_is_separate_from_background(self):
        event = {"action": "walk_down", "camera": "lateral_track"}
        a, layers = render_depth_scene(self.base, event, .1, 3, 90, 7019)
        b, _ = render_depth_scene(self.base, event, .8, 70, 90, 7019)
        self.assertIn("character", [x["name"] for x in layers])
        actor_a = next(x for x in layers if x["name"] == "character")
        _, later_layers = render_depth_scene(self.base, event, .8, 70, 90, 7019)
        actor_b = next(x for x in later_layers if x["name"] == "character")
        self.assertNotEqual(actor_a["alpha_bounds"], actor_b["alpha_bounds"])
        self.assertIsNotNone(ImageChops.difference(a, b).getbbox())

    def test_cast_shadow_moves_only_for_narrative_shadow_events(self):
        event = {"action": "shadow_cross"}
        _, layers = render_depth_scene(self.base, event, .5, 45, 90, 7019)
        self.assertIn("cast_shadow", [x["name"] for x in layers])
        _, plain = render_depth_scene(self.base, {"action": "walk_down"}, .5, 45, 90, 7019)
        self.assertNotIn("cast_shadow", [x["name"] for x in plain])

    def test_environment_is_a_separate_layer(self):
        _, layers = render_depth_scene(self.base, {"action": "phone_ring"}, .5, 45, 90, 7019)
        self.assertIn("environment_particles", [x["name"] for x in layers])

    def test_every_story_beat_has_at_least_one_independent_action_layer(self):
        for category, stories in STORIES.items():
            for _, _, beats in stories:
                for scene, action, sfx, transition, text in beats:
                    _, layers = render_depth_scene(
                        self.base, {"scene": scene, "action": action, "sfx": sfx},
                        .5, 45, 90, 7019
                    )
                    self.assertIn("background_plate_legacy", [x["name"] for x in layers])
                    self.assertTrue(any(x["name"] != "background_plate_legacy" for x in layers),
                                    f"{category}/{action} has no independent action layer")


if __name__ == "__main__":
    unittest.main()
