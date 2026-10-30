import { defineConfig } from 'vite';
export default defineConfig({
  envDir: '..',
  server: {
    host: '127.0.0.1',
    port: 5180,
    strictPort: true,
    proxy: { '/api': 'http://127.0.0.1:8010' },
  },
  build: { sourcemap: false },
});
