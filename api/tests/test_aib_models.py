import uuid
import pytest
from django.utils import timezone


@pytest.mark.django_db
def test_aib_session_creates_with_token():
    from aib.models import AibSession
    session = AibSession.objects.create()
    assert session.id is not None
    assert session.session_token is not None
    assert len(session.session_token) == 36  # UUID format
    assert session.user is None
    assert session.quote is None


@pytest.mark.django_db
def test_aib_message_links_to_session():
    from aib.models import AibSession, AibMessage
    session = AibSession.objects.create()
    msg = AibMessage.objects.create(
        session=session,
        role="user",
        content="Hello",
        extracted_fields={},
    )
    assert msg.session_id == session.id
    assert msg.role == "user"
    assert msg.extracted_fields == {}


@pytest.mark.django_db
def test_aib_session_token_is_unique():
    from aib.models import AibSession
    s1 = AibSession.objects.create()
    s2 = AibSession.objects.create()
    assert s1.session_token != s2.session_token


@pytest.mark.django_db
def test_aib_message_role_choices():
    from aib.models import AibSession, AibMessage
    session = AibSession.objects.create()
    msg = AibMessage.objects.create(session=session, role="assistant", content="Hi!")
    assert msg.role == "assistant"
