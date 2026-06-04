from types import SimpleNamespace

from app.services.chat_service import serialize_message


def test_serialize_message_outputs_expected_payload():
    message = SimpleNamespace(
        id="11111111-1111-1111-1111-111111111111",
        sender_id="22222222-2222-2222-2222-222222222222",
        receiver_id="33333333-3333-3333-3333-333333333333",
        content="Hello test message",
        media_url="https://example.com/media.jpg",
        media_type="image/jpeg",
        media_name="media.jpg",
        media_size=2048,
        timestamp="2026-01-01T00:00:00Z",
        is_seen=False,
        reply_to_message_id=None,
        reactions={"thumbs_up": 1},
        is_pinned=False,
        edited_at=None,
    )

    payload = serialize_message(message)

    assert payload["id"] == str(message.id)
    assert payload["sender_id"] == str(message.sender_id)
    assert payload["receiver_id"] == str(message.receiver_id)
    assert payload["content"] == "Hello test message"
    assert payload["media_url"] == message.media_url
    assert payload["media_type"] == message.media_type
    assert payload["reactions"] == message.reactions
