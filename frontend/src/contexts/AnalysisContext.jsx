import React, { createContext, useContext, useReducer, useCallback } from 'react';

// Action types
const ActionTypes = {
  SET_VIDEO_DATA: 'SET_VIDEO_DATA',
  START_ANALYSIS: 'START_ANALYSIS',
  UPDATE_PROGRESS: 'UPDATE_PROGRESS',
  SET_RESULTS: 'SET_RESULTS',
  SET_ERROR: 'SET_ERROR',
  RESET_ANALYSIS: 'RESET_ANALYSIS',
  UPDATE_COMMENT_FEEDBACK: 'UPDATE_COMMENT_FEEDBACK',
  SET_LOADING: 'SET_LOADING',
};

// Initial state
const initialState = {
  videoData: null,
  analysisId: null,
  analysisState: 'idle', // idle, loading, analyzing, completed, error
  analysisProgress: 0,
  analysisResults: null,
  error: null,
  loading: false,
  commentFeedback: {}, // Track user feedback on comment sentiment
  analysisHistory: [],
};

// Reducer
function analysisReducer(state, action) {
  switch (action.type) {
    case ActionTypes.SET_VIDEO_DATA:
      return { ...state, videoData: action.payload };
    
    case ActionTypes.START_ANALYSIS:
      return { 
        ...state, 
        analysisId: action.payload.analysisId,
        analysisState: 'loading',
        analysisProgress: 0,
        error: null,
      };
    
    case ActionTypes.UPDATE_PROGRESS:
      return {
        ...state,
        analysisState: 'analyzing',
        analysisProgress: action.payload.progress,
      };
    
    case ActionTypes.SET_RESULTS:
      return {
        ...state,
        analysisState: 'completed',
        analysisResults: action.payload,
        analysisProgress: 100,
        error: null,
      };
    
    case ActionTypes.SET_ERROR:
      return {
        ...state,
        analysisState: 'error',
        error: action.payload,
        loading: false,
      };
    
    case ActionTypes.RESET_ANALYSIS:
      return {
        ...state,
        analysisId: null,
        analysisState: 'idle',
        analysisProgress: 0,
        analysisResults: null,
        error: null,
      };
    
    case ActionTypes.UPDATE_COMMENT_FEEDBACK:
      return {
        ...state,
        commentFeedback: {
          ...state.commentFeedback,
          [action.payload.commentId]: action.payload.sentiment,
        },
      };
    
    case ActionTypes.SET_LOADING:
      return { ...state, loading: action.payload };
    
    default:
      return state;
  }
}

// Create context
const AnalysisContext = createContext();

// Provider component
export function AnalysisProvider({ children, initialData }) {
  const [state, dispatch] = useReducer(analysisReducer, {
    ...initialState,
    ...initialData,
  });

  // Action creators
  const actions = {
    setVideoData: useCallback((data) => {
      dispatch({ type: ActionTypes.SET_VIDEO_DATA, payload: data });
    }, []),

    startAnalysis: useCallback((analysisId) => {
      dispatch({ type: ActionTypes.START_ANALYSIS, payload: { analysisId } });
    }, []),

    updateProgress: useCallback((progress) => {
      dispatch({ type: ActionTypes.UPDATE_PROGRESS, payload: { progress } });
    }, []),

    setResults: useCallback((results) => {
      dispatch({ type: ActionTypes.SET_RESULTS, payload: results });
    }, []),

    setError: useCallback((error) => {
      dispatch({ type: ActionTypes.SET_ERROR, payload: error });
    }, []),

    resetAnalysis: useCallback(() => {
      dispatch({ type: ActionTypes.RESET_ANALYSIS });
    }, []),

    updateCommentFeedback: useCallback((commentId, sentiment) => {
      dispatch({ 
        type: ActionTypes.UPDATE_COMMENT_FEEDBACK, 
        payload: { commentId, sentiment } 
      });
    }, []),

    setLoading: useCallback((loading) => {
      dispatch({ type: ActionTypes.SET_LOADING, payload: loading });
    }, []),
  };

  // Computed values
  const computed = {
    isAnalyzing: state.analysisState === 'loading' || state.analysisState === 'analyzing',
    hasResults: state.analysisState === 'completed' && state.analysisResults !== null,
    hasError: state.analysisState === 'error' && state.error !== null,
    canStartAnalysis: state.analysisState === 'idle' || state.analysisState === 'error',
  };

  const value = {
    ...state,
    ...actions,
    ...computed,
    dispatch, // Expose dispatch for custom actions
  };

  return (
    <AnalysisContext.Provider value={value}>
      {children}
    </AnalysisContext.Provider>
  );
}

// Custom hook to use analysis context
export function useAnalysis() {
  const context = useContext(AnalysisContext);
  if (!context) {
    throw new Error('useAnalysis must be used within an AnalysisProvider');
  }
  return context;
}

// Export for testing
export { AnalysisContext, ActionTypes };

export default AnalysisProvider;