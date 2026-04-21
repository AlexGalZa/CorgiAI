"""
Optional Celery tasks for async HubSpot syncing.
When Celery is not installed, signals fall back to synchronous calls.

Anti-loop guard
---------------
The previous ``threading.local()`` flag was cross-process unsafe (Celery
workers live in separate processes and do not share Python state with the
web tier). This module now guards against inbound-webhook echoes by
comparing a sha256 of the outbound payload against
``Policy.last_hubspot_sync_hash``; identical hashes short-circuit before
any network call.
"""

import hashlib
import json
import logging

logger = logging.getLogger(__name__)


def _policy_payload(policy) -> dict:
    """Canonical payload used for HubSpot anti-loop hashing.

    Kept intentionally small — only the fields that drive the HubSpot Deal
    properties set by ``HubSpotSyncService.sync_policy_to_deal``. Matching
    on these fields is what lets us detect "the row we're about to push
    is the same one that arrived from a HubSpot webhook".
    """
    return {
        "policy_number": policy.policy_number or "",
        "coverage_type": policy.coverage_type or "",
        "status": policy.status or "",
        "premium": str(policy.premium or 0),
        "effective_date": policy.effective_date.isoformat()
        if policy.effective_date
        else "",
        "expiration_date": policy.expiration_date.isoformat()
        if policy.expiration_date
        else "",
        "hubspot_deal_id": policy.hubspot_deal_id or "",
    }


def _hash_payload(payload: dict) -> str:
    """sha256 hex digest of a canonicalized JSON payload."""
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8"),
    ).hexdigest()


def _sync_policy_with_hash_guard(policy_id: int) -> None:
    """Run ``sync_policy_to_deal`` guarded by a payload-hash anti-loop check.

    Compares the canonical payload hash against
    ``Policy.last_hubspot_sync_hash``. If they match the push is skipped
    (the HubSpot deal is already in sync — usually because the current
    Django state was itself written by an inbound webhook echo). Otherwise
    we sync and stamp the new hash via ``update_fields`` so ``updated_at``
    bumps and downstream readers observe the sync.
    """
    from policies.models import Policy
    from hubspot_sync.service import HubSpotSyncService

    try:
        policy = Policy.objects.get(id=policy_id)
    except Policy.DoesNotExist:
        logger.debug("sync_policy_task: policy %s not found", policy_id)
        return

    new_hash = _hash_payload(_policy_payload(policy))
    if new_hash and new_hash == policy.last_hubspot_sync_hash:
        logger.debug(
            "sync_policy_task: skipping policy %s — payload hash unchanged",
            policy_id,
        )
        return

    HubSpotSyncService.sync_policy_to_deal(policy_id)

    # Re-read in case the service wrote back ``hubspot_deal_id`` on create,
    # which flips the canonical payload. Compute the final hash against
    # whatever is now in the DB and stamp it with update_fields so
    # ``updated_at`` advances on the row.
    try:
        policy.refresh_from_db(fields=["hubspot_deal_id"])
    except Policy.DoesNotExist:
        return

    final_hash = _hash_payload(_policy_payload(policy))
    policy.last_hubspot_sync_hash = final_hash
    policy.save(update_fields=["last_hubspot_sync_hash", "updated_at"])


try:
    from celery import shared_task

    @shared_task(bind=True, max_retries=3, default_retry_delay=60)
    def sync_policy_task(self, policy_id: int):
        try:
            _sync_policy_with_hash_guard(policy_id)
        except Exception as e:
            self.retry(exc=e, countdown=60 * (self.request.retries + 1))

    @shared_task(bind=True, max_retries=3, default_retry_delay=60)
    def sync_user_task(self, user_id: int):
        from hubspot_sync.service import HubSpotSyncService

        try:
            HubSpotSyncService.sync_user_to_contact(user_id)
        except Exception as e:
            self.retry(exc=e, countdown=60 * (self.request.retries + 1))

    @shared_task(bind=True, max_retries=3, default_retry_delay=60)
    def sync_org_task(self, org_id: int):
        from hubspot_sync.service import HubSpotSyncService

        try:
            HubSpotSyncService.sync_org_to_company(org_id)
        except Exception as e:
            self.retry(exc=e, countdown=60 * (self.request.retries + 1))

except ImportError:
    # Celery not installed — signals.py would call service directly.
    pass
