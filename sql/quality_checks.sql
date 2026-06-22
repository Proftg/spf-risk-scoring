-- Data quality checks (run against the SQLite database).
-- Each query returns a documented quality metric.

-- 1. Total volume
SELECT COUNT(*) AS n_clients FROM clients;

-- 2. Duplicate identifiers (should be 0)
SELECT COUNT(*) AS n_duplicate_ids
FROM (SELECT ID FROM clients GROUP BY ID HAVING COUNT(*) > 1);

-- 3. Age values outside a plausible range (18-100)
SELECT COUNT(*) AS n_invalid_ages
FROM clients
WHERE AGE < 18 OR AGE > 100;

-- 4. Non strictly positive credit limits
SELECT COUNT(*) AS n_invalid_limits
FROM clients
WHERE LIMIT_BAL <= 0;

-- 5. Referential integrity: EDUCATION codes missing from the reference
SELECT COUNT(*) AS n_orphan_education
FROM clients c
LEFT JOIN reference_segments r
  ON r.dimension = 'education' AND r.code = c.EDUCATION
WHERE r.code IS NULL;

-- 6. Target balance (default rate)
SELECT
  ROUND(AVG(default_flag) * 100, 2) AS default_rate_pct
FROM clients;
