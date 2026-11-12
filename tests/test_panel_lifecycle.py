import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
s=importlib.util.spec_from_file_location('avalon_launcher',Path(__file__).parents[1]/'avalon.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class PanelLifecycle(unittest.TestCase):
 def test_off_stops_backend(self):
  with patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'Enabled: No\n',''))as run:
   self.assertTrue(m.stop_when_off());self.assertIn('stop',run.call_args.args[0])
 def test_enabled_wallpaper_preserves_presence(self):
  with patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'Enabled: Yes\n',''))as run:
   self.assertFalse(m.stop_when_off());self.assertEqual(run.call_count,1)
 def test_unknown_presence_is_not_reported_off(self):
  with patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','unavailable'))as run:
   self.assertFalse(m.stop_when_off());self.assertEqual(run.call_count,2)
 def test_browser_exit_runs_cleanup(self):
  with patch.object(m.subprocess,'call',return_value=0),patch.object(m,'stop_when_off')as cleanup:
   m.panel(['browser']);cleanup.assert_called_once()
 def test_browser_error_runs_cleanup(self):
  with patch.object(m.subprocess,'call',side_effect=OSError('failed')),patch.object(m,'stop_when_off')as cleanup:
   with self.assertRaises(OSError):m.panel(['browser'])
   cleanup.assert_called_once()
