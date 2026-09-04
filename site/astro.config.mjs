// @ts-check
import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://servirentresubnormales-wq.github.io',
  base: '/chatcontrol/',
  output: 'static',
  build: {
    format: 'directory'
  },
  vite: {
    envPrefix: 'PUBLIC_',
  }
});
