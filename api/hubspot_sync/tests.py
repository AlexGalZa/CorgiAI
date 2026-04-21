"""Tests for the HubSpot outbound anti-loop guard."""

from unittest.mock import patch

from django.test import TestCase

from hubspot_sync.tasks import (
    _hash_payload,
    _policy_payload,
    _sync_policy_with_hash_guard,
)
from tests.factories import create_test_policy


class HubSpotAntiLoopGuardTest(TestCase):
    """Verify ``sync_policy_task`` short-circuits on unchanged payload hashes.

    The scenario under test mirrors the inbound-webhook echo: HubSpot
    fires a deal.propertyChange webhook → inbound handler writes the
    same status back to Django → ``post_save`` would fire the outbound
    sync signal → the hash guard MUST detect the hash is identical and
    skip the push so we do not loop.
    """

    def test_identical_payload_hash_short_circuits_push(self):
        policy = create_test_policy()
        # Simulate an earlier successful push by stamping the hash that
        # matches the policy's current state. An inbound webhook that
        # writes back the same values would leave this hash unchanged.
        policy.last_hubspot_sync_hash = _hash_payload(_policy_payload(policy))
        policy.save(update_fields=["last_hubspot_sync_hash"])

        with patch(
            "hubspot_sync.service.HubSpotSyncService.sync_policy_to_deal"
        ) as push:
            _sync_policy_with_hash_guard(policy.id)

        push.assert_not_called()

    def test_changed_payload_triggers_push(self):
        policy = create_test_policy()
        # Stamp a stale hash so the current state looks "new" to the guard.
        policy.last_hubspot_sync_hash = "stale-hash-does-not-match"
        policy.save(update_fields=["last_hubspot_sync_hash"])

        with patch(
            "hubspot_sync.service.HubSpotSyncService.sync_policy_to_deal"
        ) as push:
            _sync_policy_with_hash_guard(policy.id)

        push.assert_called_once_with(policy.id)
        policy.refresh_from_db()
        # Hash should have been updated to reflect the current payload.
        self.assertNotEqual(policy.last_hubspot_sync_hash, "stale-hash-does-not-match")
        self.assertEqual(
            policy.last_hubspot_sync_hash,
            _hash_payload(_policy_payload(policy)),
        )

    def test_empty_hash_treats_policy_as_new(self):
        policy = create_test_policy()
        self.assertEqual(policy.last_hubspot_sync_hash, "")

        with patch(
            "hubspot_sync.service.HubSpotSyncService.sync_policy_to_deal"
        ) as push:
            _sync_policy_with_hash_guard(policy.id)

        push.assert_called_once_with(policy.id)
