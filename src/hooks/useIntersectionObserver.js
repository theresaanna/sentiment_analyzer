import { useEffect, useRef, useCallback } from 'react';

/**
 * Custom hook for intersection observer to detect when an element is visible
 * Used for infinite scroll implementation
 * 
 * @param {Function} callback - Function to call when element intersects
 * @param {Object} options - Intersection observer options
 * @returns {React.RefObject} - Ref to attach to the target element
 */
const useIntersectionObserver = (
  callback,
  options = {
    root: null,
    rootMargin: '100px',
    threshold: 0.1
  }
) => {
  const targetRef = useRef(null);
  const observerRef = useRef(null);
  const callbackRef = useRef(callback);

  // Update callback ref when callback changes
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  const handleIntersection = useCallback((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        callbackRef.current();
      }
    });
  }, []);

  useEffect(() => {
    // Create observer
    if (!observerRef.current && window.IntersectionObserver) {
      observerRef.current = new IntersectionObserver(
        handleIntersection,
        options
      );
    }

    const observer = observerRef.current;
    const target = targetRef.current;

    // Start observing
    if (observer && target) {
      observer.observe(target);
    }

    // Cleanup
    return () => {
      if (observer && target) {
        observer.unobserve(target);
      }
    };
  }, [handleIntersection, options.root, options.rootMargin, options.threshold]);

  // Cleanup observer on unmount
  useEffect(() => {
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
        observerRef.current = null;
      }
    };
  }, []);

  return targetRef;
};

export default useIntersectionObserver;