import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('configure',Path(__file__).resolve().parents[1]/'scripts/configure-runtime.py')
configure=importlib.util.module_from_spec(spec);spec.loader.exec_module(configure)

class RuntimeConfigurationTest(unittest.TestCase):
    def inventory(self):
        return patch.object(configure.urllib.request,'urlopen',return_value=io.BytesIO(b'{"models":[{"name":"local:installed"}]}'))
    def test_missing_model_cannot_replace_existing_runtime_configuration(self):
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder);path=state/'gateway.json';path.write_text('{"existing":"preserve"}')
            with self.inventory(),self.assertRaises(ValueError):configure.configure(state,'not-installed')
            self.assertEqual(path.read_text(),'{"existing":"preserve"}')
    def test_reconfiguration_keeps_gateway_identity_and_has_no_second_model(self):
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder)
            for _ in range(2):
                with self.inventory(),patch.object(configure.shutil,'which',return_value='/test/opencode'):
                    configure.configure(state,'local:installed')
                current=json.loads((state/'gateway.json').read_text())
                if _==0:token=current['token']
                else:self.assertEqual(current['token'],token)
            cfg=json.loads((state/'agent-home/.config/opencode/opencode.json').read_text())
            self.assertEqual(cfg['model'],cfg['small_model'])
            self.assertEqual(cfg['permission'],{'*':'deny'})
            self.assertEqual(cfg['enabled_providers'],['ollama'])
            self.assertEqual((state/'gateway.json').stat().st_mode&0o777,0o600)

if __name__=='__main__':unittest.main()
