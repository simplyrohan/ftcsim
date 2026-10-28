import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig, loadEnv } from 'vite';
export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, process.cwd(), ''), ...process.env };
  const backend = env.FTCSIM_BACKEND || 'http://127.0.0.1:9015';
  const sdk = env.FTCSIM_SDK || 'ws://127.0.0.1:1115/ds';
  // Only the development proxy rewrites origins. Production remains same-origin.
  const origin = (proxy: any) => {
    proxy.on('proxyReq', (request: any) => request.setHeader('Origin', backend));
    proxy.on('proxyReqWs', (request: any) => request.setHeader('Origin', backend));
  };
  return {
    plugins: [tailwindcss(), sveltekit()],
    define: { __SDK_PROXY_TARGET__: JSON.stringify(sdk) },
    server: { port: 5173, strictPort: true, proxy: {
      '/sim': { target: backend, ws: true, changeOrigin: true, configure: origin },
      '/sdk': { target: new URL(sdk).origin, ws: true, changeOrigin: true, rewrite: () => new URL(sdk).pathname, configure: origin }
    } }
  };
});
