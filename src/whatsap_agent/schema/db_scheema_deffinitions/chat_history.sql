CREATE TABLE chat_history (
    phone_number TEXT NOT NULL,
    uid TEXT NOT NULL,
    messages JSONB DEFAULT '[]', -- Array of message objects
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (phone_number)
);

-- Auto update updated_at on changes
CREATE OR REPLACE FUNCTION update_chat_updated_at()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_chat_trigger
BEFORE UPDATE ON chat_history
FOR EACH ROW
EXECUTE PROCEDURE update_chat_updated_at();
