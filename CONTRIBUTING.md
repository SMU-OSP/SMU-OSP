# 기여 가이드

## 최초 1회 세팅

```bash
poetry install
poetry run pre-commit install
npm --prefix frontend install
```

`pre-commit install`까지 해야 커밋할 때 자동 정렬이 걸린다. **이 단계를 건너뛰면
PR에서 CI 실패.**

## Python

### 사용 도구

[Ruff](https://docs.astral.sh/ruff/)를 사용하며 관련 설정은 `pyproject.toml`의 `[tool.ruff]`섹션을 참조.

```bash
poetry run ruff format .        # 코드 정렬(파일 수정)
poetry run ruff check --fix .   # lint + 자동 수정
poetry run ruff check .         # 판정만 (CI와 동일)
```

커밋 시 `pre-commit`이 위 두 명령을 스테이징된 파일에 자동으로 수행. 훅이
파일을 고치면 커밋이 중단되므로, `git add`로 다시 담아 커밋하면 된다.

### 스타일 기준

[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

#### 주요 기준

| 항목 | 규칙 |
| --- | --- |
| 줄 길이 | 80자 |
| 인덴트 | 스페이스 4칸 |
| 문자열 | 쌍따옴표 `"` |
| import | 표준 라이브러리 → 서드파티 → 프로젝트 순서, 그룹 간 빈 줄 |

### docstring

#### 기준

- **public 인터페이스에는 docstring이 반드시 있어야 합니다.**
- 이름이 `_`로 시작하지 않는 모듈 수준 함수, 클래스, 메서드를 대상으로 합니다.
- Google 스타일 섹션(`Args:`,`Returns:`, `Raises:`, `Attributes:`)을 사용합니다.
- 본문은 한국어로, 섹션 키워드는 형식이 요구하는 대로 영어로 작성합니다.

```python
def enqueue_repository_refresh(
    repository_id: int,
    snapshot_date: date | None = None,
) -> bool:
    """Repository 갱신 작업을 큐에 넣는다.

    이미 PENDING 상태로 진행 중인 갱신이 있으면 중복으로 넣지 않는다.

    Args:
        repository_id: 갱신할 Repository의 PK.
        snapshot_date: 수집 기준 날짜. 없으면 현재 날짜를 쓴다.

    Returns:
        작업을 새로 예약했으면 True. 이미 진행 중이어서 건너뛰었으면 False.

    Raises:
        RepositoryRegistrationError: 저장소를 등록할 수 없는 경우.
    """
```

#### 제외대상

- 모듈·패키지(`__init__.py`) docstring
- `__str__` 같은 매직 메서드
- `__init__`. 생성자 인자는 클래스 docstring의 `Args:`에 작성.
- DRF/Django의 `Meta` 중첩 클래스
- `admin.py`, `apps.py`, `signals.py`, `tests.py`. 프레임워크가 형태를 정해 둔 코드
- `migrations/`. Django가 생성하는 코드이므로 검사 대상 제외

### 기존 코드 예외 (베이스라인)

기존 파일 9개는 docstring이 없는 public 인터페이스가 112개 남아 있어,
`pyproject.toml`의 `[tool.ruff.lint.per-file-ignores]`에 한시적으로 예외로
등록해 두었다. **새로 만드는 파일에는 예외가 없다.**

해당 파일을 수정할 일이 생기면 docstring을 채우고 그 줄을 목록에서 지운다.
목록이 비면 블록 전체를 삭제한다. 목록에 파일을 새로 추가하지는 않는다.

## TypeScript

### 사용 도구

- [Prettier](https://prettier.io/): 포매터. 설정은 `frontend/.prettierrc.json` 참조
- [ESLint](https://eslint.org/): 규칙 검사. 설정은 `frontend/eslint.config.js` 참조

먼저 `npm --prefix frontend install`을 해야 훅이 동작한다.

```bash
cd frontend
npm run format         # 코드 정렬(파일 수정)
npm run format:check   # 정렬 상태만 확인
npm run lint           # 규칙 검사 (CI와 동일)
npm run lint:fix       # 규칙 검사 + 자동 수정
```

### 스타일 기준

[Microsoft TypeScript 스타일 가이드](https://github.com/microsoft/TypeScript/wiki/Coding-guidelines)

#### 주요 기준

| 항목 | 규칙 |
| --- | --- |
| 줄 길이 | 100자 |
| 인덴트 | 스페이스 4칸 |
| 문자열 | 쌍따옴표 `"` |
| 세미콜론 | 사용 |
| 줄바꿈 문자 | 파일의 기존 방식을 유지(`endOfLine: "auto"`) |

`endOfLine`을 `"auto"`로 둔 이유는 이 저장소가 `core.autocrlf=true`라서
작업 폴더는 CRLF, 저장된 내용은 LF이기 때문이다. `"lf"`로 고정하면 Windows에서는
전부 실패하고 CI(Linux)에서는 전부 통과하는, 손으로 맞출 수 없는 상태가 된다.

#### 이름

- 타입 이름은 PascalCase
- 인터페이스에 `I` 접두사를 붙이지 않는다 (`IUser`가 아니라 `User`)
- 함수, 속성, 지역 변수는 camelCase
- 모듈 상수는 UPPER_CASE, 함수형 컴포넌트는 PascalCase를 허용
- 밑줄 접두사는 쓰지 않는다. 단, 안 쓰는 인자는 `_` 표시를 허용
- 백엔드 JSON 키를 그대로 받는 속성은 형태를 강제하지 않는다. `src/api.ts`와
  `src/services/`에서는 `access_token`처럼 snake_case 인자도 허용한다

### JSDoc

#### 기준

- **export되는 public 인터페이스에는 JSDoc이 반드시 있어야 합니다.**
- 함수, 클래스, 메서드, 그리고 `interface`/`type`/`enum` 선언이 대상입니다.
- export되지 않는 모듈 내부 헬퍼는 대상이 아닙니다.
- **타입은 다시 적지 않습니다.** 시그니처에 이미 있으므로 `@param {string} name`이
  아니라 `@param name`으로 씁니다.

```ts
/**
 * 현재 페이지를 포함하는 페이지 번호 묶음을 만든다.
 *
 * @param currentPage 현재 페이지 번호.
 * @param totalPages 전체 페이지 수.
 * @param windowSize 한 번에 보여줄 페이지 수.
 * @returns 화면에 표시할 페이지 번호 배열.
 */
export function getPageWindow(
    currentPage: number,
    totalPages: number,
    windowSize = 10,
): number[] {
```

구조 분해로 받는 인자는 안쪽 속성까지 적어야 한다.

```ts
/**
 * @param props 컴포넌트 props.
 * @param props.open 다이얼로그 열림 상태.
 * @param props.setOpen 열림 상태를 바꾸는 함수.
 */
```

#### 제외대상

- `src/components/ui/`. `chakra-ui/cli snippet add`로 생성되는 코드다. 우리 로직이
  없고 다시 생성하면 덮어써진다. 정렬과 나머지 규칙은 그대로 적용된다.
- `.tsx`의 `@returns`. 반환값이 언제나 렌더링 결과라 "렌더링된 컴포넌트"라는 같은
  문장만 반복된다. 반환값 설명이 의미 있는 `.ts`(api, services, utils)에는 요구한다.
