import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type RepositorySummary = {
  target: string;
  id: string;
  title: string;
  category: string;
  generatedDir: string;
  repoDir: string;
  metadataDir: string;
  hasScenario: boolean;
  scenarioKind: "classic" | "graph" | "unknown";
  scenarioFile: string | null;
  hasCommitMap: boolean;
  hasVerifyResult: boolean;
};

type CommitInfo = {
  hash: string;
  shortHash: string;
  logicalId: string | null;
  parents: string[];
  authorName: string;
  authorEmail: string;
  authoredDate: string;
  subject: string;
};

type Badge = {
  kind: "BIC" | "BFC";
  bugId: string;
  role?: string;
};

type RepositoryDetail = {
  generatedDir: string;
  repoDir: string;
  metadataDir: string;
  scenario: any;
  scenarioKind: "classic" | "graph" | "unknown";
  scenarioFile: string | null;
  commitMap: Record<string, { hash: string; message?: string; role?: string; date?: string; branch?: string; parents?: string[] }>;
  graphMap: any;
  commits: CommitInfo[];
  oracleBadges: {
    byLogical: Record<string, Badge[]>;
    byHash: Record<string, Badge[]>;
  };
  verifyResult: any;
  validationResult: any;
  generationLog: string;
};

type BlameLine = {
  hash: string;
  originalLine: number;
  finalLine: number;
  author: string;
  summary: string;
  content: string;
};

const API = "";

function short(value: string | null | undefined, len = 12): string {
  return value ? value.slice(0, len) : "";
}

function roleOfCommit(detail: RepositoryDetail | null, commit: CommitInfo): string {
  if (!detail || !commit.logicalId) return "";
  return detail.commitMap?.[commit.logicalId]?.role || "";
}

function branchOfCommit(detail: RepositoryDetail | null, commit: CommitInfo): string {
  if (!detail || !commit.logicalId) return "";
  return detail.commitMap?.[commit.logicalId]?.branch || "";
}

function commitIdOf(entry: any): string {
  if (typeof entry === "string") return entry;
  if (entry && typeof entry.commit === "string") return entry.commit;
  return "";
}

function roleOfRef(entry: any): string {
  if (entry && typeof entry === "object" && typeof entry.role === "string") return entry.role;
  return "";
}

function bicEntriesOf(bug: any): any[] {
  return Array.isArray(bug?.bug_introducing_commits) ? bug.bug_introducing_commits : [];
}

function bfcEntriesOf(bug: any): any[] {
  if (Array.isArray(bug?.bug_fixing_commits)) return bug.bug_fixing_commits;
  return bug?.bug_fixing_commit ? [bug.bug_fixing_commit] : [];
}

function faultEntriesOf(bug: any): any[] {
  if (Array.isArray(bug?.faults)) return bug.faults.filter((item: any) => item && typeof item === "object");
  return bug?.fault && typeof bug.fault === "object" ? [bug.fault] : [];
}

function fixEntriesOf(bug: any): any[] {
  if (Array.isArray(bug?.fixes)) return bug.fixes.filter((item: any) => item && typeof item === "object");
  return bug?.fix && typeof bug.fix === "object" ? [bug.fix] : [];
}

function statementOf(entry: any): string {
  return String(entry?.statement || entry?.missing_statement || entry?.added_statement || "");
}

function formatCommitRef(entry: any, commitMap: RepositoryDetail["commitMap"]): string {
  const id = commitIdOf(entry);
  if (!id) return "";
  const hash = commitMap?.[id]?.hash ? ` (${short(commitMap[id].hash)})` : "";
  const role = roleOfRef(entry);
  return `${id}${role ? `:${role}` : ""}${hash}`;
}

function downloadText(name: string, text: string) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function App() {
  const [repositories, setRepositories] = useState<RepositorySummary[]>([]);
  const [selectedTarget, setSelectedTarget] = useState<string>("");
  const [detail, setDetail] = useState<RepositoryDetail | null>(null);
  const [selectedCommit, setSelectedCommit] = useState<CommitInfo | null>(null);
  const [files, setFiles] = useState<string[]>([]);
  const [selectedFile, setSelectedFile] = useState<string>("");
  const [fileContent, setFileContent] = useState<string>("");
  const [diff, setDiff] = useState<string>("");
  const [blame, setBlame] = useState<BlameLine[]>([]);
  const [tab, setTab] = useState<"file" | "diff" | "blame" | "oracle" | "verify">("file");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");

  async function fetchJson<T>(url: string): Promise<T> {
    const response = await fetch(url);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Request failed: ${response.status}`);
    return data;
  }

  async function refreshRepositories() {
    setError("");
    try {
      const data = await fetchJson<{ repositories: RepositorySummary[] }>(`${API}/api/repositories`);
      setRepositories(data.repositories);
      if (!selectedTarget && data.repositories.length > 0) {
        setSelectedTarget(data.repositories[0].target);
      }
    } catch (e: any) {
      setError(e.message);
    }
  }

  useEffect(() => {
    refreshRepositories();
  }, []);

  useEffect(() => {
    if (!selectedTarget) return;
    loadRepository(selectedTarget);
  }, [selectedTarget]);

  useEffect(() => {
    if (!selectedTarget || !selectedCommit) return;
    loadTree(selectedTarget, selectedCommit.hash);
  }, [selectedTarget, selectedCommit?.hash]);

  useEffect(() => {
    if (!selectedTarget || !selectedCommit || !selectedFile) return;
    loadFileViews(selectedTarget, selectedCommit.hash, selectedFile);
  }, [selectedTarget, selectedCommit?.hash, selectedFile]);

  async function loadRepository(target: string) {
    setLoading(true);
    setError("");
    setDetail(null);
    setFiles([]);
    setSelectedFile("");
    setFileContent("");
    setDiff("");
    setBlame([]);
    try {
      const data = await fetchJson<RepositoryDetail>(`${API}/api/repository?target=${encodeURIComponent(target)}`);
      setDetail(data);
      const firstCommit = data.commits[0] || null;
      setSelectedCommit(firstCommit);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadTree(target: string, commit: string) {
    try {
      const data = await fetchJson<{ files: string[] }>(
        `${API}/api/tree?target=${encodeURIComponent(target)}&commit=${encodeURIComponent(commit)}`
      );
      setFiles(data.files);
      if (!data.files.includes(selectedFile)) {
        setSelectedFile(data.files[0] || "");
      }
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function loadFileViews(target: string, commit: string, file: string) {
    try {
      const [fileData, diffData, blameData] = await Promise.all([
        fetchJson<{ content: string }>(
          `${API}/api/file?target=${encodeURIComponent(target)}&commit=${encodeURIComponent(commit)}&file=${encodeURIComponent(file)}`
        ),
        fetchJson<{ diff: string }>(
          `${API}/api/diff?target=${encodeURIComponent(target)}&commit=${encodeURIComponent(commit)}&file=${encodeURIComponent(file)}`
        ),
        fetchJson<{ lines: BlameLine[] }>(
          `${API}/api/blame?target=${encodeURIComponent(target)}&commit=${encodeURIComponent(commit)}&file=${encodeURIComponent(file)}`
        )
      ]);
      setFileContent(fileData.content);
      setDiff(diffData.diff);
      setBlame(blameData.lines);
    } catch (e: any) {
      setError(e.message);
    }
  }

  const selectedRepo = repositories.find(r => r.target === selectedTarget) || null;
  const scenarioMeta = detail?.scenario?.meta || {};
  const bugs = Array.isArray(detail?.scenario?.bugs) ? detail?.scenario?.bugs : [];
  const selectedBadges = selectedCommit && detail
    ? detail.oracleBadges.byHash[selectedCommit.hash] || []
    : [];

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>SZZBench Generated Repository Viewer</h1>
          <p>
            generator が実際に作成した Git リポジトリを読み込み、
            commitごとのファイル状態・diff・blame・oracleを確認します。
          </p>
        </div>
        <button onClick={refreshRepositories}>Refresh</button>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <div className="layout">
        <aside className="sidebar">
          <section className="card">
            <h2>Generated repositories</h2>
            <select value={selectedTarget} onChange={(e) => setSelectedTarget(e.target.value)}>
              {repositories.map(repo => (
                <option key={repo.target} value={repo.target}>
                  {repo.id} {repo.title ? `- ${repo.title}` : ""} [{repo.scenarioKind}] ({repo.target})
                </option>
              ))}
            </select>
            <div className="muted stack-small">
              {repositories.length} generated repository candidate(s) found under generated-input-repos/.
            </div>
          </section>

          <section className="card">
            <h2>Scenario</h2>
            {detail ? (
              <div className="meta-grid">
                <span>ID</span><strong>{scenarioMeta.id || selectedRepo?.id || ""}</strong>
                <span>Title</span><div>{scenarioMeta.title || ""}</div>
                <span>Category</span><div>{scenarioMeta.category || ""}</div>
                <span>Difficulty</span><div>{scenarioMeta.difficulty || ""}</div>
                <span>Schema</span><div>{detail.scenarioKind}{detail.scenarioFile ? ` / ${detail.scenarioFile}` : ""}</div>
                <span>Repo</span><code>{detail.repoDir}</code>
              </div>
            ) : <p className="muted">No repository loaded.</p>}
          </section>

          <section className="card grow">
            <h2>Commits</h2>
            <div className="commit-list">
              {detail?.commits.map(commit => {
                const isSelected = commit.hash === selectedCommit?.hash;
                const badges = detail.oracleBadges.byHash[commit.hash] || [];
                return (
                  <button
                    key={commit.hash}
                    className={`commit-item ${isSelected ? "selected" : ""}`}
                    onClick={() => setSelectedCommit(commit)}
                  >
                    <div className="commit-line">
                      <strong>{commit.logicalId || short(commit.hash)}</strong>
                      <span>{[roleOfCommit(detail, commit), branchOfCommit(detail, commit)].filter(Boolean).join(" / ")}</span>
                    </div>
                    <div className="commit-subject">{commit.subject}</div>
                    <div className="commit-hash">{commit.shortHash}</div>
                    <div className="badges">
                      {badges.map((b, i) => (
                        <span key={i} className={`badge ${b.kind.toLowerCase()}`}>
                          {b.kind} {b.bugId}{b.role ? `:${b.role}` : ""}
                        </span>
                      ))}
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        </aside>

        <main className="main-panel">
          {loading && <div className="card">Loading...</div>}

          {detail && (
            <>
              <section className="card">
                <div className="section-header">
                  <div>
                    <h2>Selected commit</h2>
                    <p className="muted">
                      {selectedCommit?.logicalId || "(no logical id)"} / {selectedCommit?.shortHash}
                      {" "}— {selectedCommit?.subject}
                    </p>
                  </div>
                  <div className="badges">
                    {selectedBadges.map((b, i) => (
                      <span key={i} className={`badge ${b.kind.toLowerCase()}`}>
                        {b.kind} {b.bugId}{b.role ? `:${b.role}` : ""}
                      </span>
                    ))}
                  </div>
                </div>
              </section>

              <section className="workspace">
                <div className="card file-card">
                  <h2>Files at selected commit</h2>
                  <input
                    className="filter"
                    placeholder="Filter files..."
                    onChange={(e) => {
                      const query = e.target.value.toLowerCase();
                      document.querySelectorAll<HTMLButtonElement>(".file-button").forEach(btn => {
                        btn.style.display = btn.dataset.path?.toLowerCase().includes(query) ? "block" : "none";
                      });
                    }}
                  />
                  <div className="file-list">
                    {files.map(file => (
                      <button
                        key={file}
                        data-path={file}
                        className={`file-button ${selectedFile === file ? "selected" : ""}`}
                        onClick={() => setSelectedFile(file)}
                      >
                        {file}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="card viewer-card">
                  <div className="tabs">
                    <button className={tab === "file" ? "active" : ""} onClick={() => setTab("file")}>File content</button>
                    <button className={tab === "diff" ? "active" : ""} onClick={() => setTab("diff")}>Diff</button>
                    <button className={tab === "blame" ? "active" : ""} onClick={() => setTab("blame")}>Blame</button>
                    <button className={tab === "oracle" ? "active" : ""} onClick={() => setTab("oracle")}>Oracle</button>
                    <button className={tab === "verify" ? "active" : ""} onClick={() => setTab("verify")}>Verify</button>
                  </div>

                  {tab === "file" && (
                    <CodeViewer content={fileContent} selectedFile={selectedFile} bugs={bugs} selectedCommit={selectedCommit} />
                  )}

                  {tab === "diff" && (
                    <DiffViewer diff={diff} />
                  )}

                  {tab === "blame" && (
                    <BlameViewer lines={blame} commitMap={detail.commitMap} />
                  )}

                  {tab === "oracle" && (
                    <OracleViewer bugs={bugs} commitMap={detail.commitMap} />
                  )}

                  {tab === "verify" && (
                    <VerifyViewer detail={detail} />
                  )}
                </div>
              </section>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

function CodeViewer({
  content,
  selectedFile,
  bugs,
  selectedCommit
}: {
  content: string;
  selectedFile: string;
  bugs: any[];
  selectedCommit: CommitInfo | null;
}) {
  const highlightTexts = useMemo(() => {
    if (!selectedCommit) return [];
    const logicalId = selectedCommit.logicalId;
    const result: string[] = [];
    for (const bug of bugs) {
      for (const fault of faultEntriesOf(bug)) {
        const text = statementOf(fault);
        if (fault.commit === logicalId && fault.file === selectedFile && text) {
          result.push(text);
        }
      }
      for (const fix of fixEntriesOf(bug)) {
        const text = statementOf(fix);
        if (fix.commit === logicalId && fix.file === selectedFile && text) {
          result.push(text);
        }
      }
    }
    return result.map(normalizeText).filter(Boolean);
  }, [selectedCommit, bugs, selectedFile]);

  const lines = content.split("\n");
  return (
    <pre className="code-box">
      {lines.map((line, i) => {
        const normalizedLine = normalizeText(line);
        const highlighted = highlightTexts.some(text =>
          normalizedLine.length > 0 && (text.includes(normalizedLine) || normalizedLine.includes(text))
        );
        return (
          <div key={i} className={`code-line ${highlighted ? "highlight" : ""}`}>
            <span className="line-no">{i + 1}</span>
            <span>{line}</span>
          </div>
        );
      })}
    </pre>
  );
}

function DiffViewer({ diff }: { diff: string }) {
  return (
    <pre className="diff-box">
      {diff.split("\n").map((line, i) => {
        const cls =
          line.startsWith("+") && !line.startsWith("+++") ? "add" :
          line.startsWith("-") && !line.startsWith("---") ? "del" :
          line.startsWith("@@") ? "hunk" :
          "";
        return <div key={i} className={`diff-line ${cls}`}>{line}</div>;
      })}
    </pre>
  );
}

function BlameViewer({
  lines,
  commitMap
}: {
  lines: BlameLine[];
  commitMap: Record<string, { hash: string; role?: string }>;
}) {
  const hashToLogical = new Map<string, string>();
  for (const [logical, entry] of Object.entries(commitMap || {})) {
    if (entry.hash) hashToLogical.set(entry.hash, logical);
  }

  return (
    <div className="blame-box">
      {lines.map((line, i) => (
        <div key={i} className="blame-line">
          <span className="line-no">{line.finalLine}</span>
          <span className="blame-commit">{hashToLogical.get(line.hash) || short(line.hash, 8)}</span>
          <span className="blame-author">{line.author}</span>
          <code>{line.content}</code>
        </div>
      ))}
    </div>
  );
}

function OracleViewer({
  bugs,
  commitMap
}: {
  bugs: any[];
  commitMap: Record<string, { hash: string; role?: string }>;
}) {
  return (
    <div className="oracle-list">
      {bugs.length === 0 && <p className="muted">No bugs found.</p>}
      {bugs.map((bug) => {
        const bicEntries = bicEntriesOf(bug);
        const bfcEntries = bfcEntriesOf(bug);
        const faults = faultEntriesOf(bug);
        const fixes = fixEntriesOf(bug);
        return (
          <div key={bug.id} className="oracle-card">
            <h3>{bug.id}: {bug.title}</h3>
            <div className="meta-grid">
              <span>BIC</span><div>{bicEntries.map((entry) => formatCommitRef(entry, commitMap)).filter(Boolean).join(", ")}</div>
              <span>BFC</span><div>{bfcEntries.map((entry) => formatCommitRef(entry, commitMap)).filter(Boolean).join(", ")}</div>
              <span>Faults</span>
              <div className="oracle-items">
                {faults.map((fault, i) => (
                  <div key={i} className="oracle-item">
                    <code>{fault.file || ""}</code>
                    <span>{fault.commit || ""}{fault.change_type ? ` / ${fault.change_type}` : ""}</span>
                    <pre>{statementOf(fault)}</pre>
                  </div>
                ))}
              </div>
              <span>Fixes</span>
              <div className="oracle-items">
                {fixes.map((fix, i) => (
                  <div key={i} className="oracle-item">
                    <code>{fix.file || ""}</code>
                    <span>{fix.commit || ""}{fix.fix_type ? ` / ${fix.fix_type}` : ""}</span>
                    <pre>{statementOf(fix)}</pre>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function VerifyViewer({ detail }: { detail: RepositoryDetail }) {
  const verifyJson = JSON.stringify(detail.verifyResult, null, 2);
  const validationJson = JSON.stringify(detail.validationResult, null, 2);
  const graphMapJson = JSON.stringify(detail.graphMap, null, 2);
  return (
    <div className="verify-panel">
      <div className="verify-actions">
        <button onClick={() => downloadText("verify-result.json", verifyJson)}>Download verify-result.json</button>
        {detail.graphMap && <button onClick={() => downloadText("graph-map.json", graphMapJson)}>Download graph-map.json</button>}
        <button onClick={() => downloadText("generation.log", detail.generationLog || "")}>Download generation.log</button>
      </div>
      <h3>verify-result.json</h3>
      <pre className="json-box">{verifyJson || "No verify-result.json found."}</pre>
      <h3>validation-result.json</h3>
      <pre className="json-box">{validationJson || "No validation-result.json found."}</pre>
      {detail.graphMap && (
        <>
          <h3>graph-map.json</h3>
          <pre className="json-box">{graphMapJson}</pre>
        </>
      )}
      <h3>generation.log</h3>
      <pre className="json-box">{detail.generationLog || "No generation.log found."}</pre>
    </div>
  );
}

function normalizeText(text: string): string {
  return String(text || "").replace(/\s+/g, " ").trim();
}

const root = createRoot(document.getElementById("root") as HTMLElement);
root.render(<App />);
