/**
 * Pre-load localStorage shim for Node.js.
 *
 * Must be imported BEFORE any module that uses zustand persist
 * (e.g. @cofhe/sdk) so that `globalThis.localStorage` exists when
 * zustand evaluates `localStorage` at module-load time.
 */
if (typeof globalThis !== 'undefined' && (!globalThis.localStorage || typeof globalThis.localStorage.setItem !== 'function')) {
  const mem = new Map<string, string>()
  const shim = {
    getItem: (key: string) => (mem.has(key) ? mem.get(key)! : null),
    setItem: (key: string, value: string) => mem.set(key, String(value)),
    removeItem: (key: string) => mem.delete(key),
    clear: () => mem.clear(),
    key: (index: number) => Array.from(mem.keys())[index] ?? null,
    get length() { return mem.size },
  } as Storage
  ;(globalThis as any).localStorage = shim
  if (typeof global !== 'undefined') (global as any).localStorage = shim
  if (typeof window !== 'undefined') (window as any).localStorage = shim
}
