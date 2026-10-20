# SAMSAM 애플리케이션 구조

## 요청 흐름

```text
Browser → views → services → models → CockroachDB
```

- `views`: HTTP 입력, 세션, 상태 코드와 응답
- `services`: 검증, 접근 권한, 퀴즈 구성 규칙
- `models`: SQLAlchemy 엔티티와 관계
- `templates`: `base.html`을 상속하는 Jinja 화면
- `static/pages`: 페이지별 JavaScript
- `static/shared`: API 통신·CSRF·오류 처리와 화면 간 공통 명칭
- `static/study`: 답안 UI, 긴 본문·해석의 페이지 나누기, 키보드, 오답 반복 큐
- `static/styles`: 디자인 토큰, 공통 스타일, 페이지별 스타일
- `templates/components`: 재사용하는 Jinja 컴포넌트(학습 방식 카드 등)

## 학습 기능의 책임

| 파일 | 책임 |
|---|---|
| `services/article_repository.py` | 로컬 기사 JSON과 단어 세트 식별자 |
| `services/sentences.py` | 본문 문장 추출, 문맥·해석 힌트 구성 |
| `services/cloze.py` | 임의 본문의 빈칸·보기 생성 |
| `services/grading.py` | 답안 검증, 뜻 정규화, 정오답 판정 |
| `services/study_modes.py` | 유형별 문항 조합과 재현 가능한 학습 회차 |
| `views/study_views.py` | 접근 권한, 서명 토큰, HTTP 응답과 최종 기록 저장 |
| `static/pages/quiz.js` | 학습 화면 상태와 진행 흐름 |
| `static/study/answer_renderer.js` | 각 문항 유형의 답안 입력 UI |
| `static/study/choice_reader.js` | 긴 해석 보기와 정답 해석의 페이지 넘김 |

로컬 실행은 SQLite를 사용한다. 기사와 번역은 `app/data/article_passages.json`에 있고
단어 세트는 `app/data/erw_vocabulary.json`에서 초기화한다. 구조 정리를 위한 DB 스키마 변경은 없다.

## 스타일과 정적 파일

`var.css` → `common.css` → 해당 페이지 CSS 순서로 로드한다.
세트 상세 메뉴는 `quiz_detail.css`, 학습실은 `quiz.css`가 담당한다.
템플릿은 `asset_url('경로')`를 사용하며 `app/assets.py`가 파일 변경 시 버전을 자동 갱신한다.
JS 모듈과 CSS는 캐시를 재검증하므로 의존 파일 변경도 새로고침 후 반영된다.
`package.json`은 ES 모듈과 Node 테스트 명령만 정의한다. 번들러나 npm 설치 단계는 필요하지 않다.

## 의존 규칙

1. `views`는 `services`와 `models`를 사용한다.
2. `services`는 필요한 데이터 계층·다른 서비스를 사용하며 Flask 요청 객체에 의존하지 않는다.
3. `models`는 상위 계층을 import하지 않는다.
4. 새 화면은 `base.html`을 상속하고 공통 색상·크기는 `var.css`에서 관리한다.
5. 페이지 전용 JavaScript와 CSS는 실제 동작이나 표현이 있을 때만 추가한다.
6. 브라우저 API 호출은 `shared/api.js`를 통해 CSRF와 오류 처리를 통일한다.
7. 답안 UI는 상태를 직접 저장하거나 네트워크를 호출하지 않고 콜백으로 페이지에 전달한다.
8. 테스트는 Python API·출제·채점, Node 키보드·큐·입력 UI·통신 동작을 검증한다.
