import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
  const env=loadEnv(mode,process.cwd(),'');
  return {
    plugins:[react(),tailwindcss(),{
      name:'campus-preview-metadata',
      transformIndexHtml() {
        if (!env.VITE_SITE_ORIGIN) return [];
        const url=new URL(env.VITE_SITE_ORIGIN);
        if (url.protocol!=='https:' || url.pathname!=='/' || url.search || url.hash || url.username || url.password) throw new Error('VITE_SITE_ORIGIN debe ser un origen HTTPS sin ruta ni credenciales.');
        return [
          {tag:'meta',attrs:{property:'og:image',content:`${url.origin}/og.png`},injectTo:'head'},
          {tag:'meta',attrs:{name:'twitter:image',content:`${url.origin}/og.png`},injectTo:'head'},
        ];
      },
    }],
    server:{host:'0.0.0.0',proxy:{'/api':{target:env.API_PROXY_TARGET || 'http://127.0.0.1:8000',changeOrigin:true}}},
  };
});
