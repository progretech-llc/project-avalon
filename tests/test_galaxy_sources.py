import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

import galaxy_sources as gs


class GalaxySourcesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.folder = self.root / "work"
        self.folder.mkdir()
        self.prefs = dict(
            roots=[dict(label="Work", path=str(self.folder))],
            max_files=100,
            max_directories=20,
            display_agents=None,
            show_memory=True,
        )
        self.scene = dict(
            schema="factory-observatory-wallpaper/v1",
            nodes=[
                dict(
                    id="host", kind="Host", name="Fixture", path=str(self.root), root=""
                ),
                dict(id="agent:openclaw-desk", kind="Agent", name="Old desk", root=""),
                dict(
                    id="root:Work",
                    kind="Directory system",
                    name="Work",
                    path=str(self.folder),
                    root="Work",
                ),
                dict(id="agent:worker", kind="Agent", name="Worker", root=""),
                dict(
                    id="file:one",
                    kind="Remembered file",
                    name="One",
                    path=str(self.folder / "one.py"),
                    root="Work",
                ),
            ],
            links=[{"from": 1, "to": 4}, {"from": 3, "to": 4}],
            agent_activity=[
                dict(agent=1, targets=[4]),
                dict(
                    agent=3,
                    targets=[4],
                    write_targets=[4],
                    modified_targets=[2, 4],
                    last_modified_root=2,
                ),
            ],
            counts={},
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_auto_roster_uses_current_metadata_not_saved_or_recorded_names(self):
        found = gs.candidates(
            self.scene,
            {"agents": ["openclaw-desk", "worker"]},
            {
                "agents": [
                    dict(
                        id="worker",
                        name="Worker",
                        sources=["Codex · configured client"],
                    )
                ]
            },
        )
        self.assertEqual(gs.GalaxySources.selected(self.prefs, found), ["worker"])
        self.assertNotIn("openclaw-desk", [x["id"] for x in found])
        manual = {**self.prefs, "display_agents": ["openclaw-desk"]}
        self.assertEqual(gs.GalaxySources.selected(manual, found), [])
        self.assertEqual(
            gs.GalaxySources.selected({**self.prefs, "display_agents": []}, found), []
        )

    def test_native_owners_are_selectable_and_context_targets_are_reindexed(self):
        found = gs.candidates({}, {}, {'agents': [dict(id='mak', name='Mak', sources=['Native Harness · recorded owner'])]})
        self.assertEqual([x['id'] for x in found], ['mak'])
        self.scene['agent_activity'][1]['context_targets'] = [2, 4]
        result = gs.filter_scene(self.scene, {'worker'}, self.prefs)
        self.assertEqual(result['agent_activity'][0]['context_targets'], [1, 3])

    def test_filter_reindexes_links_and_all_activity_targets_without_reassigning_authors(
        self,
    ):
        result = gs.filter_scene(self.scene, {"worker"}, self.prefs)
        self.assertNotIn("agent:openclaw-desk", [x["id"] for x in result["nodes"]])
        self.assertEqual(
            result["links"], [dict(self.scene["links"][1], **{"from": 2, "to": 3})]
        )
        activity = result["agent_activity"][0]
        self.assertEqual(activity["agent"], 2)
        self.assertEqual(activity["targets"], [3])
        self.assertEqual(activity["write_targets"], [3])
        self.assertEqual(activity["modified_targets"], [1, 3])
        self.assertEqual(activity["last_modified_root"], 1)
        self.assertEqual(result["counts"]["agents"], 1)
        self.assertEqual(len(self.scene["nodes"]), 5)

    def test_folder_filter_hides_removed_system_and_activity_references(self):
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        prefs = {**self.prefs, "roots": [dict(label="Elsewhere", path=str(elsewhere))]}
        result = gs.filter_scene(self.scene, {"worker"}, prefs)
        self.assertEqual([x["kind"] for x in result["nodes"]], ["Host", "Agent"])
        self.assertEqual(result["links"], [])
        self.assertEqual(result["agent_activity"][0]["targets"], [])
        self.assertIsNone(result["agent_activity"][0]["last_modified_root"])

    def test_root_validation_handles_offline_paths_duplicates_and_limits(self):
        offline = {
            **self.prefs,
            "roots": [dict(label="Offline", path=str(self.root / "offline"))],
        }
        self.assertEqual(gs.validate(offline, offline), offline)
        for draft in (
            {**self.prefs, "roots": offline["roots"]},
            {**self.prefs, "roots": self.prefs["roots"] * 2},
            {**self.prefs, "max_files": True},
            {**self.prefs, "display_agents": ["bad/id"]},
            {**self.prefs, "show_memory": 1},
        ):
            with self.assertRaises(ValueError):
                gs.validate(draft, self.prefs)
        alias = self.root / "linked"
        alias.symlink_to(self.folder, target_is_directory=True)
        with self.assertRaises(ValueError):
            gs.validate(
                {
                    **self.prefs,
                    "roots": self.prefs["roots"]
                    + [dict(label="Linked", path=str(alias))],
                },
                self.prefs,
            )

    def test_stale_revision_and_unknown_identity_never_write_source_settings(self):
        config = self.root / "settings.json"
        config.write_text(json.dumps(self.prefs))
        original = config.read_bytes()
        manager = gs.GalaxySources(self.root / "state")
        with (
            patch.object(gs, "CONFIG", config),
            patch.object(manager, "base", return_value={}),
        ):
            with self.assertRaises(ValueError):
                manager.save(dict(settings=self.prefs, revision="old"))
            with self.assertRaises(ValueError):
                manager.save(
                    dict(
                        settings={**self.prefs, "display_agents": ["invented"]},
                        revision=gs.revision(self.prefs),
                    )
                )
        self.assertEqual(config.read_bytes(), original)

    def test_refresh_uses_owned_config_and_output_then_discards_obsolete_result(self):
        config = self.root / "settings.json"
        config.write_text(json.dumps(self.prefs))
        published = self.root / "published.json"
        base = {
            **self.prefs,
            "agents": ["openclaw-desk"],
            "memory": {"provider": "json", "directory": str(self.root / "memory")},
        }
        manager = gs.GalaxySources(self.root / "state")

        def run(argv, **kwargs):
            self.assertEqual(
                kwargs["env"]["CONSTELLATION_CONFIG"],
                str((manager.state / "galaxy-export-sources.json").resolve()),
            )
            if "agent_discovery" in argv[-1]:
                return Mock(
                    stdout=json.dumps(
                        {
                            "agents": [
                                dict(
                                    id="worker",
                                    name="Worker",
                                    sources=["Codex · configured client"],
                                )
                            ]
                        }
                    )
                )
            self.assertIn(
                str((manager.state / "galaxy-export-scene.json").resolve()), argv[-1]
            )
            (manager.state / "galaxy-export-scene.json").write_text(
                json.dumps(self.scene)
            )
            return Mock(stdout="")

        with (
            patch.object(gs, "CONFIG", config),
            patch.object(gs, "SCENE", published),
            patch.object(manager, "base", return_value=base),
            patch.object(manager, "available", return_value=True),
            patch.object(manager, "original_scene", return_value=self.scene),
            patch.object(gs.subprocess, "run", side_effect=run),
        ):
            manager.refresh()
            self.assertNotIn(
                "agent:openclaw-desk",
                [x["id"] for x in json.loads(published.read_text())["nodes"]],
            )
            first = published.read_bytes()

            def changed(argv, **kwargs):
                result = run(argv, **kwargs)
                if "agent_discovery" not in argv[-1]:
                    config.write_text(json.dumps({**self.prefs, "display_agents": []}))
                return result

            with patch.object(gs.subprocess, "run", side_effect=changed):
                manager.refresh()
            self.assertEqual(published.read_bytes(), first)
            self.assertTrue(manager.wake.is_set())
        self.assertEqual(base["agents"], ["openclaw-desk"])
