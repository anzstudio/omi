from argparse import ArgumentTypeError
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from models.conversation import CreateConversation
from models.conversation_enums import ConversationSource
from scripts import migrate_conversation_language


def test_migration_updates_only_blank_friend_languages(monkeypatch):
    conversations = []
    updated = []
    for conversation_id, data in (
        ('missing', {'source': 'friend'}),
        ('blank', {'source': 'friend', 'language': '  '}),
        ('french', {'source': 'friend', 'language': 'fr'}),
        ('omi', {'source': 'omi'}),
    ):
        conversation = MagicMock(id=conversation_id)
        conversation.to_dict.return_value = data
        conversation.reference.update.side_effect = lambda updates, conversation_id=conversation_id: updated.append(
            (conversation_id, updates)
        )
        conversations.append(conversation)

    db = MagicMock()
    db.collection.return_value.document.return_value.collection.return_value.stream.return_value = conversations
    monkeypatch.setattr(migrate_conversation_language, 'db', db)

    result = migrate_conversation_language.process_user('uid', dry_run=False)

    assert result == {'uid': 'uid', 'fixed': 2, 'status': 'ok'}
    assert updated == [('missing', {'language': 'en'}), ('blank', {'language': 'en'})]


def test_conversation_language_default_is_scoped_to_friend_source():
    values = {
        'started_at': datetime(2026, 1, 1, tzinfo=timezone.utc),
        'finished_at': datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
        'transcript_segments': [],
    }

    assert CreateConversation(**values).language is None
    assert CreateConversation(**values, source=ConversationSource.friend).language == 'en'
    assert CreateConversation(**values, source=ConversationSource.friend, language='fr').language == 'fr'


def test_worker_count_must_be_positive():
    with pytest.raises(ArgumentTypeError):
        migrate_conversation_language._positive_int('0')
    with pytest.raises(SystemExit):
        migrate_conversation_language._build_parser().parse_args(['--workers', '0'])


def test_user_limit_must_be_nonnegative():
    with pytest.raises(ArgumentTypeError):
        migrate_conversation_language._nonnegative_int('-1')
    with pytest.raises(SystemExit):
        migrate_conversation_language._build_parser().parse_args(['--limit', '-1'])
