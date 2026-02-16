"""
Tests for feature pack dependency enforcement during install.
"""
import os
import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.test.utils import override_settings
from django.urls import reverse


class FeaturePackDependencyInstallTest(TestCase):
    """Verify feature pack install enforces dependencies."""

    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='staff',
            password='pass123',
            is_staff=True,
        )
        self.client.login(username='staff', password='pass123')

        self.temp_dir = tempfile.mkdtemp()
        self.store_dir = os.path.join(self.temp_dir, 'store')
        self.packs_dir = os.path.join(self.temp_dir, 'packs')
        os.makedirs(self.store_dir, exist_ok=True)
        os.makedirs(self.packs_dir, exist_ok=True)

        self.pack_name = 'itsm_pack'
        self.pack_store_path = os.path.join(self.store_dir, self.pack_name)
        os.makedirs(self.pack_store_path, exist_ok=True)

        config_path = os.path.join(self.pack_store_path, 'config.py')
        with open(config_path, 'w', encoding='utf-8') as handle:
            handle.write(
                "FEATURE_PACK_CONFIG = {\n"
                "    'name': 'ITSM Pack',\n"
                "    'dependencies': ['inventory_pack'],\n"
                "}\n"
            )

        self.override = override_settings(
            FEATURE_PACK_STORE_DIR=self.store_dir,
            FEATURE_PACKS_DIR=self.packs_dir,
        )
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_install_blocked_when_dependency_missing(self):
        with patch('cmdb.feature_pack_views.ensure_store_repo', return_value=(True, 'ok')):
            with patch('cmdb.feature_pack_views.FeaturePackNode.get_all_packs', return_value=[]):
                response = self.client.post(
                    reverse('cmdb:feature_pack_add'),
                    {'pack_name': self.pack_name},
                    follow=True,
                )

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Cannot install' in str(message) for message in messages))
        self.assertTrue(any('missing' in str(message) for message in messages))
        self.assertFalse(os.path.exists(os.path.join(self.packs_dir, self.pack_name)))

    def test_install_blocked_when_dependency_disabled(self):
        installed = [SimpleNamespace(name='inventory_pack', enabled=False)]
        with patch('cmdb.feature_pack_views.ensure_store_repo', return_value=(True, 'ok')):
            with patch('cmdb.feature_pack_views.FeaturePackNode.get_all_packs', return_value=installed):
                response = self.client.post(
                    reverse('cmdb:feature_pack_add'),
                    {'pack_name': self.pack_name},
                    follow=True,
                )

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Cannot install' in str(message) for message in messages))
        self.assertTrue(any('disabled' in str(message) for message in messages))
        self.assertFalse(os.path.exists(os.path.join(self.packs_dir, self.pack_name)))
