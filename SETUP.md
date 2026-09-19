# Development mode
프론트 엔드는 `npm run dev`로 어느정도 바로 확인 가능  
백엔드 API 및 DB 활용 희망할 경우 최소한 MySQL 세팅 필요  
로그인, 회원가입 등 기능 이용 시 GitHub OAuth, App 세팅 필요  

# Production mode
상기 개발 모드 세팅 외 Nginx, Uvicorn, Redis, Beat 등 세팅 필요  

# FIELD_ENCRYPTION_KEY (필수)

`User`의 `github_email` / `name` / `student_id` / `major`는 DB에 암호화되어 저장된다.
복호화 키를 `.env`의 `FIELD_ENCRYPTION_KEY`로 지정해야 하며, **이 값이 없으면
`manage.py`의 모든 명령, gunicorn, celery worker/beat가 기동 단계에서 실패한다.**

키 생성:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

주의사항

- **운영 키를 분실하면 저장된 개인정보를 영구히 복구할 수 없다.** 서버 외부에 별도 백업할 것
- 값에 따옴표나 공백이 섞이면 `ImproperlyConfigured`가 발생하지만, 오류 메시지가 해당 값을 알려주지 않는다
- 암호화된 필드는 `filter()` / `order_by()` / admin `search_fields`에 사용할 수 없다.
  예외 없이 조용히 빈 결과가 나오므로 주의할 것
- 키 교체가 필요하면 `FIELD_ENCRYPTION_KEY`에 리스트로 여러 키를 주어
  `MultiFernet` 기반 로테이션을 사용할 수 있다
