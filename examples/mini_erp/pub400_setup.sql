-- =============================================================================
-- Db2iLens mini-ERP — setup PUB400 / ACS "Run SQL Scripts"
-- =============================================================================
-- 1. Create a free account on https://pub400.com and wait for activation.
-- 2. Replace YOUR_LIBRARY below with your personal library (often = user profile).
-- 3. Connect ACS → Run SQL Scripts to pub400.com, then run this whole script.
-- 4. Scan with:
--      export DB2ILENS_PASSWORD='...'
--      db2ilens scan --host pub400.com --user YOUR_USER --schema YOUR_LIBRARY \
--        --password-stdin --out scan.yaml <<< "$DB2ILENS_PASSWORD"
--
-- Intentionally embeds R01–R08 traps (CCSID 65535, CYYMMDD, blanks, etc.).
-- =============================================================================

SET SCHEMA YOUR_LIBRARY;

-- ---------------------------------------------------------------------------
-- Drop previous demo objects (ignore errors on first run)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS LIGNES_CMD;
DROP TABLE IF EXISTS COMMANDES;
DROP TABLE IF EXISTS ARTICLES;
DROP TABLE IF EXISTS CLIENTS;

-- ---------------------------------------------------------------------------
-- CLIENTS
-- R03: CUSNAME CCSID 65535
-- R05: blank CUSNAME values
-- R08: ACTFLG Y/N
-- R01−: PHNNUM DEC(8,0) phone (not a date)
-- ---------------------------------------------------------------------------
CREATE TABLE CLIENTS (
    CUSID   CHAR(10)       CCSID 37     NOT NULL,
    CUSNAME CHAR(30)       CCSID 65535  NOT NULL,
    ACTFLG  CHAR(1)        CCSID 37     NOT NULL,
    PHNNUM  DECIMAL(8, 0)               NOT NULL
);

INSERT INTO CLIENTS (CUSID, CUSNAME, ACTFLG, PHNNUM) VALUES
    ('C0001', 'ACME CORP',       'Y', 61234567),
    ('C0002', '              ',  'N', 98765432),
    ('C0003', 'BETA INDUSTRIES', 'Y', 55555555),
    ('C0004', '   ',             'N', 33445566),
    ('C0005', 'GAMMA LOGISTICS', 'Y', 77889900);

-- ---------------------------------------------------------------------------
-- COMMANDES
-- R01: ORDDTE DEC(8,0) YYYYMMDD
-- ---------------------------------------------------------------------------
CREATE TABLE COMMANDES (
    ORDID  CHAR(10)       CCSID 37 NOT NULL,
    CUSID  CHAR(10)       CCSID 37 NOT NULL,
    ORDDTE DECIMAL(8, 0)           NOT NULL,
    ORDSTS CHAR(1)        CCSID 37 NOT NULL
);

INSERT INTO COMMANDES (ORDID, CUSID, ORDDTE, ORDSTS) VALUES
    ('O1001', 'C0001', 20260115, 'O'),
    ('O1002', 'C0002', 20260228, 'C'),
    ('O1003', 'C0003', 20260301, 'O'),
    ('O1004', 'C0001', 20261231, 'X'),
    ('O1005', 'C0005', 20261111, 'O');

-- ---------------------------------------------------------------------------
-- ARTICLES
-- R02: CRTDTE DEC(7,0) CYYMMDD (includes 19xx via 990615 → century 0)
-- R06−: ARTDESC has COLUMN_TEXT so obscure-name rule should not fire
-- R09: STDPRC zeros as sentinel (rule stub in v1)
-- ---------------------------------------------------------------------------
CREATE TABLE ARTICLES (
    ARTID   CHAR(10)       CCSID 37 NOT NULL,
    ARTDESC CHAR(40)       CCSID 37 NOT NULL,
    CRTDTE  DECIMAL(7, 0)           NOT NULL,
    STDPRC  DECIMAL(9, 0)           NOT NULL
);

INSERT INTO ARTICLES (ARTID, ARTDESC, CRTDTE, STDPRC) VALUES
    ('A100', 'WIDGET-A', 1250115, 1999),
    ('A200', 'GADGET-B', 1241201, 4599),
    ('A300', 'MOTOR-C',  1260301, 0),
    ('A400', 'SEAL-D',    990615, 0),
    ('A500', 'BOLT-E',   1220101, 125);

LABEL ON COLUMN ARTICLES (ARTDESC TEXT IS 'Article description');

-- ---------------------------------------------------------------------------
-- LIGNES_CMD
-- R04 offline uses implied_scale=2; on real IBM i SCALE=0 only —
--     document as known JDBC/offline divergence in #18 if R04 is absent.
-- R07: TAGS with recurring '|' separator
-- ---------------------------------------------------------------------------
CREATE TABLE LIGNES_CMD (
    ORDID CHAR(10)        CCSID 37 NOT NULL,
    ARTID CHAR(10)        CCSID 37 NOT NULL,
    QTY   DECIMAL(7, 0)            NOT NULL,
    PRC   DECIMAL(9, 0)            NOT NULL,
    TAGS  VARCHAR(50)     CCSID 37
);

INSERT INTO LIGNES_CMD (ORDID, ARTID, QTY, PRC, TAGS) VALUES
    ('O1001', 'A100',  2, 1999, 'spare|urgent'),
    ('O1001', 'A200',  1, 4599, 'bulk,retail'),
    ('O1002', 'A100', 10, 1899, 'promo'),
    ('O1003', 'A300',  3, 9990, 'export|hazmat'),
    ('O1004', 'A200',  5, 4500, 'retail'),
    ('O1005', 'A100',  1, 1999, 'spare');

SELECT 'CLIENTS' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM CLIENTS
UNION ALL
SELECT 'COMMANDES', COUNT(*) FROM COMMANDES
UNION ALL
SELECT 'ARTICLES', COUNT(*) FROM ARTICLES
UNION ALL
SELECT 'LIGNES_CMD', COUNT(*) FROM LIGNES_CMD;
