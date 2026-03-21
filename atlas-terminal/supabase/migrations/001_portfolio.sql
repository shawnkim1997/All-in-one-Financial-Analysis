-- Portfolio positions table
CREATE TABLE IF NOT EXISTS positions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  ticker TEXT NOT NULL,
  company_name TEXT,
  quantity DECIMAL(15,6) NOT NULL,
  avg_price DECIMAL(15,4) NOT NULL,
  currency TEXT DEFAULT 'USD',
  source TEXT DEFAULT 'manual',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Watchlist table
CREATE TABLE IF NOT EXISTS watchlist (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  ticker TEXT NOT NULL,
  added_at TIMESTAMPTZ DEFAULT NOW()
);

-- Analysis cache table
CREATE TABLE IF NOT EXISTS analysis_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  analysis_type TEXT NOT NULL,
  data JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL
);

-- Indexes
CREATE INDEX idx_positions_user ON positions(user_id);
CREATE INDEX idx_positions_ticker ON positions(ticker);
CREATE INDEX idx_watchlist_user ON watchlist(user_id);
CREATE INDEX idx_cache_ticker_type ON analysis_cache(ticker, analysis_type);
CREATE INDEX idx_cache_expires ON analysis_cache(expires_at);
