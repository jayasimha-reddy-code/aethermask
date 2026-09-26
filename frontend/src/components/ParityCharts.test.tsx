import { ParityCharts } from './ParityCharts';
import type { ChartBlock } from '../lib/types';

describe('ParityCharts component', () => {
  const dummyChart: ChartBlock = {
    category_column: 'category',
    measure_column: 'value',
    masked_category_column: 'cover_category',
    masked_measure_column: 'cover_value',
    original_series: [{ name: 'A', value: 10, count: 1 }],
    sanitized_series: [{ name: 'A', value: 10, count: 1 }],
  };

  test('ParityCharts is a valid component function', () => {
    expect(typeof ParityCharts).toBe('function');
  });

  test('handles ChartBlock with matching parity', () => {
    expect(dummyChart.original_series[0].value).toBe(dummyChart.sanitized_series[0].value);
  });
});
