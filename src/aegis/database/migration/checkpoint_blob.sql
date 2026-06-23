        CREATE TABLE IF NOT EXISTS checkpoint_blobs (
            thread_id TEXT NOT NULL,
            checkpoint_id TEXT NOT NULL,
            parent_id TEXT,
            checkpoint BLOB NOT NULL,
            metadata BLOB NOT NULL,
            PRIMARY KEY (thread_id, checkpoint_id)
        );
