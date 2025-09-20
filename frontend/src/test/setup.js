import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock window.fetch globally
global.fetch = vi.fn()

// Mock window.scrollTo for jsdom
global.scrollTo = vi.fn()

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true
})

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
  takeRecords() {
    return []
  }
}

// Reset all mocks before each test
beforeEach(() => {
  vi.clearAllMocks()
  global.fetch.mockClear()
  localStorageMock.getItem.mockClear()
  localStorageMock.setItem.mockClear()
  localStorageMock.removeItem.mockClear()
  localStorageMock.clear.mockClear()
})

// Clean up after each test
afterEach(() => {
  vi.restoreAllMocks()
})
