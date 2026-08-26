import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { allocateChangeId, formatChangeId, storeRecord, validateRecord } from '../src/core.mjs';

async function tempRoot() {
  return fs.mkdtemp(path.join(os.tmpdir(), 'goreecloud-changelogs-'));
}

function validRecord(changeId = 'GC-2026-08-26-001') {
  return {
    schema_version: '1.0.0',
    change_id: changeId,
    created_at: '2026-08-26T23:30:00.000Z',
    summary: 'Implement Changelogs Core v1 test record.',
    change_type: 'Added',
    components: ['GoreeCloud Changelogs'],
    maturity: 'Implemented',
    status: 'Implemented',
    visibility: 'internal',
    evidence: []
  };
}

test('formats zero-padded change IDs', () => {
  assert.equal(formatChangeId('2026-08-26', 4), 'GC-2026-08-26-004');
  assert.equal(formatChangeId('2026-08-26', 1000), 'GC-2026-08-26-1000');
});

test('allocator increments atomically for one filesystem root', async () => {
  const root = await tempRoot();
  const now = new Date('2026-08-26T23:30:00.000Z');
  const ids = await Promise.all(Array.from({ length: 20 }, () => allocateChangeId({ root, now })));
  assert.equal(new Set(ids).size, 20);
  assert.equal(ids.includes('GC-2026-08-26-001'), true);
  assert.equal(ids.includes('GC-2026-08-26-020'), true);
});

test('schema validator accepts canonical record', async () => {
  const result = await validateRecord(validRecord());
  assert.equal(result.valid, true, JSON.stringify(result.errors));
});

test('schema validator rejects missing required fields', async () => {
  const record = validRecord();
  delete record.summary;
  const result = await validateRecord(record);
  assert.equal(result.valid, false);
});

test('record store is create-only and rejects duplicate IDs', async () => {
  const root = await tempRoot();
  const record = validRecord();
  const stored = await storeRecord(record, { root });
  assert.equal(JSON.parse(await fs.readFile(stored, 'utf8')).change_id, record.change_id);
  await assert.rejects(() => storeRecord(record, { root }), /already exists/);
});
