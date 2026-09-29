import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

import {
  AppState,
  CATEGORIES,
  DIFFICULTIES,
  FACTORS,
  FaultType,
  Role,
  SourceVersion,
  TIERS,
  Tier,
  generateIndexEntry,
  generateReadme,
  generateScenarioYaml,
  initialState,
  localValidate,
  nextVersion
} from './scenarioModel';

type Finding = { severity: string; code: string; message: string; location: string | null };

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
  const [findings, setFindings] = useState<Finding[]>([]);
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
    setState((s) => ({ ...s, versions: [...s.versions, nextVersion(s)] }));
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

  // The Download buttons fetch what Save would write -- the README with its
  // generated header, the index entry in index.yml's style -- after the same
  // validate --lint, and write nothing (PR #101 review).  Without the backend only
  // scenario.yml can be downloaded: the header comes from SZZBench itself.
  async function download(kind: 'scenario' | 'readme' | 'index') {
    setSaveMessage('');
    setSaveError('');
    setFindings([]);
    let response: Response;
    let data: any;
    try {
      response = await fetch('/api/scenarios/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: state.scenarioId, scenarioYaml, readme })
      });
      data = await response.json();
    } catch {
      if (kind === 'scenario') {
        downloadFile('scenario.yml', scenarioYaml, 'text/yaml');
        return;
      }
      setSaveError(`The backend is not reachable, and the README's generated header and the index entry come from it. `
        + `Start the editor with npm run dev, or place the files under scenarios/${state.scenarioId}/ and run `
        + `szzbench readme --write scenarios/${state.scenarioId} before the scenario counts as ready.`);
      return;
    }
    setFindings(Array.isArray(data.findings) ? data.findings : []);
    if (!response.ok) {
      setSaveError(data.error || 'Preview failed');
      return;
    }
    if (kind === 'scenario') downloadFile('scenario.yml', data.scenarioYaml, 'text/yaml');
    else if (kind === 'readme') downloadFile('README.md', data.readme, 'text/markdown');
    else downloadFile('index-entry.yml', data.indexEntry, 'text/yaml');
  }

  async function saveToScenarios() {
    setSaveMessage('');
    setSaveError('');
    setFindings([]);
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
      // what `szzbench validate --lint` found, shown whether or not the save went through
      setFindings(Array.isArray(data.findings) ? data.findings : []);
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
          <button onClick={() => download('scenario')}>Download scenario.yml</button>
          <button onClick={() => download('readme')}>Download README.md</button>
          <button onClick={() => download('index')}>Download index entry</button>
          <button className="primary" onClick={saveToScenarios} disabled={!state.tier}
            title={state.tier ? '' : 'Choose a tier first'}>Save to scenarios/</button>
        </div>
      </header>

      <div className="notice info">
        This editor writes classic scenarios/SZZ-xxxx/scenario.yml files: one source file, one bug, a linear history. It does not write advanced-scenarios or scenario.graph.yml. Saving runs SZZBench's own validator (validate --lint) and adds the generated README header.
      </div>

      {saveMessage && <div className="notice success">{saveMessage}</div>}
      {saveError && <div className="notice error">{saveError}</div>}
      {findings.length > 0 && (
        <div className="notice info">
          <strong>validate --lint</strong>
          <ul className="validationList">
            {findings.map((f, i) => (
              <li key={i} className={f.severity === 'INFO' ? 'ok' : 'warn'}>
                {f.severity} {f.code}: {f.message}{f.location ? ` (${f.location})` : ''}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="layout">
        <section className="panel formPanel">
          <h2>Scenario metadata</h2>
          <div className="grid2">
            <label>Scenario ID<input value={state.scenarioId} onChange={(e) => update('scenarioId', e.target.value)} /></label>
            <label>Title<input value={state.title} onChange={(e) => update('title', e.target.value)} /></label>
            <label>Slug<input value={state.slug} onChange={(e) => update('slug', e.target.value)} /></label>
            <label>Category
              <select value={state.categoryCode} onChange={(e) => update('categoryCode', e.target.value)}>
                {CATEGORIES.map(([code, name]) => <option value={code} key={code}>{code} {name}</option>)}
              </select>
            </label>
            <label>Tier
              <select value={state.tier} onChange={(e) => update('tier', e.target.value as Tier)}>
                <option value="">(choose: what the scenario is for)</option>
                {TIERS.map((tier) => <option value={tier} key={tier}>{tier}</option>)}
              </select>
            </label>
            <label>Difficulty
              <select value={state.difficulty} onChange={(e) => update('difficulty', e.target.value)}>
                {DIFFICULTIES.map((d) => <option value={d} key={d}>{d}</option>)}
              </select>
            </label>
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
                <label>Message<input value={v.message} placeholder="describe the change, not its role" onChange={(e) => updateVersion(index, { message: e.target.value })} /></label>
                <label>Author<input value={v.author} onChange={(e) => updateVersion(index, { author: e.target.value })} /></label>
                <label>Date (optional)<input value={v.date} placeholder="generated when empty" onChange={(e) => updateVersion(index, { date: e.target.value })} /></label>
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
          <p className="small">Saving and downloading insert the generated header (category, tier, factors, oracle) with szzbench readme --write.</p>
          <pre className="preview">{readme}</pre>
          <h2>index.yml entry</h2>
          <p className="small">Saved and downloaded entries are rendered by the backend in index.yml's own style.</p>
          <pre className="preview">{indexEntry}</pre>
        </aside>
      </div>
    </main>
  );
}

createRoot(document.getElementById('root')!).render(<App />);
