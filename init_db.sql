/*
 Navicat Premium Data Transfer

 Source Server         : PixivManager
 Source Server Type    : SQLite
 Source Server Version : 3021000
 Source Schema         : main

 Target Server Type    : SQLite
 Target Server Version : 3021000
 File Encoding         : 65001

 Date: 01/01/2019 07:39:59
*/

PRAGMA foreign_keys = false;

-- ----------------------------
-- Table structure for session
-- ----------------------------
DROP TABLE IF EXISTS "session";
CREATE TABLE "session" (
  "uuid" TEXT NOT NULL,
  "data" TEXT,
  CONSTRAINT "uuid" UNIQUE ("uuid" ASC)
);

-- ----------------------------
-- Table structure for ugoira
-- ----------------------------
DROP TABLE IF EXISTS "ugoira";
CREATE TABLE "ugoira" (
  "works_id" INTEGER NOT NULL,
  "delay" integer,
  "zip_url" TEXT,
  CONSTRAINT "ugoira_id" UNIQUE ("works_id" ASC) ON CONFLICT REPLACE
);

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS "users";
CREATE TABLE "users" (
  "local_id" integer NOT NULL,
  "user_id" INTEGER NOT NULL,
  "name" TEXT,
  "account" TEXT,
  "gender" integer,
  "total_illusts" integer,
  "total_manga" integer,
  "total_novels" integer,
  "is_followed" integer,
  "country_code" TEXT,
  PRIMARY KEY ("local_id"),
  CONSTRAINT "user_id" UNIQUE ("user_id" ASC) ON CONFLICT REPLACE
);

-- ----------------------------
-- Table structure for works
-- ----------------------------
DROP TABLE IF EXISTS "works";
CREATE TABLE "works" (
  "local_id" INTEGER NOT NULL,
  "works_id" integer NOT NULL,
  "author_id" integer,
  "type" text,
  "title" TEXT,
  "caption" TEXT,
  "create_date" integer,
  "page_count" integer,
  "total_bookmarks" integer,
  "total_view" integer,
  "is_bookmarked" integer,
  "tags" text,
  "custom_tags" TEXT,
  "bookmark_rate" real,
  "image_urls" TEXT,
  PRIMARY KEY ("local_id"),
  CONSTRAINT "works_id" UNIQUE ("works_id" ASC)
);

PRAGMA foreign_keys = true;
