"""Updates must not silently replace established workspaces with empty ones."""
import json
from pathlib import Path
import tempfile
import unittest
from juno.workspace_guard import WorkspaceError, read_identity, validate_owner, pin_identity


class WorkspaceGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)

    def established(self):
        data = self.state/'postgres/data'
        data.mkdir(parents=True)
        (data/'PG_VERSION').write_text('17')
        (self.state/'desktop-owner.json').write_text(json.dumps({'owner_id':'owner-a','device_id':'rotating'}))
        pin_identity(self.state, 'owner-a')

    def test_first_run_allowed_but_existing_database_cannot_get_new_owner(self):
        self.assertEqual(read_identity(self.state), {})
        validate_owner({}, [])
        with self.assertRaises(WorkspaceError): validate_owner({}, ['existing'])
        with self.assertRaises(WorkspaceError): validate_owner({'owner_id':'missing'}, ['existing'])
        validate_owner({'owner_id':'existing'}, ['existing','other'])

    def test_lost_database_or_owner_stops_instead_of_initializing_empty_workspace(self):
        self.established()
        version=self.state/'postgres/data/PG_VERSION'
        version.unlink()
        with self.assertRaises(WorkspaceError): read_identity(self.state)
        version.write_text('17')
        (self.state/'desktop-owner.json').unlink()
        with self.assertRaises(WorkspaceError): read_identity(self.state)

    def test_path_and_owner_pins_cannot_be_silently_replaced(self):
        self.established()
        original=(self.state/'workspace-identity.json').read_bytes()
        with self.assertRaises(WorkspaceError): pin_identity(self.state,'different')
        self.assertEqual((self.state/'workspace-identity.json').read_bytes(),original)
        marker=json.loads(original);marker['path']='/different/workspace'
        (self.state/'workspace-identity.json').write_text(json.dumps(marker))
        with self.assertRaises(WorkspaceError): read_identity(self.state)

    def test_device_rotation_is_allowed_and_corrupt_identity_is_rejected(self):
        self.established()
        (self.state/'desktop-owner.json').write_text(json.dumps({'owner_id':'owner-a','device_id':'new-device'}))
        self.assertEqual(read_identity(self.state)['device_id'],'new-device')
        pin_identity(self.state,'owner-a')
        (self.state/'workspace-identity.json').write_text('{broken')
        with self.assertRaises(WorkspaceError): read_identity(self.state)

    def test_legacy_identity_without_database_is_not_a_fresh_install(self):
        (self.state/'desktop-owner.json').write_text(json.dumps({'owner_id':'existing'}))
        with self.assertRaises(WorkspaceError): read_identity(self.state)
