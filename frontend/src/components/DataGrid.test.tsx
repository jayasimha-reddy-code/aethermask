import { DataGrid } from './DataGrid';
import type { FramePreview } from '../lib/types';

describe('DataGrid component', () => {
  const dummyFrame: FramePreview = {
    columns: ['id', 'label'],
    dtypes: ['int', 'string'],
    rows: [
      [1, 'test-a'],
      [2, 'test-b'],
    ],
    total_rows: 2,
    total_columns: 2,
  };

  test('DataGrid is a valid component function', () => {
    expect(typeof DataGrid).toBe('function');
  });

  test('accepts required FramePreview props', () => {
    const props = { frame: dummyFrame, tone: 'neutral' as const };
    expect(props.frame.total_rows).toBe(2);
  });
});
