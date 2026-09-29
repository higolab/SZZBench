// The editor's scenario model: state, defaults, and the text it generates.
//
// Everything here is plain TypeScript with no React or DOM, so the tests can run
// it with Node and check what it generates against SZZBench's Python validator
// (tests/test_scenario_editor.py, issue #97).

export type Role = 'initial' | 'bug_introducing' | 'bug_fixing' | 'distractor' | 'refactoring' | 'formatting';
export type FaultType = 'line_modification' | 'omission';
/** `meta.tier` is a declaration the author makes; it has no default (docs/decisions/vocabulary.md §7). */
export type Tier = '' | 'control' | 'discriminating';

export type SourceVersion = {
  id: string;
  role: Role;
  message: string;
  author: string;
  /** optional: when empty, generation fills a deterministic date (docs/generator-options.md §1) */
  date: string;
  source: string;
};

export type AppState = {
  scenarioId: string;
  title: string;
  slug: string;
  description: string;
  categoryCode: string;
  tier: Tier;
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

/** The classic-suite categories: code and name, as docs/decisions/vocabulary.md §3 fixes them. */
export const CATEGORIES: [string, string][] = [
  ['S1', 'Basic semantic line changes'],
  ['S2', 'Omission and deletion bugs'],
  ['S3', 'Intermediate noise and history noise'],
  ['S4', 'BFC-side noise and tangled commits'],
  ['S5', 'Refactoring, move, and rename after BIC'],
  ['S6', 'Multiple BICs, duplicate faults, and composite faults'],
  ['S7', 'Context, message, and non-local evidence'],
  ['S8', 'Non-source, configuration, test-only, and file-level edge cases'],
];

export const TIERS: Tier[] = ['control', 'discriminating'];
export const DIFFICULTIES = ['easy', 'medium', 'hard'];

export const FACTORS = [
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

export const DEFAULT_AUTHOR = 'Alice <alice@example.com>';

export const DEFAULT_SOURCE = `package example;

public class Range {
    public boolean contains(int value, int min, int max) {
        return value >= min && value <= max;
    }
}
`;

export function categoryName(code: string): string {
  return CATEGORIES.find(([c]) => c === code)?.[1] ?? '';
}

export function initialState(): AppState {
  return {
    scenarioId: 'SZZ-0002',
    title: 'New SZZ scenario',
    slug: 'new-szz-scenario',
    description: 'Describe the scenario purpose and the SZZ difficulty factor here.',
    categoryCode: 'S1',
    tier: '',
    difficulty: 'medium',
    status: 'draft',
    factors: ['single-bic', 'single-bfc', 'line-modification'],
    repositoryName: 'SZZ-0002-new-szz-scenario',
    defaultBranch: 'main',
    language: 'java',
    buildSystem: 'none',
    sourceRoot: 'src/main/java',
    sourceFilePath: 'src/main/java/example/Range.java',
    // Messages describe the change and never the role (docs/decisions/oracle-leakage.md),
    // and one author writes every commit, so neither a message nor an author names the answer.
    versions: [
      {
        id: 'c0',
        role: 'initial',
        message: 'Add the range check',
        author: DEFAULT_AUTHOR,
        date: '',
        source: DEFAULT_SOURCE
      },
      {
        id: 'c1',
        role: 'bug_introducing',
        message: 'Exclude the bounds from the range check',
        author: DEFAULT_AUTHOR,
        date: '',
        source: DEFAULT_SOURCE.replace('return value >= min && value <= max;', 'return value > min && value < max;')
      },
      {
        id: 'c2',
        role: 'bug_fixing',
        message: 'Include the bounds in the range check',
        author: DEFAULT_AUTHOR,
        date: '',
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

/** The version `addVersion` appends: an empty message, which the checks ask the author to write. */
export function nextVersion(state: AppState): SourceVersion {
  const next = state.versions.length;
  const previous = state.versions[state.versions.length - 1];
  return {
    id: `c${next}`,
    role: next === 1 ? 'bug_introducing' : 'distractor',
    message: '',
    author: previous?.author || DEFAULT_AUTHOR,
    date: '',
    source: previous?.source || ''
  };
}

export function yamlScalar(value: string | undefined): string {
  const v = value ?? '';
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

export function generateScenarioYaml(state: AppState): string {
  const lines: string[] = [];
  lines.push('schema_version: "1.0"');
  lines.push('');
  lines.push('meta:');
  lines.push(`  id: ${yamlScalar(state.scenarioId)}`);
  lines.push(`  title: ${yamlScalar(state.title)}`);
  lines.push(`  slug: ${yamlScalar(state.slug)}`);
  lines.push('  description: >');
  lines.push(block(state.description, 4).trimEnd());
  lines.push(`  category: ${yamlScalar(categoryName(state.categoryCode))}`);
  lines.push(`  category_code: ${yamlScalar(state.categoryCode)}`);
  lines.push('  factors:');
  lines.push(listLines(state.factors, 4));
  lines.push(`  difficulty: ${yamlScalar(state.difficulty)}`);
  lines.push(`  status: ${yamlScalar(state.status)}`);
  if (state.tier) {
    lines.push(`  tier: ${yamlScalar(state.tier)}`);
  }
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
    if (v.date.trim()) {
      lines.push(`    date: ${yamlScalar(v.date.trim())}`);
    }
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

/**
 * The hand-written part of the README (docs/scenario-readme.md).  The generated
 * header that states category, tier, factors and oracle is not written here: the
 * save endpoint inserts it with `szzbench readme --write`, so it is rendered by
 * the same code as every other scenario's.
 */
export function generateReadme(state: AppState): string {
  return `# ${state.scenarioId}: ${state.title}

## Purpose

${state.description}

## Commit structure

${state.versions.map((v) => `- \`${v.id}\`: ${v.message}${v.id === state.bic ? ' (BIC)' : v.id === state.bfc ? ' (BFC)' : ''}`).join('\n')}

## Expected behavior

The bug-fixing commit is \`${state.bfc}\`.
The expected bug-introducing commit is \`${state.bic}\`.
`;
}

export function generateIndexEntry(state: AppState): string {
  return `- id: "${state.scenarioId}"
  title: "${state.title.replace(/"/g, '\\"')}"
  slug: "${state.slug}"
  category_code: "${state.categoryCode}"
  category: "${categoryName(state.categoryCode)}"
  factors:
${state.factors.map((f) => `    - "${f}"`).join('\n')}
  difficulty: "${state.difficulty}"
  status: "${state.status}"
  path: "scenarios/${state.scenarioId}/scenario.yml"
`;
}

export function localValidate(state: AppState): string[] {
  const messages: string[] = [];
  const ids = state.versions.map((v) => v.id);
  const bicIndex = ids.indexOf(state.bic);
  const bfcIndex = ids.indexOf(state.bfc);
  if (/^SZZ-\d{4}$/.test(state.scenarioId)) messages.push('OK: scenario ID format');
  else messages.push('WARN: scenario ID should match SZZ-0001 format');
  if (state.tier) messages.push(`OK: tier is ${state.tier}`);
  else messages.push('WARN: choose a tier (control or discriminating); saving needs one');
  if (state.versions.length >= 2) messages.push('OK: at least two versions');
  else messages.push('WARN: add at least two versions');
  const unnamed = state.versions.filter((v) => !v.message.trim()).map((v) => v.id);
  if (unnamed.length === 0) messages.push('OK: every commit has a message');
  else messages.push(`WARN: write a message describing the change for ${unnamed.join(', ')}`);
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
