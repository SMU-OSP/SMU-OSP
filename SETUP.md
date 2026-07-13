# Development mode
프론트 엔드는 `npm run dev`로 어느정도 바로 확인 가능  
백엔드 API 및 DB 활용 희망할 경우 최소한 MySQL 세팅 필요  
로그인, 회원가입 등 기능 이용 시 GitHub OAuth, App 세팅 필요  

# Production mode
상기 개발 모드 세팅 외 Nginx, Uvicorn, Redis, Beat 등 세팅 필요  

# Docker (local development / test)
로컬 개발 및 테스트용 컨테이너 환경 (배포용 아님)

```bash
cp .env.example .env      # 값 확인 후 필요 시 수정
docker compose up --build
```

- 프론트엔드: http://127.0.0.1:5173
- 백엔드 API: http://127.0.0.1:8000
- MySQL: `127.0.0.1:3306`, Redis: `127.0.0.1:6379`
- 서비스 구성: `frontend`, `backend`, `worker`(Celery), `beat`(Celery beat), `db`(MySQL), `redis`
- 코드는 볼륨 마운트되어 있어 백엔드/프론트엔드 모두 변경 시 자동 반영(HMR)
- CORS/CSRF 허용 도메인 문제를 피하려면 `localhost`가 아닌 `127.0.0.1:5173`으로 접속

