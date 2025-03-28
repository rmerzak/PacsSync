-- Ensure the `uuid-ossp` extension is available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Check if the database exists and create it if it does not
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'backend') THEN
        EXECUTE 'CREATE DATABASE backend';
    END IF;
END $$;

-- Connect to the specific database
\c backend

-- Create the "users" table if it does not exist
CREATE TABLE IF NOT EXISTS "users" (
  "id" UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  "username" VARCHAR(255) NOT NULL,
  "first_name" VARCHAR(255),
  "last_name" VARCHAR(255),
  "email" VARCHAR(255) UNIQUE,
  "password" VARCHAR(255),
  "gender" VARCHAR(255),
  "sexual_preferences" TEXT,
  "interests" TEXT[],
  "pictures" TEXT[5],
  "fame_rating" NUMERIC,
  "location" VARCHAR(255),
  "latitude" NUMERIC,
  "address" VARCHAR(255),
  "age" NUMERIC,
  "bio" TEXT,
  "is_verified" BOOLEAN DEFAULT FALSE,
  "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "updated_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create the "user_views" table if it does not exist
CREATE TABLE IF NOT EXISTS "user_views" (
  "id" UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  "viewer_id" UUID,
  "viewed_id" UUID,
  "view_time" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_viewer_id FOREIGN KEY ("viewer_id") REFERENCES "users" ("id"),
  CONSTRAINT fk_viewed_id FOREIGN KEY ("viewed_id") REFERENCES "users" ("id")
);

-- Create the "user_likes" table if it does not exist
CREATE TABLE IF NOT EXISTS "user_likes" (
  "id" UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  "liker_id" UUID,
  "liked_id" UUID,
  "like_time" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_liker_id FOREIGN KEY ("liker_id") REFERENCES "users" ("id"),
  CONSTRAINT fk_liked_id FOREIGN KEY ("liked_id") REFERENCES "users" ("id")
);

-- Create the "Message" table if it does not exist
CREATE TABLE IF NOT EXISTS "Message" (
  "id" UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  "sender_id" UUID,
  "receiver_id" UUID,
  "time" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "content" TEXT,
  CONSTRAINT fk_sender_id FOREIGN KEY ("sender_id") REFERENCES "users" ("id"),
  CONSTRAINT fk_receiver_id FOREIGN KEY ("receiver_id") REFERENCES "users" ("id")
);