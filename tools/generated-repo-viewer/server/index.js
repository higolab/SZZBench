import express from "express";
import cors from "cors";
import path from "node:path";
import fs from "node:fs/promises";
import fssync from "node:fs";
import { fileURLToPath } from "node:url";
import { execFile } from "node:child_process";
import yaml from "js-yaml";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const viewerRoot = path.resolve(__dirname, "..");
const projectRoot = path.resolve(viewerRoot, "..", "..");
const generatedRoot = path.join(projectRoot, "generated-input-repos");

const app = express();
const port = Number(process.env.SZZBENCH_REPO_VIEWER_PORT || 4174);
const serveDist = process.argv.includes("--serve-dist");

app.use(cors());
app.use(express.json({ limit: "2mb" }));

function normalizeForClient(absPath) {
  return path.relative(projectRoot, absPath).replaceAll(path.sep, "/");
}

function assertInsideProject(absPath) {
  const resolved = path.resolve(absPath);
  const rel = path.relative(projectRoot, resolved);
  if (rel.startsWith("..") || path.isAbsolute(rel)) {
    throw new Error("Path escapes the SZZBench project root.");
  }
  return resolved;
}

function resolveTarget(target) {
  if (!target || typeof target !== "string") {
    throw new Error("Missing target.");
  }

  const raw = target.replaceAll("\\", "/");
  if (path.isAbsolute(raw)) {
    return assertInsideProject(raw);
  }

  return assertInsideProject(path.join(projectRoot, raw));
}

function repoDirFromTarget(target) {
  const generatedDir = resolveTarget(target);
  const repoDir = path.join(generatedDir, "repo");
  const gitDir = path.join(repoDir, ".git");
  if (!fssync.existsSync(gitDir)) {
    throw new Error(`Not a generated repository directory: ${target}`);
  }
  return { generatedDir, repoDir };
}

async function readJsonIfExists(filePath) {
  try {
    const text = await fs.readFile(filePath, "utf8");
    return JSON.parse(text);
  } catch {
    return null;
  }
}

async function readYamlIfExists(filePath) {
  try {
    const text = await fs.readFile(filePath, "utf8");
    return yaml.load(text);
  } catch {
    return null;
  }
}

async function readScenarioMetadata(metadataDir) {
  const graphPath = path.join(metadataDir, "scenario.graph.yml");
  const classicPath = path.join(metadataDir, "scenario.yml");
  if (fssync.existsSync(graphPath)) {
    return {
      scenario: await readYamlIfExists(graphPath),
      scenarioPath: graphPath,
      scenarioFile: "scenario.graph.yml",
      scenarioKind: "graph"
    };
  }
  if (fssync.existsSync(classicPath)) {
    return {
      scenario: await readYamlIfExists(classicPath),
      scenarioPath: classicPath,
      scenarioFile: "scenario.yml",
      scenarioKind: "classic"
    };
  }
  return {
    scenario: null,
    scenarioPath: null,
    scenarioFile: null,
    scenarioKind: "unknown"
  };
}

function runGit(repoDir, args, options = {}) {
  return new Promise((resolve, reject) => {
    execFile("git", args, {
      cwd: repoDir,
      encoding: "utf8",
      maxBuffer: options.maxBuffer || 20 * 1024 * 1024
    }, (error, stdout, stderr) => {
      if (error) {
        reject(new Error((stderr || stdout || error.message).trim()));
        return;
      }
      resolve(stdout);
    });
  });
}

function parseGitLog(raw, commitMap) {
  const hashToLogical = new Map();
  for (const [logicalId, entry] of Object.entries(commitMap || {})) {
    if (entry && entry.hash) {
      hashToLogical.set(entry.hash, logicalId);
    }
  }

  return raw.trim().split("\n").filter(Boolean).map((line) => {
    const [hash, parentsRaw, authorName, authorEmail, authoredDate, subject] = line.split("\x01");
    const parents = parentsRaw ? parentsRaw.split(" ").filter(Boolean) : [];
    return {
      hash,
      shortHash: hash.slice(0, 12),
      logicalId: hashToLogical.get(hash) || null,
      parents,
      authorName,
      authorEmail,
      authoredDate,
      subject
    };
  });
}

async function findGeneratedRepositories() {
  const results = [];

  async function walk(dir, depth) {
    if (depth > 4) return;
    let entries;
    try {
      entries = await fs.readdir(dir, { withFileTypes: true });
    } catch {
      return;
    }

    const hasRepo = entries.some(e => e.isDirectory() && e.name === "repo");
    if (hasRepo && fssync.existsSync(path.join(dir, "repo", ".git"))) {
      const metadataDir = path.join(dir, "metadata");
      const commitMapPath = path.join(metadataDir, "commit-map.json");
      const verifyPath = path.join(metadataDir, "verify-result.json");
      const scenarioInfo = await readScenarioMetadata(metadataDir);
      const scenario = scenarioInfo.scenario;
      const meta = scenario?.meta || {};
      results.push({
        target: normalizeForClient(dir),
        id: meta.id || path.basename(path.dirname(dir)) || path.basename(dir),
        title: meta.title || "",
        category: meta.category || "",
        generatedDir: normalizeForClient(dir),
        repoDir: normalizeForClient(path.join(dir, "repo")),
        metadataDir: normalizeForClient(metadataDir),
        hasScenario: Boolean(scenarioInfo.scenarioPath),
        scenarioKind: scenarioInfo.scenarioKind,
        scenarioFile: scenarioInfo.scenarioFile,
        hasCommitMap: fssync.existsSync(commitMapPath),
        hasVerifyResult: fssync.existsSync(verifyPath)
      });
      return;
    }

    for (const entry of entries) {
      if (entry.isDirectory() && entry.name !== ".git" && !entry.name.startsWith(".")) {
        await walk(path.join(dir, entry.name), depth + 1);
      }
    }
  }

  await walk(generatedRoot, 0);
  results.sort((a, b) => a.target.localeCompare(b.target));
  return results;
}

function collectOracleBadgesForCommits(scenario, commitMap) {
  const byLogical = {};
  const byHash = {};
  const bugs = Array.isArray(scenario?.bugs) ? scenario.bugs : [];

  function add(logicalId, badge) {
    if (!logicalId) return;
    if (!byLogical[logicalId]) byLogical[logicalId] = [];
    byLogical[logicalId].push(badge);
    const hash = commitMap?.[logicalId]?.hash;
    if (hash) {
      if (!byHash[hash]) byHash[hash] = [];
      byHash[hash].push(badge);
    }
  }

  for (const bug of bugs) {
    const bugId = bug.id || "bug";
    const bicEntries = Array.isArray(bug.bug_introducing_commits) ? bug.bug_introducing_commits : [];
    const bfcEntries = Array.isArray(bug.bug_fixing_commits) ? bug.bug_fixing_commits : [];
    for (const bic of bicEntries) {
      if (typeof bic === "string") add(bic, { kind: "BIC", bugId });
      else if (bic?.commit) add(bic.commit, { kind: "BIC", bugId, role: bic.role });
    }
    add(bug.bug_fixing_commit, { kind: "BFC", bugId });
    for (const bfc of bfcEntries) {
      if (typeof bfc === "string") add(bfc, { kind: "BFC", bugId });
      else if (bfc?.commit) add(bfc.commit, { kind: "BFC", bugId, role: bfc.role });
    }
  }

  return { byLogical, byHash };
}

app.get("/api/health", (req, res) => {
  res.json({
    ok: true,
    projectRoot: normalizeForClient(projectRoot),
    generatedRoot: normalizeForClient(generatedRoot)
  });
});

app.get("/api/repositories", async (req, res) => {
  try {
    const repositories = await findGeneratedRepositories();
    res.json({ repositories });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get("/api/repository", async (req, res) => {
  try {
    const { generatedDir, repoDir } = repoDirFromTarget(req.query.target);
    const metadataDir = path.join(generatedDir, "metadata");
    const commitMapPath = path.join(metadataDir, "commit-map.json");
    const graphMapPath = path.join(metadataDir, "graph-map.json");
    const verifyResultPath = path.join(metadataDir, "verify-result.json");
    const validationResultPath = path.join(metadataDir, "validation-result.json");
    const generationLogPath = path.join(metadataDir, "generation.log");

    const scenarioInfo = await readScenarioMetadata(metadataDir);
    const scenario = scenarioInfo.scenario;
    const commitMap = await readJsonIfExists(commitMapPath) || {};
    const graphMap = await readJsonIfExists(graphMapPath);
    const verifyResult = await readJsonIfExists(verifyResultPath);
    const validationResult = await readJsonIfExists(validationResultPath);

    let generationLog = "";
    try {
      generationLog = await fs.readFile(generationLogPath, "utf8");
    } catch {
      generationLog = "";
    }

    const logRaw = await runGit(repoDir, ["log", "--reverse", "--format=%H%x01%P%x01%an%x01%ae%x01%aI%x01%s"]);
    const commits = parseGitLog(logRaw, commitMap);
    const oracleBadges = collectOracleBadgesForCommits(scenario, commitMap);

    res.json({
      generatedDir: normalizeForClient(generatedDir),
      repoDir: normalizeForClient(repoDir),
      metadataDir: normalizeForClient(metadataDir),
      scenarioKind: scenarioInfo.scenarioKind,
      scenarioFile: scenarioInfo.scenarioFile,
      scenario,
      commitMap,
      graphMap,
      commits,
      oracleBadges,
      verifyResult,
      validationResult,
      generationLog
    });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

app.get("/api/tree", async (req, res) => {
  try {
    const { repoDir } = repoDirFromTarget(req.query.target);
    const commit = String(req.query.commit || "");
    if (!commit) throw new Error("Missing commit.");
    const raw = await runGit(repoDir, ["ls-tree", "-r", "--name-only", commit]);
    const files = raw.trim().split("\n").filter(Boolean);
    res.json({ files });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

app.get("/api/file", async (req, res) => {
  try {
    const { repoDir } = repoDirFromTarget(req.query.target);
    const commit = String(req.query.commit || "");
    const file = String(req.query.file || "");
    if (!commit || !file) throw new Error("Missing commit or file.");
    const content = await runGit(repoDir, ["show", `${commit}:${file}`]);
    res.json({ content });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

app.get("/api/diff", async (req, res) => {
  try {
    const { repoDir } = repoDirFromTarget(req.query.target);
    const commit = String(req.query.commit || "");
    const file = String(req.query.file || "");
    if (!commit) throw new Error("Missing commit.");
    let args;
    if (file) {
      args = ["show", "--format=", "--find-renames", "--find-copies", commit, "--", file];
    } else {
      args = ["show", "--format=", "--find-renames", "--find-copies", commit];
    }
    const diff = await runGit(repoDir, args, { maxBuffer: 30 * 1024 * 1024 });
    res.json({ diff });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

app.get("/api/blame", async (req, res) => {
  try {
    const { repoDir } = repoDirFromTarget(req.query.target);
    const commit = String(req.query.commit || "");
    const file = String(req.query.file || "");
    if (!commit || !file) throw new Error("Missing commit or file.");

    const raw = await runGit(repoDir, ["blame", "--line-porcelain", commit, "--", file], {
      maxBuffer: 30 * 1024 * 1024
    });
    const lines = [];
    let current = null;
    for (const row of raw.split("\n")) {
      if (/^[0-9a-f]{40}\s+/.test(row)) {
        const parts = row.split(" ");
        current = {
          hash: parts[0],
          originalLine: Number(parts[1]),
          finalLine: Number(parts[2]),
          author: "",
          summary: "",
          content: ""
        };
      } else if (current && row.startsWith("author ")) {
        current.author = row.slice("author ".length);
      } else if (current && row.startsWith("summary ")) {
        current.summary = row.slice("summary ".length);
      } else if (current && row.startsWith("\t")) {
        current.content = row.slice(1);
        lines.push(current);
        current = null;
      }
    }
    res.json({ lines });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

if (serveDist) {
  const distDir = path.join(viewerRoot, "dist");
  app.use(express.static(distDir));
  app.use((req, res) => {
    res.sendFile(path.join(distDir, "index.html"));
  });
}

app.listen(port, "127.0.0.1", () => {
  console.log(`[generated-repo-viewer] API listening on http://127.0.0.1:${port}`);
  console.log(`[generated-repo-viewer] project root: ${projectRoot}`);
});
