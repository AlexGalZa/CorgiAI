"""
Tests for the common module.

Covers SoftDeleteModel mixin, Notification creation,
and AuditLogEntry creation.
"""

from django.test import TestCase
from django.utils import timezone

from common.models import (
    SoftDeleteModel,
    SoftDeleteManager,
    SoftDeleteAllManager,
    Notification,
    AuditLogEntry,
)
from tests.factories import create_test_user, setup_user_with_org


class SoftDeleteModelTest(TestCase):
    """Tests for SoftDeleteModel mixin behavior.

    Since SoftDeleteModel is abstract, we test its behavior through
    a concrete proxy or by verifying the mixin methods directly.
    """

    def test_soft_delete_model_has_correct_fields(self):
        """Verify SoftDeleteModel defines expected fields."""
        field_names = [f.name for f in SoftDeleteModel._meta.get_fields()]
        self.assertIn("is_deleted", field_names)
        self.assertIn("deleted_at", field_names)

    def test_soft_delete_manager_is_default(self):
        """Verify default manager filters out deleted records."""
        # SoftDeleteModel is abstract, so we can't access .objects on it directly
        # (Django raises AttributeError: Manager isn't available). Check the
        # manager class is wired through a concrete subclass instead.
        from policies.models import Policy

        self.assertIsInstance(Policy.objects, SoftDeleteManager)

    def test_all_objects_manager_exists(self):
        """Verify all_objects manager includes deleted records."""
        from policies.models import Policy

        self.assertIsInstance(Policy.all_objects, SoftDeleteAllManager)


class NotificationTest(TestCase):
    """Tests for Notification model."""

    def test_create_notification(self):
        user = create_test_user(email="notify@test.com")
        notification = Notification.objects.create(
            user=user,
            notification_type="info",
            title="Test Notification",
            message="This is a test notification message.",
        )
        self.assertIsNotNone(notification.id)
        self.assertEqual(notification.title, "Test Notification")
        self.assertIsNone(notification.read_at)
        self.assertFalse(notification.is_read)

    def test_notification_is_read_property(self):
        user = create_test_user(email="read@test.com")
        notification = Notification.objects.create(
            user=user,
            notification_type="success",
            title="Read Test",
            message="Already read",
            read_at=timezone.now(),
        )
        self.assertTrue(notification.is_read)

    def test_notification_types(self):
        user = create_test_user(email="types@test.com")
        for ntype, _ in Notification.NOTIFICATION_TYPES:
            n = Notification.objects.create(
                user=user,
                notification_type=ntype,
                title=f"{ntype} notification",
                message="test",
            )
            self.assertEqual(n.notification_type, ntype)

    def test_notification_with_organization(self):
        user, org = setup_user_with_org()
        notification = Notification.objects.create(
            user=user,
            organization=org,
            notification_type="quote_update",
            title="Quote Updated",
            message="Your quote has been updated",
        )
        self.assertEqual(notification.organization, org)

    def test_notification_str(self):
        user = create_test_user(email="notstr@test.com")
        notification = Notification.objects.create(
            user=user,
            notification_type="info",
            title="String Test",
            message="test",
        )
        self.assertIn("String Test", str(notification))

    def test_notification_action_url(self):
        user = create_test_user(email="action@test.com")
        notification = Notification.objects.create(
            user=user,
            notification_type="policy_update",
            title="Policy Ready",
            message="View your policy",
            action_url="/portal/policies/123",
        )
        self.assertEqual(notification.action_url, "/portal/policies/123")


class AuditLogEntryTest(TestCase):
    """Tests for AuditLogEntry model."""

    def test_create_audit_log_entry(self):
        user = create_test_user(email="audit@test.com")
        entry = AuditLogEntry.objects.create(
            user=user,
            action="create",
            model_name="Quote",
            object_id="Q-12345",
            changes={"status": {"old": "draft", "new": "submitted"}},
        )
        self.assertIsNotNone(entry.id)
        self.assertEqual(entry.action, "create")
        self.assertEqual(entry.model_name, "Quote")
        self.assertEqual(entry.object_id, "Q-12345")

    def test_audit_log_str_representation(self):
        user = create_test_user(email="auditstr@test.com")
        entry = AuditLogEntry.objects.create(
            user=user,
            action="update",
            model_name="Policy",
            object_id="P-001",
        )
        result = str(entry)
        self.assertIn("auditstr@test.com", result)
        self.assertIn("update", result)
        self.assertIn("Policy", result)

    def test_audit_log_without_user(self):
        entry = AuditLogEntry.objects.create(
            user=None,
            action="create",
            model_name="System",
            object_id=None,
        )
        self.assertIn("system", str(entry))

    def test_audit_log_changes_json(self):
        user = create_test_user(email="auditjson@test.com")
        changes = {
            "premium": {"old": "5000.00", "new": "8000.00"},
            "limits": {"old": 1000000, "new": 2000000},
        }
        entry = AuditLogEntry.objects.create(
            user=user,
            action="update",
            model_name="Policy",
            object_id="P-002",
            changes=changes,
        )
        self.assertEqual(entry.changes["premium"]["new"], "8000.00")

    def test_audit_log_all_action_types(self):
        user = create_test_user(email="auditall@test.com")
        for action_code, _ in AuditLogEntry.ACTION_CHOICES:
            entry = AuditLogEntry.objects.create(
                user=user,
                action=action_code,
                model_name="Test",
                object_id="1",
            )
            self.assertEqual(entry.action, action_code)

    def test_audit_log_with_ip_and_user_agent(self):
        user = create_test_user(email="auditip@test.com")
        entry = AuditLogEntry.objects.create(
            user=user,
            action="login",
            model_name="User",
            object_id=str(user.id),
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        )
        self.assertEqual(entry.ip_address, "192.168.1.1")
        self.assertIn("Mozilla", entry.user_agent)

    def test_audit_log_ordering(self):
        user = create_test_user(email="auditorder@test.com")
        AuditLogEntry.objects.create(
            user=user,
            action="create",
            model_name="A",
            object_id="1",
        )
        e2 = AuditLogEntry.objects.create(
            user=user,
            action="create",
            model_name="B",
            object_id="2",
        )
        entries = list(AuditLogEntry.objects.all())
        # Should be ordered by -timestamp (newest first)
        self.assertEqual(entries[0].id, e2.id)
