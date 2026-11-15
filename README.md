# SPHEREye

Projeto Next.js. Use Node.js 22 ou superior.

```sh
cd frontend
npm ci
npm run dev
```

Abra [http://localhost:3000](http://localhost:3000). Para gerar a versão estática em `frontend/out`, execute `npm run build` no diretório `frontend`.

Na Vercel, a branch `develop` consulta `https://api.dev.sphereye.earth` por meio das rotas de mesmo domínio em `vercel.json`. O comando `npm run dev` no frontend usa as mesmas rotas por padrão. Para apontar o servidor local para outra API ou configurar outros deploys, defina `NEXT_PUBLIC_API_BASE_URL` e inclua a origem do frontend em `CORS_ALLOWED_ORIGINS` no backend. Os exemplos offline estão disponíveis em todos os ambientes.
