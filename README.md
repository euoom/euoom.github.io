# euoom — Digital Garden

개발하면서 만든 것, 실험한 것, 실패한 것과 다시 생각하게 된 것을 기록하는 개인 기술 아카이브입니다.

## Publishing flow

공개 글의 원본은 Knowledge Base에 두고, 이 저장소에는 GitHub Pages에서 바로 서비스할 수 있는 정적 결과물을 생성합니다.

```text
knowledge-base/public/post/**/*.md
        ↓
scripts/sync-posts.py
        ↓
posts.json
post/<route>.json
post/<route>/index.html
feed.xml
sitemap.xml
robots.txt
        ↓
   GitHub Pages
```

## Publishing model

`knowledge-base/public/post/`가 글의 작성 원본입니다. 별도의 draft 단계를 두지 않고, 이 디렉터리에서 글을 작성하거나 수정하는 상태 자체를 초안으로 봅니다.

```text
public/post/에서 작성
        ↓
sync
        ↓
euoom.github.io에 정적 결과물 생성 (local staging)
        ↓
local preview
        ↓
commit + push
        ↓
GitHub Pages에 실제 공개
```

따라서 sync만 실행한 상태는 아직 웹에 공개된 것이 아니며, 사이트 저장소를 commit/push하는 시점을 publish 경계로 사용합니다.

## Sync

```bash
python3 scripts/sync-posts.py
```

기본 workspace 구조가 `workspace/knowledge-base`와 `workspace/repository/euoom.github.io`라면 별도 설정 없이 Knowledge Base의 `public/post`를 자동으로 찾습니다. 다른 위치를 사용할 때만 `KB_ROOT` 환경변수나 Git에서 제외되는 `scripts/config.json`의 `knowledge_base_root`로 Knowledge Base 루트를 지정합니다. `--source`는 특정 `public/post` 디렉터리를 일시적으로 직접 지정할 때 사용합니다.

```bash
# 기본 workspace 구조에서는 설정 불필요
python3 scripts/sync-posts.py

# Knowledge Base 위치를 override
KB_ROOT=/path/to/knowledge-base python3 scripts/sync-posts.py

# 또는 로컬 설정 파일 사용
cp scripts/config.example.json scripts/config.json

# 특정 공개 원본을 직접 override
python3 scripts/sync-posts.py --source /path/to/public/post
```

## Frontmatter

```yaml
---
title: "글 제목"
date: "2026-09-27"
tags: ["Architecture", "AI"]
summary: "목록과 메타데이터에 표시할 짧은 설명"
icon: "✦"
featured: true
project_url: "https://example.com/"
---
```

파일명은 기본 slug가 되며 `lowercase-kebab-case.md` 형식을 사용합니다. 하위 디렉터리도 같은 형식을 사용하며 `public/post` 아래 상대 경로가 그대로 URL route가 됩니다. 예를 들어 `public/post/research/foo.md`는 `/post/research/foo/`로 생성됩니다. `project_url`은 선택 사항입니다.

## Local preview

`file://`로 직접 열면 `fetch()`가 제한될 수 있으므로 간단한 HTTP 서버를 사용합니다.

```bash
python3 -m http.server 8000
```

그 다음 브라우저에서 `http://localhost:8000/`을 엽니다.

## Validation

```bash
node --check app.js
node --check post.js
python3 -B scripts/sync-posts.py
python3 -m json.tool posts.json >/dev/null
git diff --check
```
