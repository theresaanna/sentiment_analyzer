import { beforeAll, afterEach, afterAll, vi } from 'vitest';
import '@testing-library/jest-dom';

// Mock fetch globally
global.fetch = vi.fn();

// Mock window.scrollTo for jsdom
global.scrollTo = vi.fn();

// Mock timers for Toast tests
beforeAll(() => {
  // Setup fake timers for tests that need them
  vi.useFakeTimers();
});

afterEach(() => {
  // Clear all mocks after each test
  vi.clearAllMocks();
  
  // Clear all timers
  vi.clearAllTimers();
  
  // Reset fetch mock
  global.fetch.mockReset();
});

afterAll(() => {
  // Restore real timers
  vi.useRealTimers();
});

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
global.localStorage = localStorageMock;

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
  takeRecords() {
    return [];
  }
};