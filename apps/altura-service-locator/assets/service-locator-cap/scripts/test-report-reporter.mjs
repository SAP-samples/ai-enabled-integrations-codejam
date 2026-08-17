/**
 * Custom reporter for Node.js native test runner (`node --test`).
 * Collects test results and writes them to .test-results.json.
 *
 * This reporter intentionally does NOT read coverage data — coverage is
 * written by c8 after the node process exits. A separate post-step script
 * (write-test-report.mjs) merges test results with coverage into the final
 * test_report.json.
 *
 * Usage (as additional reporter alongside the default "spec" output):
 *   node --test \
 *     --test-reporter=spec --test-reporter-destination=stdout \
 *     --test-reporter=./scripts/test-report-reporter.mjs --test-reporter-destination=stdout \
 *     test/
 */

import { writeFileSync } from "node:fs";
import { join } from "node:path";

const rootDir = process.cwd();
const outputPath = join(rootDir, ".test-results.json");

function round(n, digits) {
  const f = 10 ** digits;
  return Math.round(n * f) / f;
}

/**
 * Node.js test reporter — async generator function.
 *
 * Events of interest:
 *   test:start  — fired for every test/suite with { name, nesting, testId }
 *   test:pass   — { name, nesting, testId, details: { type, duration_ms } }
 *   test:fail   — same shape as test:pass
 *
 * `details.type` is "suite" for describe blocks and "test" for leaf tests.
 * `nesting` is the depth (0 = top-level file, 1 = first describe, etc.).
 *
 * We track the suite ancestry per-file to reconstruct full hierarchical test
 * names like "describe > nested describe > test name".
 */
export default async function* reporter(source) {
  // Per-file suite stacks keyed by file path
  const suiteStacks = new Map();
  const tests = [];
  let passed = 0;
  let failed = 0;
  let skipped = 0;
  let total = 0;

  for await (const event of source) {
    switch (event.type) {
      case "test:start": {
        const { data } = event;
        const file = data.file || "";
        if (!suiteStacks.has(file)) suiteStacks.set(file, []);
        const stack = suiteStacks.get(file);
        // Adjust stack to current nesting level then push this name
        // nesting=0 is the file-level implicit suite which we skip in names
        stack.length = data.nesting;
        stack.push(data.name);
        break;
      }

      case "test:pass": {
        const { data } = event;
        // Skip suite-level (describe block) completions
        if (data.details?.type === "suite") break;
        // Skip file-level wrapper (nesting=0, name is the file path)
        if (data.nesting === 0 && data.name === data.file) break;

        total++;
        if (data.skip || data.todo) {
          skipped++;
          tests.push({
            name: buildFullName(data, suiteStacks),
            outcome: "skipped",
            duration: round((data.details?.duration_ms || 0) / 1000, 4),
          });
        } else {
          passed++;
          tests.push({
            name: buildFullName(data, suiteStacks),
            outcome: "passed",
            duration: round((data.details?.duration_ms || 0) / 1000, 4),
          });
        }
        break;
      }

      case "test:fail": {
        const { data } = event;
        // Skip suite-level (describe block) failures
        if (data.details?.type === "suite") break;
        // Skip file-level wrapper
        if (data.nesting === 0 && data.name === data.file) break;

        total++;
        if (data.skip || data.todo) {
          skipped++;
          tests.push({
            name: buildFullName(data, suiteStacks),
            outcome: "skipped",
            duration: round((data.details?.duration_ms || 0) / 1000, 4),
          });
        } else {
          failed++;
          tests.push({
            name: buildFullName(data, suiteStacks),
            outcome: "failed",
            duration: round((data.details?.duration_ms || 0) / 1000, 4),
          });
        }
        break;
      }

      default:
        break;
    }
  }

  // Write intermediate results (coverage is merged in the post-step)
  const results = { total, passed, failed, skipped, tests };
  writeFileSync(outputPath, `${JSON.stringify(results)}\n`);

  yield "";
}

/**
 * Build a full test name from the suite stack.
 * The stack at the time of test:pass/fail contains the path from describe
 * blocks down to the test itself. We join with " > " for a readable full name.
 */
function buildFullName(data, suiteStacks) {
  const file = data.file || "";
  const stack = suiteStacks.get(file);
  if (stack && stack.length > 0) {
    // The stack should include the describe hierarchy + the test name itself.
    // Since test:start fires before test:pass, the stack at nesting `data.nesting`
    // should be [file-wrapper, describe1, describe2, ..., testName].
    // We skip the first entry if it's the file path (nesting=0 file wrapper).
    const names = stack.slice(0, data.nesting + 1);
    const filtered = names.filter((n) => n !== file);
    if (filtered.length > 0) return filtered.join(" > ");
  }
  return data.name || "unnamed test";
}
