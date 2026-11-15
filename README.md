# SPHEREye

Projeto Next.js. Use Node.js 22 ou superior.

```sh
cd frontend
npm ci
npm run dev
```

Abra [http://localhost:3000](http://localhost:3000). Para gerar a versão estática em `frontend/out`, execute `npm run build` no diretório `frontend`.

Na Vercel, a branch `develop` consulta `https://api.dev.sphereye.earth` por meio das rotas de mesmo domínio em `vercel.json`. Para desenvolvimento local ou outros deploys, configure `NEXT_PUBLIC_API_BASE_URL` antes do build e inclua a origem do frontend em `CORS_ALLOWED_ORIGINS` no backend. Sem essa variável, os exemplos offline ficam disponíveis.
