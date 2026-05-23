import express from 'express';
import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import yaml from 'js-yaml';

const app = express();
const PORT = Number(process.env.PORT || 3001);
const thisFile = fileURLToPath(import.meta.url);
const serverDir = path.dirname(thisFile);
const editorDir = path.resolve(serverDir, '..');
const repoRoot = path.resolve(editorDir, '..', '..');
const scenariosDir = path.join(repoRoot, 'scenarios');
const serveStatic = process.argv.includes('--serve-static');

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
  return {
    id: meta.id,
    title: meta.title || '',
    slug: meta.slug || '',
    category: meta.category || '',
    factors: Array.isArray(meta.factors) ? meta.factors : [],
    difficulty: meta.difficulty || '',
    status: meta.status || 'draft',
    path: `scenarios/${meta.id}/scenario.yml`
  };
}

async function updateIndexYaml(indexEntry) {
  await fs.mkdir(scenariosDir, { recursive: true });
  const indexPath = path.join(scenariosDir, 'index.yml');
  let data = { scenarios: [] };

  if (await pathExists(indexPath)) {
    const current = await fs.readFile(indexPath, 'utf8');
    const parsed = yaml.load(current);
    if (parsed && typeof parsed === 'object' && Array.isArray(parsed.scenarios)) {
      data = parsed;
    }
  }

  data.scenarios = data.scenarios.filter((entry) => entry && entry.id !== indexEntry.id);
  data.scenarios.push(indexEntry);
  data.scenarios.sort((a, b) => String(a.id).localeCompare(String(b.id)));

  const text = yaml.dump(data, {
    lineWidth: 120,
    noRefs: true,
    sortKeys: false,
    quotingType: '"',
    forceQuotes: false
  });
  await fs.writeFile(indexPath, text, 'utf8');
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

app.post('/api/scenarios/save', async (req, res, next) => {
  try {
    const { id, scenarioYaml, readme, overwrite } = req.body || {};
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

    const scenarioDir = safeScenarioDir(id);
    if (await pathExists(scenarioDir)) {
      const existing = await fs.readdir(scenarioDir);
      if (existing.length > 0 && !overwrite) {
        const err = new Error(`${id} already exists. Enable overwrite to replace it.`);
        err.status = 409;
        throw err;
      }
    }

    await fs.mkdir(scenarioDir, { recursive: true });
    await fs.writeFile(path.join(scenarioDir, 'scenario.yml'), scenarioYaml.endsWith('\n') ? scenarioYaml : `${scenarioYaml}\n`, 'utf8');
    await fs.writeFile(path.join(scenarioDir, 'README.md'), readme.endsWith('\n') ? readme : `${readme}\n`, 'utf8');

    const indexEntry = buildIndexEntryFromScenario(scenario);
    await updateIndexYaml(indexEntry);

    res.json({
      ok: true,
      id,
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
