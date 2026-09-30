import { describe, it, expect } from 'vitest';
import { projectSchema, analysisSchema } from '@/schemas';

describe('project schema', () => {
  const validProject = {
    id: '3f2504e0-4f89-41d3-9a0c-0305e82c3301',
    name: 'Warehouse rooftops',
    description: null,
    is_archived: false,
    created_at: '2026-01-15T10:00:00Z',
    updated_at: '2026-01-15T10:00:00Z',
  };

  it('parses a valid project', () => {
    const parsed = projectSchema.parse(validProject);
    expect(parsed.name).toBe('Warehouse rooftops');
    expect(parsed.is_archived).toBe(false);
  });

  it('rejects an invalid project (bad id, missing flag)', () => {
    const result = projectSchema.safeParse({
      ...validProject,
      id: 'not-a-uuid',
      is_archived: undefined,
    });
    expect(result.success).toBe(false);
  });
});

describe('analysis schema', () => {
  const validAnalysis = {
    id: 'd3b07384-d9a7-4f9e-8b2a-1c2d3e4f5a6b',
    name: 'Block A',
    status: 'draft',
    project: '3f2504e0-4f89-41d3-9a0c-0305e82c3301',
    area: {
      type: 'Polygon',
      coordinates: [
        [
          [0, 0],
          [0, 1],
          [1, 1],
          [0, 0],
        ],
      ],
    },
    created_at: '2026-01-15T10:00:00Z',
    submitted_at: null,
    completed_at: null,
  };

  it('parses a valid analysis with polygon area', () => {
    const parsed = analysisSchema.parse(validAnalysis);
    expect(parsed.status).toBe('draft');
    expect(parsed.area?.type).toBe('Polygon');
  });

  it('rejects an analysis with an unknown status', () => {
    const result = analysisSchema.safeParse({ ...validAnalysis, status: 'archived' });
    expect(result.success).toBe(false);
  });
});
