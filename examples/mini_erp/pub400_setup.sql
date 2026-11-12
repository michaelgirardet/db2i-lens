-- =============================================================================
-- Db2iLens mini-ERP — setup PUB400 / ACS "Run SQL Scripts"
-- =============================================================================
-- Free PUB400 accounts cannot CREATE SCHEMA. Each user already has a personal
-- library (often same name as the user profile). Replace YOUR_LIBRARY below
-- with that library before running.
--
-- Tables are prefixed MLENS_ so they do not collide with other objects in the
-- shared personal library. Scan with --tables MLENS_% to ignore the rest.
--
-- 1. Create a free account on https://pub400.com and wait for activation.
-- 2. Replace YOUR_LIBRARY below with your personal library (UPPERCASE).
-- 3. Connect ACS → Run SQL Scripts to pub400.com, then run this whole script.
-- 4. Scan with:
--      export JT400_JAR=$HOME/.db2ilens/jt400.jar
--      export DB2ILENS_PASSWORD='...'
--      db2ilens scan --host pub400.com --user YOUR_USER --schema YOUR_LIBRARY \
--        --tables MLENS_% --out scan.yaml
--
-- Intentionally embeds R01–R08 traps (CCSID 65535, CYYMMDD, blanks, etc.).
-- Note: R04 (implied decimal scale) is offline-schema-only — SYSCOLUMNS2 has
-- no implied_scale, so JDBC scans will not raise R04 on PRC.
-- =============================================================================

SET SCHEMA YOUR_LIBRARY;

-- ---------------------------------------------------------------------------
-- Drop previous demo objects (ignore errors on first run)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS MLENS_LIGNES_CMD;
DROP TABLE IF EXISTS MLENS_COMMANDES;
DROP TABLE IF EXISTS MLENS_ARTICLES;
DROP TABLE IF EXISTS MLENS_CLIENTS;

-- ---------------------------------------------------------------------------
-- MLENS_CLIENTS
-- R03: CUSNAME CCSID 65535
-- R05: blank CUSNAME values
-- R08: ACTFLG Y/N
-- R01−: PHNNUM DEC(8,0) phone (not a date)
-- ---------------------------------------------------------------------------
CREATE TABLE MLENS_CLIENTS (
    CUSID   CHAR(10)       CCSID 37     NOT NULL,
    CUSNAME CHAR(30)       CCSID 65535  NOT NULL,
    ACTFLG  CHAR(1)        CCSID 37     NOT NULL,
    PHNNUM  DECIMAL(8, 0)               NOT NULL
);

INSERT INTO MLENS_CLIENTS (CUSID, CUSNAME, ACTFLG, PHNNUM) VALUES
    ('C0001', 'ACME CORP',       'Y', 61234567),
    ('C0002', '              ',  'N', 98765432),
    ('C0003', 'BETA INDUSTRIES', 'Y', 55555555),
    ('C0004', '   ',             'N', 33445566),
    ('C0005', 'GAMMA LOGISTICS', 'Y', 77889900);

-- ---------------------------------------------------------------------------
-- MLENS_COMMANDES
-- R01: ORDDTE DEC(8,0) YYYYMMDD
-- ---------------------------------------------------------------------------
CREATE TABLE MLENS_COMMANDES (
    ORDID  CHAR(10)       CCSID 37 NOT NULL,
    CUSID  CHAR(10)       CCSID 37 NOT NULL,
    ORDDTE DECIMAL(8, 0)           NOT NULL,
    ORDSTS CHAR(1)        CCSID 37 NOT NULL
);

INSERT INTO MLENS_COMMANDES (ORDID, CUSID, ORDDTE, ORDSTS) VALUES
    ('O1001', 'C0001', 20260115, 'O'),
    ('O1002', 'C0002', 20260228, 'C'),
    ('O1003', 'C0003', 20260301, 'O'),
    ('O1004', 'C0001', 20261231, 'X'),
    ('O1005', 'C0005', 20261111, 'O');

-- ---------------------------------------------------------------------------
-- MLENS_ARTICLES
-- R02: CRTDTE DEC(7,0) CYYMMDD (includes 19xx via 990615 → century 0)
-- R06−: ARTDESC has COLUMN_TEXT so obscure-name rule should not fire
-- R09: STDPRC zeros as sentinel (rule stub in v1)
-- ---------------------------------------------------------------------------
CREATE TABLE MLENS_ARTICLES (
    ARTID   CHAR(10)       CCSID 37 NOT NULL,
    ARTDESC CHAR(40)       CCSID 37 NOT NULL,
    CRTDTE  DECIMAL(7, 0)           NOT NULL,
    STDPRC  DECIMAL(9, 0)           NOT NULL
);

INSERT INTO MLENS_ARTICLES (ARTID, ARTDESC, CRTDTE, STDPRC) VALUES
    ('A100', 'WIDGET-A', 1250115, 1999),
    ('A200', 'GADGET-B', 1241201, 4599),
    ('A300', 'MOTOR-C',  1260301, 0),
    ('A400', 'SEAL-D',    990615, 0),
    ('A500', 'BOLT-E',   1220101, 125);

LABEL ON COLUMN MLENS_ARTICLES (ARTDESC TEXT IS 'Article description');

-- ---------------------------------------------------------------------------
-- MLENS_LIGNES_CMD
-- R04 offline uses implied_scale=2; on real IBM i SCALE=0 only —
--     document as known JDBC/offline divergence in #18 if R04 is absent.
-- R07: TAGS with recurring '|' separator
-- ---------------------------------------------------------------------------
CREATE TABLE MLENS_LIGNES_CMD (
    ORDID CHAR(10)        CCSID 37 NOT NULL,
    ARTID CHAR(10)        CCSID 37 NOT NULL,
    QTY   DECIMAL(7, 0)            NOT NULL,
    PRC   DECIMAL(9, 0)            NOT NULL,
    TAGS  VARCHAR(50)     CCSID 37
);

INSERT INTO MLENS_LIGNES_CMD (ORDID, ARTID, QTY, PRC, TAGS) VALUES
    ('O1001', 'A100',  2, 1999, 'spare|urgent'),
    ('O1001', 'A200',  1, 4599, 'bulk,retail'),
    ('O1002', 'A100', 10, 1899, 'promo'),
    ('O1003', 'A300',  3, 9990, 'export|hazmat'),
    ('O1004', 'A200',  5, 4500, 'retail'),
    ('O1005', 'A100',  1, 1999, 'spare');

SELECT 'MLENS_CLIENTS' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM MLENS_CLIENTS
UNION ALL
SELECT 'MLENS_COMMANDES', COUNT(*) FROM MLENS_COMMANDES
UNION ALL
SELECT 'MLENS_ARTICLES', COUNT(*) FROM MLENS_ARTICLES
UNION ALL
SELECT 'MLENS_LIGNES_CMD', COUNT(*) FROM MLENS_LIGNES_CMD;
