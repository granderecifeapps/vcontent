# VContent

Plataforma de organização de conteúdo para agência: clientes, peças de TikTok e Instagram, calendário e aprovação.

A parte local usa PostgreSQL e um storage compatível com S3 (MinIO). Nada fica só na memória do navegador.

## Subir na sua máquina

Requisitos: Docker Desktop, Python 3.12+ e Node.js 20+.

Na pasta `vcontent`:

```powershell
docker compose up -d
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --port 8010
```

Em outro terminal:

```powershell
cd frontend
npm install
npm run dev
```

Abra http://localhost:3010

Acesso inicial da administradora, definido em `backend/.env`:

- e-mail: `admin@vcontent.local`
- senha: `Admin!2026`

Troque essa senha em Configurações antes de qualquer uso compartilhado.

O frontend fala com a API por `/backend`, no mesmo endereço do site. Os cookies de sessão não vão para o JavaScript.

## O que já funciona

- Login, sessão, recuperação de senha e troca de senha.
- Dois perfis: administradora e cliente, com a regra repetida na API.
- Clientes com acesso próprio, logo, ativação e exclusão lógica.
- Conteúdos de TikTok (foto, carrossel, vídeo, com hashtags) e Instagram (post, carrossel, reels, stories, sem hashtags).
- Upload de JPG, JPEG, PNG, WEBP, MP4 e MOV no MinIO, com pré-visualização e ordem do carrossel.
- Fluxo de status: rascunho, aguardando, aprovado, ajustes, em revisão, reenviado, publicado e cancelado.
- Aprovação em card, com arraste e botões. Ajuste só entra com motivo.
- Histórico preservado a cada rodada.
- Calendário mensal, semanal e diário.
- Notificações internas. E-mail e WhatsApp têm um ponto de extensão, ainda sem envio.
- Auditoria das ações sensíveis.

Testes do fluxo crítico:

```powershell
cd backend
.\.venv\Scripts\python -m pytest
```

## Deploy gratuito, no passo seguinte

A aplicação já separa configuração por ambiente. O caminho sem custo fixo é:

- Frontend Next.js na Vercel.
- PostgreSQL no plano gratuito do Supabase ou do Neon. A variável é `DATABASE_URL`.
- Arquivos no Storage S3 do Supabase ou no Cloudflare R2. As variáveis `S3_ENDPOINT`, `S3_PUBLIC_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` e `S3_BUCKET` já são as da API.
- API FastAPI em um serviço com processo contínuo (Render, Koyeb ou Fly no free tier). Não dá para encaixar este FastAPI dentro da função serverless da Vercel sem reescrever a API.

No ar, defina `APP_ENV=production`, `COOKIE_SECURE=true`, `SECRET_KEY` longa e uma senha nova da administradora. O link de redefinição de senha deixa de aparecer na resposta e passa a depender do canal externo, que ainda será ligado.

Rode `alembic upgrade head` uma vez no banco de produção antes de abrir a API.
