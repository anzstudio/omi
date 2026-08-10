from datetime import datetime, timezone
from models.chat import Message, MessageSender, MessageType

def test_get_messages_as_string_sender_app_id():
    m = Message(
        id='m1',
        text='hello',
        created_at=datetime.now(timezone.utc),
        sender=MessageSender.ai,
        type=MessageType.text,
        app_id='some-app-id'
    )
    result = Message.get_messages_as_string([m])
    assert "some-app-id" in result

def test_get_messages_as_xml_sender_app_id():
    m = Message(
        id='m1',
        text='hello',
        created_at=datetime.now(timezone.utc),
        sender=MessageSender.ai,
        type=MessageType.text,
        app_id='some-app-id'
    )
    result = Message.get_messages_as_xml([m])
    assert "<sender>some-app-id</sender>" in result
