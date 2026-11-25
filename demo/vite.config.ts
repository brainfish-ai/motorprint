import { defineConfig } from 'vite';
import { resolve } from 'node:path';
export default defineConfig({
  root: __dirname,
  base: './',
  build: {
    rollupOptions: { input: { main: resolve(__dirname, 'index.html'), collect: resolve(__dirname, 'collect.html') } },
  },
  server: { port: 5173 },
});
