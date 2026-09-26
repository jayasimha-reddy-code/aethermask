import { useReducer, useCallback } from 'react';
import type { Stage } from './types';
import { STAGE_INDEX, STAGES } from '../components/StageRail';

export interface PipelineStageState {
  stage: Stage;
  direction: number;
  visited: Set<Stage>;
}

export type PipelineStageAction =
  | { type: 'GO'; target: Stage }
  | { type: 'NEXT' }
  | { type: 'PREV' }
  | { type: 'RESET' };

export function pipelineStageReducer(
  state: PipelineStageState,
  action: PipelineStageAction,
): PipelineStageState {
  switch (action.type) {
    case 'GO': {
      if (action.target === state.stage) return state;
      const currentIdx = STAGE_INDEX[state.stage];
      const targetIdx = STAGE_INDEX[action.target];
      const direction = targetIdx > currentIdx ? 1 : -1;
      const newVisited = new Set(state.visited);
      newVisited.add(action.target);
      return {
        stage: action.target,
        direction,
        visited: newVisited,
      };
    }
    case 'NEXT': {
      const currentIdx = STAGE_INDEX[state.stage];
      if (currentIdx >= STAGES.length - 1) return state;
      const nextStage = STAGES[currentIdx + 1].id;
      const newVisited = new Set(state.visited);
      newVisited.add(nextStage);
      return {
        stage: nextStage,
        direction: 1,
        visited: newVisited,
      };
    }
    case 'PREV': {
      const currentIdx = STAGE_INDEX[state.stage];
      if (currentIdx <= 0) return state;
      const prevStage = STAGES[currentIdx - 1].id;
      return {
        stage: prevStage,
        direction: -1,
        visited: state.visited,
      };
    }
    case 'RESET': {
      return {
        stage: 'ingest',
        direction: -1,
        visited: new Set<Stage>(['ingest']),
      };
    }
    default:
      return state;
  }
}

export function usePipelineStageReducer(initialStage: Stage = 'ingest') {
  const [state, dispatch] = useReducer(pipelineStageReducer, {
    stage: initialStage,
    direction: 1,
    visited: new Set<Stage>([initialStage]),
  });

  const go = useCallback((target: Stage) => {
    dispatch({ type: 'GO', target });
  }, []);

  const next = useCallback(() => {
    dispatch({ type: 'NEXT' });
  }, []);

  const prev = useCallback(() => {
    dispatch({ type: 'PREV' });
  }, []);

  const reset = useCallback(() => {
    dispatch({ type: 'RESET' });
  }, []);

  return {
    stage: state.stage,
    direction: state.direction,
    visited: state.visited,
    go,
    next,
    prev,
    reset,
  };
}
