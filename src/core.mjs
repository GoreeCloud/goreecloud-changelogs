import fs from 'node:fs/promises';
import path from 'node:path';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';

const CHANGE_ID_RE = /^GC-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{3,}$/;

export async function createValidator(schemaPath = new URL('../schema/change.schema.json', import.meta.url)) {
  const schema = JSON.parse(await fs.readFile(schemaPath, 'utf8'));
  const ajv = new Ajv({ allErrors: true, strict: true });
  addFormats(ajv);
  return ajv.compile(schema);
}

export async function validateRecord(record, schemaPath) {
  const validate = await createValidator(schemaPath);
  const valid = validate(record);
  return { valid: Boolean(valid), errors: validate.errors ?? [] };
}

export function canonicalDate(input = new Date()) {
  const d = input instanceof Date ? input : new Date(input);
  if (Number.isNaN(d.valueOf())) throw new TypeError('Invalid date');
  return d.toISOString().slice(0, 10);
}

export function formatChangeId(date, sequence) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) throw new TypeError('date must be YYYY-MM-DD');
  if (!Number.isInteger(sequence) || sequence < 1) throw new TypeError('sequence must be a positive integer');
  return `GC-${date}-${String(sequence).padStart(3, '0')}`;
}

export function isChangeId(value) {
  return typeof value === 'string' && CHANGE_ID_RE.test(value);
}

async function withFileLock(lockDir, fn, { retries = 100, delayMs = 20 } = {}) {
  await fs.mkdir(path.dirname(lockDir), { recursive: true });
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      await fs.mkdir(lockDir);
      try {
        return await fn();
      } finally {
        await fs.rm(lockDir, { recursive: true, force: true });
      }
    } catch (error) {
      if (error?.code !== 'EEXIST' || attempt === retries) throw error;
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
  }
}

export async function allocateChangeId({ root = '.changelogs', now = new Date() } = {}) {
  const date = canonicalDate(now);
  const stateDir = path.join(root, 'state');
  const countersPath = path.join(stateDir, 'counters.json');
  const lockDir = path.join(stateDir, '.allocator.lock');

  return withFileLock(lockDir, async () => {
    await fs.mkdir(stateDir, { recursive: true });
    let counters = {};
    try {
      counters = JSON.parse(await fs.readFile(countersPath, 'utf8'));
    } catch (error) {
      if (error?.code !== 'ENOENT') throw error;
    }

    const next = Number(counters[date] ?? 0) + 1;
    counters[date] = next;

    const temp = `${countersPath}.${process.pid}.${Date.now()}.tmp`;
    await fs.writeFile(temp, `${JSON.stringify(counters, null, 2)}\n`, { flag: 'wx' });
    await fs.rename(temp, countersPath);
    return formatChangeId(date, next);
  });
}

export async function storeRecord(record, { root = '.changelogs', schemaPath } = {}) {
  const result = await validateRecord(record, schemaPath);
  if (!result.valid) {
    const error = new Error('Change record failed schema validation');
    error.validationErrors = result.errors;
    throw error;
  }
  if (!isChangeId(record.change_id)) throw new Error('Invalid change_id');

  const recordsDir = path.join(root, 'records');
  await fs.mkdir(recordsDir, { recursive: true });
  const finalPath = path.join(recordsDir, `${record.change_id}.json`);
  const tempPath = `${finalPath}.${process.pid}.${Date.now()}.tmp`;

  await fs.writeFile(tempPath, `${JSON.stringify(record, null, 2)}\n`, { flag: 'wx' });
  try {
    await fs.link(tempPath, finalPath);
  } catch (error) {
    if (error?.code === 'EEXIST') throw new Error(`Change record already exists: ${record.change_id}`);
    throw error;
  } finally {
    await fs.rm(tempPath, { force: true });
  }
  return finalPath;
}

export async function allocateAndStore(record, options = {}) {
  const changeId = await allocateChangeId(options);
  const createdAt = options.now instanceof Date ? options.now.toISOString() : new Date(options.now ?? Date.now()).toISOString();
  const complete = {
    schema_version: '1.0.0',
    ...record,
    change_id: changeId,
    created_at: record.created_at ?? createdAt
  };
  const file = await storeRecord(complete, options);
  return { change_id: changeId, file, record: complete };
}
