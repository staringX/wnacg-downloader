-- Create manga downloads table
CREATE TABLE IF NOT EXISTS manga_downloads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(500) NOT NULL,
  author VARCHAR(200) NOT NULL,
  work_name VARCHAR(500) NOT NULL,
  manga_url TEXT NOT NULL UNIQUE,
  file_size BIGINT,
  page_count INTEGER,
  updated_at TIMESTAMP WITH TIME ZONE,
  downloaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  file_path TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_manga_author ON manga_downloads(author);
CREATE INDEX IF NOT EXISTS idx_manga_work ON manga_downloads(work_name);
CREATE INDEX IF NOT EXISTS idx_manga_updated ON manga_downloads(updated_at DESC);

-- Create author favorites table
CREATE TABLE IF NOT EXISTS favorite_authors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  author_name VARCHAR(200) NOT NULL UNIQUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create recent updates tracking table
CREATE TABLE IF NOT EXISTS manga_updates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(500) NOT NULL,
  author VARCHAR(200) NOT NULL,
  work_name VARCHAR(500) NOT NULL,
  manga_url TEXT NOT NULL UNIQUE,
  file_size BIGINT,
  page_count INTEGER,
  updated_at TIMESTAMP WITH TIME ZONE,
  is_downloaded BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_updates_author ON manga_updates(author);
CREATE INDEX IF NOT EXISTS idx_updates_downloaded ON manga_updates(is_downloaded);
