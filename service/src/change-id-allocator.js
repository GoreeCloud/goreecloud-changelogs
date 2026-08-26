function formatChangeId(date, sequence) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) throw new TypeError('date must be YYYY-MM-DD');
  if (!Number.isInteger(sequence) || sequence < 1) throw new TypeError('sequence must be a positive integer');
  return `GC-${date}-${String(sequence).padStart(3, '0')}`;
}

export class ChangeIdAllocator {
  constructor(state) {
    this.state = state;
  }

  async fetch(request) {
    if (request.method !== 'POST') {
      return new Response('Method Not Allowed', { status: 405 });
    }

    const { date } = await request.json();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date ?? '')) {
      return Response.json({ error: 'date must be YYYY-MM-DD' }, { status: 400 });
    }

    const sequence = await this.state.storage.transaction(async txn => {
      const current = Number((await txn.get('sequence')) ?? 0);
      const next = current + 1;
      await txn.put('sequence', next);
      return next;
    });

    return Response.json({ change_id: formatChangeId(date, sequence), sequence });
  }
}
