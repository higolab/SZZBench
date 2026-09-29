import express from 'express';
import { execFile } from 'node:child_process';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import yaml from 'js-yaml';

const app = express();
const PORT = Number(process.env.PORT || 3001);
const thisFile = fileURLToPath(import.meta.url);
const serverDir = path.dirname(thisFile);
const editorDir = path.resolve(serverDir, '..');
// SZZBENCH_REPO_ROOT points the editor at another checkout (the tests use a scratch copy).
const repoRoot = path.resolve(process.env.SZZBENCH_REPO_ROOT || path.resolve(editorDir, '..', '..'));
const scenariosDir = path.join(repoRoot, 'scenarios');
const serveStatic = process.argv.includes('--serve-static');
// The Python that runs SZZBench's own validator and README renderer on save (issue #97).
const python = process.env.SZZBENCH_PYTHON || 'python3';
const TIERS = ['control', 'discriminating'];
const execFileAsync = promisify(execFile);

app.use(express.json({ limit: '10mb' }));

function assertScenarioId(id) {
  if (typeof id !== 'string' || !/^SZZ-\d{4}$/.test(id)) {
    const err = new Error('Scenario id must match SZZ-0001 style.');
    err.status = 400;
    throw err;
  }
}

function safeScenarioDir(id) {
  assertScenarioId(id);
  const dir = path.resolve(scenariosDir, id);
  if (!dir.startsWith(path.resolve(scenariosDir) + path.sep)) {
    const err = new Error('Invalid scenario path.');
    err.status = 400;
    throw err;
  }
  return dir;
}

async function pathExists(p) {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

async function listScenarioIds() {
  if (!(await pathExists(scenariosDir))) {
    return [];
  }
  const entries = await fs.readdir(scenariosDir, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isDirectory() && /^SZZ-\d{4}$/.test(entry.name))
    .map((entry) => entry.name)
    .sort();
}

function buildIndexEntryFromScenario(scenario) {
  const meta = scenario?.meta || {};
  const entry = {
    id: meta.id,
    title: meta.title || '',
    slug: meta.slug || ''
  };
  if (meta.category_code) entry.category_code = meta.category_code;
  Object.assign(entry, {
    category: meta.category || '',
    factors: Array.isArray(meta.factors) ? meta.factors : [],
    difficulty: meta.difficulty || '',
    status: meta.status || 'draft',
    path: `scenarios/${meta.id}/scenario.yml`
  });
  return entry;
}

/**
 * Put `entry` into index.yml by editing text, not by re-dumping the file.
 *
 * A re-dump re-indented every entry (3,764 of 1,881 lines changed for one save) and
 * re-quoted titles; now an existing entry's lines are replaced, a new entry is
 * inserted before the first larger id, and every other line stays byte for byte.
 */
function renderIndexEntry(entry) {
  return yaml.dump([entry], { noArrayIndent: true, quotingType: "'", lineWidth: -1, noRefs: true, sortKeys: false });
}

function spliceIndexEntry(text, entry) {
  const blockLines = renderIndexEntry(entry).replace(/\n$/, '').split('\n');
  const lines = (text.endsWith('\n') ? text.slice(0, -1) : text).split('\n');
  if (!lines.some((line) => /^scenarios:\s*$/.test(line))) {
    if (lines.length === 1 && lines[0] === '') lines.pop();
    lines.push('scenarios:');
  }
  const starts = [];
  lines.forEach((line, index) => {
    if (/^- id: /.test(line)) starts.push(index);
  });
  const idAt = (index) => String((yaml.load(lines[index].slice(2)) || {}).id);
  const endOf = (k) => {
    if (k + 1 < starts.length) return starts[k + 1];
    for (let index = starts[k] + 1; index < lines.length; index++) {
      if (/^\S/.test(lines[index]) && !lines[index].startsWith('- ')) return index;
    }
    return lines.length;
  };
  const existing = starts.findIndex((start) => idAt(start) === String(entry.id));
  if (existing >= 0) {
    lines.splice(starts[existing], endOf(existing) - starts[existing], ...blockLines);
  } else {
    const after = starts.findIndex((start) => idAt(start).localeCompare(String(entry.id)) > 0);
    const at = after >= 0 ? starts[after] : starts.length ? endOf(starts.length - 1) : lines.length;
    lines.splice(at, 0, ...blockLines);
  }
  return lines.join('\n') + '\n';
}

async function updateIndexYaml(indexEntry) {
  await fs.mkdir(scenariosDir, { recursive: true });
  const indexPath = path.join(scenariosDir, 'index.yml');
  const current = (await pathExists(indexPath)) ? await fs.readFile(indexPath, 'utf8') : 'scenarios:\n';
  await fs.writeFile(indexPath, spliceIndexEntry(current, indexEntry), 'utf8');
}

/** Run `python -m szzbench.cli <args>` from this checkout's src/. */
async function szzbench(args) {
  const env = {
    ...process.env,
    PYTHONPATH: [path.join(repoRoot, 'src'), process.env.PYTHONPATH].filter(Boolean).join(path.delimiter)
  };
  try {
    const { stdout, stderr } = await execFileAsync(python, ['-m', 'szzbench.cli', ...args],
      { env, cwd: repoRoot, maxBuffer: 16 * 1024 * 1024 });
    return { code: 0, stdout, stderr };
  } catch (err) {
    if (typeof err.code === 'number') return { code: err.code, stdout: err.stdout || '', stderr: err.stderr || '' };
    const failure = new Error(`Cannot run SZZBench with ${python}: ${err.message}. Set SZZBENCH_PYTHON to a Python that has SZZBench's dependencies.`);
    failure.status = 500;
    throw failure;
  }
}

/**
 * Write the scenario to a scratch copy of the layout, insert the generated README
 * header there and run `validate --lint` on it: what SZZBench itself would say
 * about the files, before any of them reaches scenarios/ (issue #97).
 */
async function stageAndValidate(id, scenarioYaml, readme) {
  const staging = await fs.mkdtemp(path.join(os.tmpdir(), 'szzbench-editor-'));
  try {
    const stagedScenarios = path.join(staging, 'scenarios');
    const stagedAdvanced = path.join(staging, 'advanced-scenarios');
    const stagedDir = path.join(stagedScenarios, id);
    await fs.mkdir(stagedDir, { recursive: true });
    await fs.mkdir(stagedAdvanced, { recursive: true });
    await fs.writeFile(path.join(stagedDir, 'scenario.yml'), scenarioYaml.endsWith('\n') ? scenarioYaml : `${scenarioYaml}\n`, 'utf8');
    await fs.writeFile(path.join(stagedDir, 'README.md'), readme.endsWith('\n') ? readme : `${readme}\n`, 'utf8');
    const header = await szzbench(['readme', '--write', '--scenarios-root', stagedScenarios,
      '--advanced-scenarios-root', stagedAdvanced, stagedDir]);
    if (header.code !== 0) {
      const err = new Error(`szzbench readme --write failed: ${(header.stderr || header.stdout).trim()}`);
      err.status = 500;
      throw err;
    }
    const validation = await szzbench(['validate', '--lint', '--json', path.join(stagedDir, 'scenario.yml')]);
    let report;
    try {
      report = JSON.parse(validation.stdout);
    } catch {
      const err = new Error(`szzbench validate did not report JSON: ${(validation.stderr || validation.stdout).trim()}`);
      err.status = 500;
      throw err;
    }
    return {
      report,
      scenarioYaml: await fs.readFile(path.join(stagedDir, 'scenario.yml'), 'utf8'),
      readme: await fs.readFile(path.join(stagedDir, 'README.md'), 'utf8')
    };
  } finally {
    await fs.rm(staging, { recursive: true, force: true });
  }
}

app.get('/api/health', (_req, res) => {
  res.json({ ok: true, repoRoot, scenariosDir });
});

app.get('/api/scenarios', async (_req, res, next) => {
  try {
    const ids = await listScenarioIds();
    const last = ids.length === 0 ? 0 : Math.max(...ids.map((id) => Number(id.slice(4))));
    const nextId = `SZZ-${String(last + 1).padStart(4, '0')}`;
    res.json({ ids, nextId, scenariosDir });
  } catch (err) {
    next(err);
  }
});

/** The checks every request that produces files passes: save and preview alike. */
function parseScenarioRequest(body) {
  const { id, scenarioYaml, readme } = body || {};
  assertScenarioId(id);
  if (typeof scenarioYaml !== 'string' || scenarioYaml.trim() === '') {
    const err = new Error('scenarioYaml is required.');
    err.status = 400;
    throw err;
  }
  if (typeof readme !== 'string' || readme.trim() === '') {
    const err = new Error('readme is required.');
    err.status = 400;
    throw err;
  }

  let scenario;
  try {
    scenario = yaml.load(scenarioYaml);
  } catch (parseErr) {
    const err = new Error(`scenarioYaml is not valid YAML: ${parseErr.message}`);
    err.status = 400;
    throw err;
  }

  if (!scenario || scenario?.meta?.id !== id) {
    const err = new Error('scenarioYaml meta.id must match the requested id.');
    err.status = 400;
    throw err;
  }
  if (!TIERS.includes(scenario?.meta?.tier)) {
    const err = new Error(`Choose meta.tier (${TIERS.join(' or ')}) before saving: it declares what the scenario is for.`);
    err.status = 400;
    throw err;
  }
  return { id, scenarioYaml, readme, scenario };
}

function refuseErrors(res, staged, what) {
  const findings = Array.isArray(staged.report.findings) ? staged.report.findings : [];
  if (staged.report.errors > 0) {
    res.status(400).json({
      ok: false,
      error: `szzbench validate --lint found ${staged.report.errors} error(s); nothing was ${what}.`,
      findings
    });
    return null;
  }
  return findings;
}

// What Save would write, without writing it: the Download buttons use this, so a
// downloaded README carries the generated header too (PR #101 review).
app.post('/api/scenarios/preview', async (req, res, next) => {
  try {
    const { id, scenarioYaml, readme, scenario } = parseScenarioRequest(req.body);
    const staged = await stageAndValidate(id, scenarioYaml, readme);
    const findings = refuseErrors(res, staged, 'rendered');
    if (findings === null) return;
    res.json({
      ok: true,
      id,
      findings,
      scenarioYaml: staged.scenarioYaml,
      readme: staged.readme,
      indexEntry: renderIndexEntry(buildIndexEntryFromScenario(scenario))
    });
  } catch (err) {
    next(err);
  }
});

app.post('/api/scenarios/save', async (req, res, next) => {
  try {
    const { id, scenarioYaml, readme, scenario } = parseScenarioRequest(req.body);
    const { overwrite } = req.body || {};

    const scenarioDir = safeScenarioDir(id);
    if (await pathExists(scenarioDir)) {
      const existing = await fs.readdir(scenarioDir);
      if (existing.length > 0 && !overwrite) {
        const err = new Error(`${id} already exists. Enable overwrite to replace it.`);
        err.status = 409;
        throw err;
      }
    }

    const staged = await stageAndValidate(id, scenarioYaml, readme);
    const findings = refuseErrors(res, staged, 'saved');
    if (findings === null) return;

    await fs.mkdir(scenarioDir, { recursive: true });
    await fs.writeFile(path.join(scenarioDir, 'scenario.yml'), staged.scenarioYaml, 'utf8');
    await fs.writeFile(path.join(scenarioDir, 'README.md'), staged.readme, 'utf8');

    const indexEntry = buildIndexEntryFromScenario(scenario);
    await updateIndexYaml(indexEntry);

    res.json({
      ok: true,
      id,
      findings,
      files: [
        path.relative(repoRoot, path.join(scenarioDir, 'scenario.yml')),
        path.relative(repoRoot, path.join(scenarioDir, 'README.md')),
        path.relative(repoRoot, path.join(scenariosDir, 'index.yml'))
      ]
    });
  } catch (err) {
    next(err);
  }
});

if (serveStatic) {
  const distDir = path.join(editorDir, 'dist');
  app.use(express.static(distDir));
  app.use((_req, res) => {
    res.sendFile(path.join(distDir, 'index.html'));
  });
}

app.use((err, _req, res, _next) => {
  const status = err.status || 500;
  res.status(status).json({ ok: false, error: err.message || String(err) });
});

app.listen(PORT, '127.0.0.1', () => {
  console.log(`[scenario-editor] API server listening on http://127.0.0.1:${PORT}`);
  console.log(`[scenario-editor] repoRoot=${repoRoot}`);
});
