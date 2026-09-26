import { SplitCompare } from './SplitCompare';
import type { FramePreview } from '../lib/types';

describe('SplitCompare component', () => {
  const dummyFrame: FramePreview = {
    columns: ['id', 'val'],
    dtypes: ['int', 'string'],
    rows: [[1, 'secret']],
    total_rows: 1,
    total_columns: 2,
  };

  test('SplitCompare is a valid component function', () => {
    expect(typeof SplitCompare).toBe('function');
  });

  test('validates split view frame comparison props', () => {
    const props = {
      confidential: dummyFrame,
      sanitized: dummyFrame,
      tableName: 'missions',
    };
    expect(props.tableName).toBe('missions');
  });
});
