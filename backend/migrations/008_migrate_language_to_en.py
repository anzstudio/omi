import argparse
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to the Python path before local imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import firebase_admin
from firebase_admin import credentials, firestore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _init_firebase():
    if not firebase_admin._apps:
        try:
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
        except ValueError:
            pass
        except Exception as e:
            logger.error("Error initializing Firebase Admin SDK. Make sure GOOGLE_APPLICATION_CREDENTIALS is set.")
            logger.error(e)
            sys.exit(1)


def get_db():
    _init_firebase()
    return firestore.client()


def get_all_users():
    """Get all user documents."""
    users_ref = get_db().collection('users')
    return list(users_ref.stream())


def process_user_conversations(user_doc, dry_run=False):
    """Migrate empty language fields to 'en' for a single user."""
    uid = user_doc.id
    conversations_ref = get_db().collection('users').document(uid).collection('conversations')

    # Query for conversations where language is not set or empty
    # Firestore doesn't have a direct "is null" query that works well across all cases,
    # so we get all conversations and filter locally, or just check 'language' field.
    # To be efficient, we'll stream conversations and update those needing it.

    conversations = list(conversations_ref.stream())

    updates = 0
    batch = get_db().batch()
    batch_count = 0

    for doc in conversations:
        data = doc.to_dict()
        language = data.get('language')

        # We only update if language is None or empty string
        if not language:
            if not dry_run:
                batch.update(doc.reference, {'language': 'en'})
                batch_count += 1
                if batch_count >= 499:
                    batch.commit()
                    batch = get_db().batch()
                    batch_count = 0
            updates += 1

    if batch_count > 0 and not dry_run:
        batch.commit()

    return updates


def main():
    parser = argparse.ArgumentParser(description='Migrate empty conversation language to en')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing')
    args = parser.parse_args()

    logger.info("Fetching all users...")
    users = get_all_users()
    logger.info(f"Found {len(users)} users")

    total_updates = 0
    users_updated = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=64) as executor:
        futures = {executor.submit(process_user_conversations, user, args.dry_run): user.id for user in users}
        for future in as_completed(futures):
            uid = futures[future]
            try:
                updates = future.result()
                if updates > 0:
                    total_updates += updates
                    users_updated += 1
            except Exception as e:
                logger.error(f"Error processing {uid}: {e}")

    elapsed = time.time() - start
    logger.info(f"Done in {elapsed:.1f}s")
    logger.info(f"Results: {total_updates} conversations updated across {users_updated} users.")


if __name__ == '__main__':
    main()
