import React from 'react';
import { useToast } from './ToastContext';
import { escapeHtml } from '../../utils/dashboardUtils';
import './Toast.css';

/**
 * Toast variant configuration
 */
const variantConfig = {
  success: {
    gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    icon: '✅',
    textColor: 'text-white',
    borderColor: '#059669'
  },
  danger: {
    gradient: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
    icon: '❌',
    textColor: 'text-white',
    borderColor: '#dc2626'
  },
  warning: {
    gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
    icon: '⚠️',
    textColor: 'text-white',
    borderColor: '#d97706'
  },
  info: {
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    icon: 'ℹ️',
    textColor: 'text-white',
    borderColor: '#764ba2'
  }
};

/**
 * Individual Toast Component
 */
const Toast = ({ toast, onClose }) => {
  const config = variantConfig[toast.variant] || variantConfig.info;
  
  return (
    <div 
      className={`toast align-items-center ${config.textColor} border-0 show`}
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
      style={{
        minWidth: '350px',
        background: config.gradient,
        border: `2px solid ${config.borderColor}`,
        borderRadius: '12px',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
        backdropFilter: 'blur(10px)',
        animation: 'slideInRight 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        transformOrigin: 'top right',
        marginBottom: '10px',
      }}
    >
      <div className="d-flex align-items-center" style={{ padding: '8px' }}>
        <div className="toast-body d-flex align-items-center" style={{ fontWeight: 500 }}>
          <span 
            className="me-3" 
            style={{ 
              fontSize: '1.3rem', 
              filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))' 
            }}
          >
            {config.icon}
          </span>
          <span style={{ fontSize: '0.95rem', letterSpacing: '0.3px' }}>
            {escapeHtml(toast.message)}
          </span>
        </div>
        <button
          type="button"
          className="btn-close btn-close-white me-2 m-auto"
          style={{ 
            opacity: 0.9, 
            filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.3))' 
          }}
          onClick={() => onClose(toast.id)}
          aria-label="Close"
        />
      </div>
    </div>
  );
};

/**
 * Toast Container Component
 */
const ToastContainer = () => {
  const { toasts, hideToast } = useToast();

  return (
    <div aria-live="polite" aria-atomic="true" className="position-relative">
      <div 
        className="toast-container position-fixed top-0 end-0 p-3"
        style={{ zIndex: 1100 }}
      >
        {toasts.map(toast => (
          <Toast 
            key={toast.id} 
            toast={toast} 
            onClose={hideToast}
          />
        ))}
      </div>
    </div>
  );
};

export default ToastContainer;