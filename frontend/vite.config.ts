import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  resolve: {
    // Sandpack and our CodeEditor both use CodeMirror. Two copies of these
    // packages break CodeMirror with "Unrecognized extension value".
    dedupe: ['@codemirror/state', '@codemirror/view', '@codemirror/language'],
  },
})
