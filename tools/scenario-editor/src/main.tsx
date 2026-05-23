import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

type Role = 'initial' | 'bug_introducing' | 'bug_fixing' | 'distractor' | 'refactoring' | 'formatting';
type FaultType = 'line_modification' | 'omission';

type SourceVersion = {
  id: string;
  role: Role;
  message: string;
  author: string;
  date: string;
  source: string;
};

type AppState = {
  scenarioId: string;
  title: string;
  slug: string;
  description: string;
  category: string;
  difficulty: string;
  status: string;
  factors: string[];
  repositoryName: string;
  defaultBranch: string;
  language: string;
  buildSystem: string;
  sourceRoot: string;
  sourceFilePath: string;
  versions: SourceVersion[];
  bugId: string;
  bugTitle: string;
  bic: string;
  bfc: string;
  faultType: FaultType;
  entityType: string;
  entityName: string;
  entitySignature: string;
  faultStatement: string;
  fixStatement: string;
  missingStatement: string;
  addedStatement: string;
  overwrite: boolean;
};

const FACTORS = [
  'single-bic',
  'single-bfc',
  'line-modification',
  'line-addition-fix',
  'omission-bug',
  'formatting-after-bic',
  'line-number-shift',
  'basic-blame-distractor',
  'tangled-bic',
  'tangled-bfc',
  'multi-bic',
  'revert-reintroduce',
  'copy-propagation'
];

const DEFAULT_SOURCE = `package example;

public class Range {
    public boolean contains(int value, int min, int max) {
        return value >= min && value <= max;
    }
}
`;

function addDaysIso(dayOffset: number): string {
  const d = new Date(Date.UTC(2024, 0, 1 + dayOffset, 10, 0, 0));
  return d.toISOString().replace('.000Z', 'Z');
}

function initialState(): AppState {
  return {
    scenarioId: 'SZZ-0004',
    title: 'New SZZ scenario',
    slug: 'new-szz-scenario',
    description: 'Describe the scenario purpose and the SZZ difficulty factor here.',
    category: 'basic',
    difficulty: 'easy',
    status: 'draft',
    factors: ['single-bic', 'single-bfc', 'line-modification'],
    repositoryName: 'SZZ-0004-new-szz-scenario',
    defaultBranch: 'main',
    language: 'java',
    buildSystem: 'none',
    sourceRoot: 'src/main/java',
    sourceFilePath: 'src/main/java/example/Range.java',
    versions: [
      {
        id: 'c0',
        role: 'initial',
        message: 'Initial correct implementation',
        author: 'Alice <alice@example.com>',
        date: addDaysIso(0),
        source: DEFAULT_SOURCE
      },
      {
        id: 'c1',
        role: 'bug_introducing',
        message: 'Introduce bug',
        author: 'Bob <bob@example.com>',
        date: addDaysIso(1),
        source: DEFAULT_SOURCE.replace('return value >= min && value <= max;', 'return value > min && value < max;')
      },
      {
        id: 'c2',
        role: 'bug_fixing',
        message: 'Fix bug',
        author: 'Alice <alice@example.com>',
        date: addDaysIso(2),
        source: DEFAULT_SOURCE
      }
    ],
    bugId: 'B001',
    bugTitle: 'Boundary values are excluded',
    bic: 'c1',
    bfc: 'c2',
    faultType: 'line_modification',
    entityType: 'method',
    entityName: 'contains',
    entitySignature: 'boolean contains(int value, int min, int max)',
    faultStatement: 'return value > min && value < max;',
    fixStatement: 'return value >= min && value <= max;',
    missingStatement: 'if (s == null) {\n    return "";\n}',
    addedStatement: 'if (s == null) {\n    return "";\n}',
    overwrite: false
  };
}

function yamlScalar(value: string | undefined): string {
  const v = value ?? '';
  if (/^[A-Za-z0-9_.@<>/: -]+$/.test(v) && v.trim() === v && !v.includes(': ')) {
    return `"${v.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
  }
  return `"${v.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
}

function block(value: string, indent: number): string {
  const normalized = (value || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n').replace(/\n+$/, '');
  const pad = ' '.repeat(indent);
  if (normalized.length === 0) {
    return `${pad}\n`;
  }
  return normalized.split('\n').map((line) => `${pad}${line}`).join('\n') + '\n';
}

function listLines(items: string[], indent: number): string {
  const pad = ' '.repeat(indent);
  return items.map((item) => `${pad}- ${yamlScalar(item)}`).join('\n');
}

function labelsForVersion(v: SourceVersion, state: AppState): string[] {
  if (v.id === state.bic) return [state.bugId, 'fault'];
  if (v.id === state.bfc) return [state.bugId, 'fix'];
  if (v.role === 'formatting') return ['formatting_only', 'non_bug_introducing_change'];
  return [];
}

function generateScenarioYaml(state: AppState): string {
  const lines: string[] = [];
  lines.push('schema_version: "1.0"');
  lines.push('');
  lines.push('meta:');
  lines.push(`  id: ${yamlScalar(state.scenarioId)}`);
  lines.push(`  title: ${yamlScalar(state.title)}`);
  lines.push(`  slug: ${yamlScalar(state.slug)}`);
  lines.push('  description: >');
  lines.push(block(state.description, 4).trimEnd());
  lines.push(`  category: ${yamlScalar(state.category)}`);
  lines.push('  factors:');
  lines.push(listLines(state.factors, 4));
  lines.push(`  difficulty: ${yamlScalar(state.difficulty)}`);
  lines.push(`  status: ${yamlScalar(state.status)}`);
  lines.push('');
  lines.push('repository:');
  lines.push(`  name: ${yamlScalar(state.repositoryName)}`);
  lines.push(`  default_branch: ${yamlScalar(state.defaultBranch)}`);
  lines.push(`  language: ${yamlScalar(state.language)}`);
  lines.push(`  build_system: ${yamlScalar(state.buildSystem)}`);
  lines.push(`  source_root: ${yamlScalar(state.sourceRoot)}`);
  lines.push('');
  lines.push('commits:');

  state.versions.forEach((v, i) => {
    lines.push(`  - id: ${yamlScalar(v.id)}`);
    lines.push(`    message: ${yamlScalar(v.message)}`);
    lines.push(`    author: ${yamlScalar(v.author)}`);
    lines.push(`    date: ${yamlScalar(v.date)}`);
    lines.push(`    role: ${yamlScalar(v.role)}`);
    lines.push('    operations:');
    if (i === 0) {
      lines.push('      - type: "write_file"');
      lines.push(`        path: ${yamlScalar(state.sourceFilePath)}`);
      lines.push('        content: |');
      lines.push(block(v.source, 10).trimEnd());
    } else {
      lines.push('      - type: "replace"');
      lines.push(`        path: ${yamlScalar(state.sourceFilePath)}`);
      lines.push('        old: |');
      lines.push(block(state.versions[i - 1].source, 10).trimEnd());
      lines.push('        new: |');
      lines.push(block(v.source, 10).trimEnd());
      const labels = labelsForVersion(v, state);
      if (labels.length > 0) {
        lines.push('        labels:');
        lines.push(listLines(labels, 10));
      }
    }
    lines.push('');
  });

  lines.push('bugs:');
  lines.push(`  - id: ${yamlScalar(state.bugId)}`);
  lines.push(`    title: ${yamlScalar(state.bugTitle)}`);
  lines.push(`    bug_fixing_commit: ${yamlScalar(state.bfc)}`);
  lines.push('    bug_introducing_commits:');
  lines.push(`      - ${yamlScalar(state.bic)}`);
  lines.push('');
  lines.push('    fault:');
  lines.push(`      commit: ${yamlScalar(state.bic)}`);
  lines.push(`      file: ${yamlScalar(state.sourceFilePath)}`);
  lines.push('      entity:');
  lines.push(`        type: ${yamlScalar(state.entityType)}`);
  lines.push(`        name: ${yamlScalar(state.entityName)}`);
  lines.push(`        signature: ${yamlScalar(state.entitySignature)}`);
  if (state.faultType === 'omission') {
    lines.push('      change_type: "omission"');
    lines.push('      missing_statement: |');
    lines.push(block(state.missingStatement, 8).trimEnd());
  } else {
    lines.push(`      statement: ${yamlScalar(state.faultStatement)}`);
    lines.push('      change_type: "line_modification"');
  }
  lines.push('');
  lines.push('    fix:');
  lines.push(`      commit: ${yamlScalar(state.bfc)}`);
  lines.push(`      file: ${yamlScalar(state.sourceFilePath)}`);
  lines.push('      entity:');
  lines.push(`        type: ${yamlScalar(state.entityType)}`);
  lines.push(`        name: ${yamlScalar(state.entityName)}`);
  lines.push(`        signature: ${yamlScalar(state.entitySignature)}`);
  if (state.faultType === 'omission') {
    lines.push('      added_statement: |');
    lines.push(block(state.addedStatement, 8).trimEnd());
    lines.push('      fix_type: "line_addition"');
  } else {
    lines.push(`      statement: ${yamlScalar(state.fixStatement)}`);
    lines.push('      fix_type: "line_modification"');
  }
  lines.push('');
  lines.push('    expected_szz:');
  lines.push('      commit_level:');
  lines.push('        true_positives:');
  lines.push(`          - ${yamlScalar(state.bic)}`);
  lines.push('        false_positives_allowed: []');
  lines.push('      line_level:');
  if (state.faultType === 'omission') {
    lines.push('        available: false');
    lines.push('        reason: "The fault is an omitted statement, so no faulty deleted line exists."');
  } else {
    lines.push('        available: true');
    lines.push('        faulty_statements:');
    lines.push(`          - ${yamlScalar(state.faultStatement)}`);
  }
  lines.push('');
  lines.push('checks:');
  lines.push('  - type: "git_history_contains"');
  lines.push('    commits:');
  state.versions.forEach((v) => lines.push(`      - ${yamlScalar(v.id)}`));
  return lines.join('\n') + '\n';
}

function generateReadme(state: AppState): string {
  return `# ${state.scenarioId}: ${state.title}

## Purpose

${state.description}

## Commit structure

${state.versions.map((v) => `- \`${v.id}\`: ${v.message} (${v.role})`).join('\n')}

## Expected behavior

The bug-fixing commit is \`${state.bfc}\`.
The expected bug-introducing commit is \`${state.bic}\`.

## Factors

${state.factors.map((f) => `- ${f}`).join('\n')}
`;
}

function generateIndexEntry(state: AppState): string {
  return `- id: "${state.scenarioId}"
  title: "${state.title.replace(/"/g, '\\"')}"
  slug: "${state.slug}"
  category: "${state.category}"
  factors:
${state.factors.map((f) => `    - "${f}"`).join('\n')}
  difficulty: "${state.difficulty}"
  status: "${state.status}"
  path: "scenarios/${state.scenarioId}/scenario.yml"
`;
}

function downloadFile(filename: string, content: string, type = 'text/plain') {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function App() {
  const [state, setState] = useState<AppState>(initialState());
  const [saveMessage, setSaveMessage] = useState<string>('');
  const [saveError, setSaveError] = useState<string>('');
  const [knownIds, setKnownIds] = useState<string[]>([]);

  useEffect(() => {
    fetch('/api/scenarios')
      .then((r) => r.json())
      .then((data) => {
        if (data.nextId) {
          setState((s) => ({
            ...s,
            scenarioId: data.nextId,
            repositoryName: `${data.nextId}-${s.slug}`
          }));
        }
        if (Array.isArray(data.ids)) setKnownIds(data.ids);
      })
      .catch(() => {
        // API may be unavailable if the UI is not started through npm run dev.
      });
  }, []);

  const scenarioYaml = useMemo(() => generateScenarioYaml(state), [state]);
  const readme = useMemo(() => generateReadme(state), [state]);
  const indexEntry = useMemo(() => generateIndexEntry(state), [state]);
  const validationMessages = useMemo(() => localValidate(state), [state]);

  function update<K extends keyof AppState>(key: K, value: AppState[K]) {
    setState((s) => ({ ...s, [key]: value }));
  }

  function updateVersion(index: number, patch: Partial<SourceVersion>) {
    setState((s) => {
      const versions = [...s.versions];
      versions[index] = { ...versions[index], ...patch };
      return { ...s, versions };
    });
  }

  function addVersion() {
    setState((s) => {
      const next = s.versions.length;
      const previous = s.versions[s.versions.length - 1];
      const versions = [
        ...s.versions,
        {
          id: `c${next}`,
          role: next === 1 ? 'bug_introducing' : 'distractor',
          message: `Commit c${next}`,
          author: previous?.author || 'Alice <alice@example.com>',
          date: addDaysIso(next),
          source: previous?.source || ''
        } as SourceVersion
      ];
      return { ...s, versions };
    });
  }

  function removeVersion(index: number) {
    setState((s) => {
      if (s.versions.length <= 2) return s;
      const versions = s.versions.filter((_, i) => i !== index).map((v, i) => ({ ...v, id: `c${i}` }));
      return {
        ...s,
        versions,
        bic: versions.some((v) => v.id === s.bic) ? s.bic : versions[Math.min(1, versions.length - 1)].id,
        bfc: versions.some((v) => v.id === s.bfc) ? s.bfc : versions[versions.length - 1].id
      };
    });
  }

  async function saveToScenarios() {
    setSaveMessage('');
    setSaveError('');
    try {
      const response = await fetch('/api/scenarios/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: state.scenarioId,
          scenarioYaml,
          readme,
          indexEntry,
          overwrite: state.overwrite
        })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Save failed');
      }
      setSaveMessage(`Saved: ${data.files.join(', ')}`);
      setKnownIds((ids) => Array.from(new Set([...ids, state.scenarioId])).sort());
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <main>
      <header className="hero">
        <div>
          <h1>SZZBench Scenario Editor</h1>
          <p>Create scenario.yml files from source-code versions and save them directly to the local scenarios directory.</p>
        </div>
        <div className="actions">
          <button onClick={() => downloadFile('scenario.yml', scenarioYaml, 'text/yaml')}>Download scenario.yml</button>
          <button onClick={() => downloadFile('README.md', readme, 'text/markdown')}>Download README.md</button>
          <button onClick={() => downloadFile('index-entry.yml', indexEntry, 'text/yaml')}>Download index entry</button>
          <button className="primary" onClick={saveToScenarios}>Save to scenarios/</button>
        </div>
      </header>

      <div className="notice info">
        This editor currently supports only the classic scenarios/SZZ-xxxx/scenario.yml format. It does not support advanced-scenarios or scenario.graph.yml yet.
      </div>

      {saveMessage && <div className="notice success">{saveMessage}</div>}
      {saveError && <div className="notice error">{saveError}</div>}

      <div className="layout">
        <section className="panel formPanel">
          <h2>Scenario metadata</h2>
          <div className="grid2">
            <label>Scenario ID<input value={state.scenarioId} onChange={(e) => update('scenarioId', e.target.value)} /></label>
            <label>Title<input value={state.title} onChange={(e) => update('title', e.target.value)} /></label>
            <label>Slug<input value={state.slug} onChange={(e) => update('slug', e.target.value)} /></label>
            <label>Category<input value={state.category} onChange={(e) => update('category', e.target.value)} /></label>
            <label>Difficulty<input value={state.difficulty} onChange={(e) => update('difficulty', e.target.value)} /></label>
            <label>Status<input value={state.status} onChange={(e) => update('status', e.target.value)} /></label>
          </div>
          <label>Description<textarea rows={4} value={state.description} onChange={(e) => update('description', e.target.value)} /></label>
          <div className="checkboxGrid">
            {FACTORS.map((factor) => (
              <label key={factor} className="checkLabel">
                <input
                  type="checkbox"
                  checked={state.factors.includes(factor)}
                  onChange={(e) => {
                    const factors = e.target.checked
                      ? [...state.factors, factor]
                      : state.factors.filter((f) => f !== factor);
                    update('factors', factors);
                  }}
                />
                {factor}
              </label>
            ))}
          </div>

          <h2>Repository</h2>
          <div className="grid2">
            <label>Repository name<input value={state.repositoryName} onChange={(e) => update('repositoryName', e.target.value)} /></label>
            <label>Default branch<input value={state.defaultBranch} onChange={(e) => update('defaultBranch', e.target.value)} /></label>
            <label>Language<input value={state.language} onChange={(e) => update('language', e.target.value)} /></label>
            <label>Build system<input value={state.buildSystem} onChange={(e) => update('buildSystem', e.target.value)} /></label>
            <label>Source root<input value={state.sourceRoot} onChange={(e) => update('sourceRoot', e.target.value)} /></label>
            <label>Source file path<input value={state.sourceFilePath} onChange={(e) => update('sourceFilePath', e.target.value)} /></label>
          </div>

          <h2>Source versions</h2>
          {state.versions.map((v, index) => (
            <div className="versionCard" key={v.id}>
              <div className="versionHeader">
                <strong>{v.id}</strong>
                <button disabled={state.versions.length <= 2} onClick={() => removeVersion(index)}>Remove</button>
              </div>
              <div className="grid2">
                <label>Role
                  <select value={v.role} onChange={(e) => updateVersion(index, { role: e.target.value as Role })}>
                    <option value="initial">initial</option>
                    <option value="bug_introducing">bug_introducing</option>
                    <option value="bug_fixing">bug_fixing</option>
                    <option value="distractor">distractor</option>
                    <option value="refactoring">refactoring</option>
                    <option value="formatting">formatting</option>
                  </select>
                </label>
                <label>Message<input value={v.message} onChange={(e) => updateVersion(index, { message: e.target.value })} /></label>
                <label>Author<input value={v.author} onChange={(e) => updateVersion(index, { author: e.target.value })} /></label>
                <label>Date<input value={v.date} onChange={(e) => updateVersion(index, { date: e.target.value })} /></label>
              </div>
              <label>Source code<textarea className="code" value={v.source} onChange={(e) => updateVersion(index, { source: e.target.value })} /></label>
            </div>
          ))}
          <button onClick={addVersion}>+ Add next source version</button>

          <h2>Bug oracle</h2>
          <div className="grid2">
            <label>Bug ID<input value={state.bugId} onChange={(e) => update('bugId', e.target.value)} /></label>
            <label>Bug title<input value={state.bugTitle} onChange={(e) => update('bugTitle', e.target.value)} /></label>
            <label>BIC
              <select value={state.bic} onChange={(e) => update('bic', e.target.value)}>
                {state.versions.map((v) => <option value={v.id} key={v.id}>{v.id}</option>)}
              </select>
            </label>
            <label>BFC
              <select value={state.bfc} onChange={(e) => update('bfc', e.target.value)}>
                {state.versions.map((v) => <option value={v.id} key={v.id}>{v.id}</option>)}
              </select>
            </label>
            <label>Fault type
              <select value={state.faultType} onChange={(e) => update('faultType', e.target.value as FaultType)}>
                <option value="line_modification">line_modification</option>
                <option value="omission">omission</option>
              </select>
            </label>
            <label>Entity type<input value={state.entityType} onChange={(e) => update('entityType', e.target.value)} /></label>
            <label>Entity name<input value={state.entityName} onChange={(e) => update('entityName', e.target.value)} /></label>
            <label>Entity signature<input value={state.entitySignature} onChange={(e) => update('entitySignature', e.target.value)} /></label>
          </div>

          {state.faultType === 'line_modification' ? (
            <div className="grid2">
              <label>Fault statement<textarea rows={3} value={state.faultStatement} onChange={(e) => update('faultStatement', e.target.value)} /></label>
              <label>Fix statement<textarea rows={3} value={state.fixStatement} onChange={(e) => update('fixStatement', e.target.value)} /></label>
            </div>
          ) : (
            <div className="grid2">
              <label>Missing statement<textarea rows={5} value={state.missingStatement} onChange={(e) => update('missingStatement', e.target.value)} /></label>
              <label>Added statement<textarea rows={5} value={state.addedStatement} onChange={(e) => update('addedStatement', e.target.value)} /></label>
            </div>
          )}

          <label className="checkLabel">
            <input type="checkbox" checked={state.overwrite} onChange={(e) => update('overwrite', e.target.checked)} />
            Overwrite existing scenario if {state.scenarioId} already exists
          </label>
          {knownIds.length > 0 && <p className="small">Existing IDs detected: {knownIds.join(', ')}</p>}
        </section>

        <aside className="panel previewPanel">
          <h2>Lightweight checks</h2>
          <ul className="validationList">
            {validationMessages.map((m) => <li key={m} className={m.startsWith('OK') ? 'ok' : 'warn'}>{m}</li>)}
          </ul>

          <h2>Timeline</h2>
          <ol className="timeline">
            {state.versions.map((v) => (
              <li key={v.id}><strong>{v.id}</strong> <span>{v.role}</span><br />{v.message}</li>
            ))}
          </ol>

          <h2>scenario.yml preview</h2>
          <pre className="preview">{scenarioYaml}</pre>
          <h2>README.md preview</h2>
          <pre className="preview">{readme}</pre>
          <h2>index.yml entry</h2>
          <pre className="preview">{indexEntry}</pre>
        </aside>
      </div>
    </main>
  );
}

function localValidate(state: AppState): string[] {
  const messages: string[] = [];
  const ids = state.versions.map((v) => v.id);
  const bicIndex = ids.indexOf(state.bic);
  const bfcIndex = ids.indexOf(state.bfc);
  if (/^SZZ-\d{4}$/.test(state.scenarioId)) messages.push('OK: scenario ID format');
  else messages.push('WARN: scenario ID should match SZZ-0001 format');
  if (state.versions.length >= 2) messages.push('OK: at least two versions');
  else messages.push('WARN: add at least two versions');
  if (bicIndex >= 0 && bfcIndex >= 0 && bicIndex < bfcIndex) messages.push('OK: BIC precedes BFC');
  else messages.push('WARN: BIC should precede BFC');
  if (state.sourceFilePath.trim()) messages.push('OK: source file path is set');
  else messages.push('WARN: source file path is empty');
  const bicSource = state.versions[bicIndex]?.source || '';
  const bfcSource = state.versions[bfcIndex]?.source || '';
  if (state.faultType === 'line_modification') {
    if (state.faultStatement && bicSource.includes(state.faultStatement)) messages.push('OK: fault statement appears in BIC version');
    else messages.push('WARN: fault statement does not appear in BIC version');
    if (state.fixStatement && bfcSource.includes(state.fixStatement)) messages.push('OK: fix statement appears in BFC version');
    else messages.push('WARN: fix statement does not appear in BFC version');
  } else {
    if (state.missingStatement.trim()) messages.push('OK: missing statement is set');
    else messages.push('WARN: missing statement is empty');
    if (state.addedStatement && bfcSource.includes(state.addedStatement)) messages.push('OK: added statement appears in BFC version');
    else messages.push('WARN: added statement does not appear in BFC version');
  }
  return messages;
}

createRoot(document.getElementById('root')!).render(<App />);
