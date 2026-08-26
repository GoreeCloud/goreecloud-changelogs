#!/usr/bin/env node
import fs from 'node:fs/promises';
import { allocateChangeId, validateRecord } from './core.mjs';

const [, , command, ...args] = process.argv;

async function main() {
  if (command === 'allocate') {
    const rootArg = args.find(arg => arg.startsWith('--root='));
    const root = rootArg ? rootArg.slice('--root='.length) : '.changelogs';
    console.log(await allocateChangeId({ root }));
    return;
  }

  if (command === 'validate') {
    const file = args.find(arg => !arg.startsWith('--'));
    if (!file) throw new Error('Usage: npm run validate -- <record.json>');
    const record = JSON.parse(await fs.readFile(file, 'utf8'));
    const result = await validateRecord(record);
    if (!result.valid) {
      console.error(JSON.stringify(result.errors, null, 2));
      process.exitCode = 1;
      return;
    }
    console.log('valid');
    return;
  }

  throw new Error('Usage: node src/cli.mjs <allocate|validate> [arguments]');
}

main().catch(error => {
  console.error(error.stack ?? error.message ?? String(error));
  process.exitCode = 1;
});
