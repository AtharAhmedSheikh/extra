-- Create customers table
CREATE TABLE customers (
    phone_number TEXT NOT NULL UNIQUE PRIMARY KEY,
    total_spend INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    escalation_status BOOLEAN NOT NULL DEFAULT FALSE,
    customer_type TEXT CHECK (customer_type IN ('B2B', 'D2C')) NOT NULL,
    customer_name TEXT,
    email TEXT,
    address TEXT,
    cart_id TEXT,
    order_history TEXT[] DEFAULT '{}', -- Array of strings
    socials JSONB DEFAULT '{}',        -- JSON object for social links
    customer_quickbook_id TEXT,
    tags TEXT[] NOT NULL DEFAULT '{}',          -- Array of strings
    interest_groups TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Optional: Automatically update updated_at on record update
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ language 'plpgsql';