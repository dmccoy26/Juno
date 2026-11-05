import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('preservation',Path(__file__).resolve().parents[2]/'scripts/check_update_preservation.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class UpdatePreservationTests(unittest.TestCase):
    def baseline(self):return {'workspace':'/private/work','owner':'original','rows':{'memories':['digest'],'check_ins':['diary']},'devices':['paired-laptop']}
    def test_credential_rotation_and_additional_device_do_not_hide_lost_work(self):
        before=self.baseline();after={**before,'devices':['paired-laptop','rotated-desktop']}
        m.compare(before,after)
        with self.assertRaises(ValueError):m.compare(before,{**after,'rows':{'memories':[],'check_ins':['diary']}})
        with self.assertRaises(ValueError):m.compare(before,{**after,'devices':['rotated-desktop']})
    def test_empty_workspace_owner_switch_or_changed_diary_fail(self):
        before=self.baseline()
        for change in ({'workspace':'/other'},{'owner':'new'},{'rows':{}},{'rows':{'memories':['digest'],'check_ins':['changed']}}):
            with self.subTest(change=change),self.assertRaises(ValueError):m.compare(before,{**before,**change})
