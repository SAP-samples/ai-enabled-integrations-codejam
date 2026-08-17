/**
 * Post-test script that assembles the final test_report.json.
 *
 * Reads .test-results.json (written by the node:test reporter) and
 * coverage/coverage-final.json (written by c8 after the test process exits),
 * then merges them into test_report.json.
 *
 * Schema mirrors the agent-side report written by sap-agent-bootstrap's
 * conftest.py so downstream tooling (evaluation scorers, dashboards) can
 * consume both shapes uniformly.
 */

import { existsSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const rootDir = process.cwd();
const resultsPath = join(rootDir, ".test-results.json");
const coverageDir = join(rootDir, "coverage");
const outputPath = join(rootDir, "test_report.json");
const sectionName = "CAP Tests";
const sectionMarker = "cap_tests";

function round(n, digits) {
  const f = 10 ** digits;
  return Math.round(n * f) / f;
}

function readCoverage() {
  const finalPath = join(coverageDir, "coverage-final.json");
  if (!existsSync(finalPath)) return null;
  let data;
  try {
    data = JSON.parse(readFileSync(finalPath, "utf8"));
  } catch {
    return null;
  }

  let total = 0;
  let covered = 0;
  for (const file of Object.values(data)) {
    const s = file?.s ?? {};
    for (const v of Object.values(s)) {
      total += 1;
      if (v > 0) covered += 1;
    }
  }
  if (!total) return null;
  return round((covered / total) * 100, 2);
}

// Read test results
if (!existsSync(resultsPath)) {
  console.error("No .test-results.json found — did the test reporter run?");
  process.exit(1);
}

const results = JSON.parse(readFileSync(resultsPath, "utf8"));
const { total, passed, failed, skipped, tests } = results;
const score = total ? round((passed / total) * 100, 2) : 0.0;

const section = {
  name: sectionName,
  marker: sectionMarker,
  total,
  passed,
  failed,
  skipped,
  score,
  tests,
};

const summary = { total, passed, failed, score };
const coverage = readCoverage();
if (coverage !== null) summary.coverage = coverage;

const report = { summary, sections: [section] };

writeFileSync(outputPath, `${JSON.stringify(report, null, 2)}\n`);

// Clean up intermediate file
unlinkSync(resultsPath);

console.log(`Report written to ${outputPath}`);
