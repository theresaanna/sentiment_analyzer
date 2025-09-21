import { useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';

// Toast types
export const ToastTypes = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info',
};

// Toast component
function Toast({ message, type, duration, onClose }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const getIcon = () => {
    switch (type) {
      case ToastTypes.SUCCESS:
        return '✓';
      case ToastTypes.ERROR:
        return '✕';
      case ToastTypes.WARNING:
        return '⚠';
      case ToastTypes.INFO:
      default:
        return 'ℹ';
    }
  };

  const getClassName = () => {
    const baseClass = 'toast-notification';
    const typeClass = `toast-${type}`;
    return `${baseClass} ${typeClass}`;
  };

  return (
    <div className={getClassName()}>
      <div className="toast-icon">{getIcon()}</div>
      <div className="toast-message">{message}</div>
      <button className="toast-close" onClick={onClose}>×</button>
    </div>
  );
}

// Toast container manager
class ToastManager {
  constructor() {
    this.toasts = new Map();
    this.container = null;
    this.root = null;
    this.init();
  }

  init() {
    if (typeof document === 'undefined') return;

    // Create container if it doesn't exist
    if (!this.container) {
      this.container = document.getElementById('toast-container');
      
      if (!this.container) {
        this.container = document.createElement('div');
        this.container.id = 'toast-container';
        this.container.className = 'toast-container';
        document.body.appendChild(this.container);
      }

      // Create React root for the container
      this.root = createRoot(this.container);
    }
  }

  show(message, type = ToastTypes.INFO, duration = 3000) {
    const id = Date.now() + Math.random();
    
    this.toasts.set(id, {
      message,
      type,
      duration,
      onClose: () => this.remove(id),
    });

    this.render();
    return id;
  }

  remove(id) {
    this.toasts.delete(id);
    this.render();
  }

  clear() {
    this.toasts.clear();
    this.render();
  }

  render() {
    if (!this.root) return;

    const toastElements = Array.from(this.toasts.entries()).map(([id, props]) => (
      <Toast key={id} {...props} />
    ));

    this.root.render(
      <div className="toast-wrapper">
        {toastElements}
      </div>
    );
  }
}

// Create singleton instance
const toastManager = new ToastManager();

// Custom hook for using toast notifications
export function useToast() {
  const showToast = useCallback((message, type = ToastTypes.INFO, duration = 3000) => {
    return toastManager.show(message, type, duration);
  }, []);

  const showSuccess = useCallback((message, duration) => {
    return showToast(message, ToastTypes.SUCCESS, duration);
  }, [showToast]);

  const showError = useCallback((message, duration) => {
    return showToast(message, ToastTypes.ERROR, duration);
  }, [showToast]);

  const showWarning = useCallback((message, duration) => {
    return showToast(message, ToastTypes.WARNING, duration);
  }, [showToast]);

  const showInfo = useCallback((message, duration) => {
    return showToast(message, ToastTypes.INFO, duration);
  }, [showToast]);

  const clearToasts = useCallback(() => {
    toastManager.clear();
  }, []);

  return {
    showToast,
    showSuccess,
    showError,
    showWarning,
    showInfo,
    clearToasts,
  };
}

// Export for direct usage outside React components
export const toast = {
  success: (message, duration) => toastManager.show(message, ToastTypes.SUCCESS, duration),
  error: (message, duration) => toastManager.show(message, ToastTypes.ERROR, duration),
  warning: (message, duration) => toastManager.show(message, ToastTypes.WARNING, duration),
  info: (message, duration) => toastManager.show(message, ToastTypes.INFO, duration),
  clear: () => toastManager.clear(),
};

export default useToast;