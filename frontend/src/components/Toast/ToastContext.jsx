import React, { createContext, useContext, useState, useCallback } from 'react';
import { TOAST_VARIANTS, DASHBOARD_CONFIG } from '../../utils/dashboardUtils';

/**
 * Toast Context for managing notifications
 */
const ToastContext = createContext({
  toasts: [],
  showToast: () => {},
  hideToast: () => {},
});

/**
 * Hook to use the toast context
 */
export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

/**
 * Toast Provider Component
 */
export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const showToast = useCallback((message, variantOrType = TOAST_VARIANTS.INFO, duration = DASHBOARD_CONFIG.TOAST_DURATION) => {
    const id = Date.now() + Math.random();
    // Support both 'variant' and 'type' for compatibility
    const variant = variantOrType === 'error' ? 'danger' : variantOrType;
    const newToast = {
      id,
      message,
      variant,
      type: variant, // Also set type for test compatibility
      duration,
    };

    setToasts(prev => [...prev, newToast]);

    // Auto-hide after duration
    if (duration > 0) {
      setTimeout(() => {
        hideToast(id);
      }, duration);
    }

    return id;
  }, []);

  const hideToast = useCallback((id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, showToast, hideToast }}>
      {children}
    </ToastContext.Provider>
  );
};

export default ToastContext;