import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import changeSchema from '../../schema/change.schema.json';
export { ChangeIdAllocator } from './change-id-allocator.js';

const ajv = new Ajv2020({ allErrors: true, strict: true });
addFormats(ajv);
const validate = ajv.compile(changeSchema);

const json = (body, status = 200) => Response.json(body, { status });

function authorized(request, env) {
  if (!env.CHANGELOGS_API_TOKEN) return false;
  return request.headers.get('authorization') === `Bearer ${env.CHANGELOGS_API_TOKEN}`;
}

function canonicalDate(now = new Date()) {
  return now.toISOString().slice(0, 10);
}

async function allocateId(env, date) {
  const id = env.CHANGE_ID_ALLOCATOR.idFromName(date);
  const stub = env.CHANGE_ID_ALLOCATOR.get(id);
  const response = await stub.fetch('https://allocator.internal/allocate', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ date })
  });
  if (!response.ok) throw new Error(`Change ID allocation failed: ${response.status}`);
  return response.json();
}

async function insertRecord(db, record) {
  const statements = [
    db.prepare(`INSERT INTO changes
      (change_id, schema_version, created_at, updated_at, occurred_at, summary, change_type, maturity, status, visibility, record_json)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`)
      .bind(
        record.change_id,
        record.schema_version ?? '1.0.0',
        record.created_at,
        record.updated_at ?? null,
        record.occurred_at ?? null,
        record.summary,
        record.change_type,
        record.maturity,
        record.status,
        record.visibility,
        JSON.stringify(record)
      )
  ];

  for (const component of record.components ?? []) {
    statements.push(db.prepare('INSERT INTO change_components (change_id, component) VALUES (?, ?)').bind(record.change_id, component));
  }
  for (const environment of record.environments ?? []) {
    statements.push(db.prepare('INSERT INTO change_environments (change_id, environment) VALUES (?, ?)').bind(record.change_id, environment));
  }

  await db.batch(statements);
}

async function createChange(request, env) {
  if (!authorized(request, env)) return json({ error: 'unauthorized' }, 401);

  let input;
  try {
    input = await request.json();
  } catch {
    return json({ error: 'invalid_json' }, 400);
  }

  const createdAt = input.created_at ?? new Date().toISOString();
  const date = canonicalDate(new Date(createdAt));
  const allocation = await allocateId(env, date);
  const record = {
    schema_version: '1.0.0',
    ...input,
    change_id: allocation.change_id,
    created_at: createdAt
  };

  if (!validate(record)) {
    return json({ error: 'schema_validation_failed', validation_errors: validate.errors ?? [] }, 422);
  }

  try {
    await insertRecord(env.CHANGELOGS_DB, record);
  } catch (error) {
    return json({ error: 'ledger_insert_failed', message: String(error?.message ?? error), change_id: record.change_id }, 500);
  }

  return json({ change_id: record.change_id, record }, 201);
}

async function getChange(changeId, env) {
  const row = await env.CHANGELOGS_DB.prepare('SELECT record_json FROM changes WHERE change_id = ?').bind(changeId).first();
  if (!row) return json({ error: 'not_found' }, 404);
  return json(JSON.parse(row.record_json));
}

async function listChanges(url, env) {
  const clauses = [];
  const bindings = [];
  const joins = [];

  for (const [param, column] of [['status', 'c.status'], ['maturity', 'c.maturity'], ['type', 'c.change_type'], ['visibility', 'c.visibility']]) {
    const value = url.searchParams.get(param);
    if (value) {
      clauses.push(`${column} = ?`);
      bindings.push(value);
    }
  }

  const component = url.searchParams.get('component');
  if (component) {
    joins.push('JOIN change_components cc ON cc.change_id = c.change_id');
    clauses.push('cc.component = ?');
    bindings.push(component);
  }

  const environment = url.searchParams.get('environment');
  if (environment) {
    joins.push('JOIN change_environments ce ON ce.change_id = c.change_id');
    clauses.push('ce.environment = ?');
    bindings.push(environment);
  }

  const from = url.searchParams.get('from');
  if (from) {
    clauses.push('c.created_at >= ?');
    bindings.push(from);
  }
  const to = url.searchParams.get('to');
  if (to) {
    clauses.push('c.created_at <= ?');
    bindings.push(to);
  }

  const requestedLimit = Number(url.searchParams.get('limit') ?? 50);
  const limit = Number.isFinite(requestedLimit) ? Math.max(1, Math.min(100, Math.trunc(requestedLimit))) : 50;
  bindings.push(limit);

  const sql = `SELECT DISTINCT c.record_json FROM changes c ${joins.join(' ')} ${clauses.length ? `WHERE ${clauses.join(' AND ')}` : ''} ORDER BY c.created_at DESC LIMIT ?`;
  const result = await env.CHANGELOGS_DB.prepare(sql).bind(...bindings).all();
  return json({ records: (result.results ?? []).map(row => JSON.parse(row.record_json)), limit });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === '/health') {
      return json({ service: 'goreecloud-changelogs', status: 'ok' });
    }

    if (url.pathname === '/v1/changes' && request.method === 'POST') {
      return createChange(request, env);
    }

    if (url.pathname === '/v1/changes' && request.method === 'GET') {
      if (!authorized(request, env)) return json({ error: 'unauthorized' }, 401);
      return listChanges(url, env);
    }

    const match = url.pathname.match(/^\/v1\/changes\/(GC-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{3,})$/);
    if (match && request.method === 'GET') {
      if (!authorized(request, env)) return json({ error: 'unauthorized' }, 401);
      return getChange(match[1], env);
    }

    return json({ error: 'not_found' }, 404);
  }
};
