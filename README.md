# Telegram Bot for MobileDev

파이썬으로 개발한 텔레그램 봇.

## Environment

봇 토큰과 채팅 ID는 저장소 루트의 `.env`에서 관리합니다.

```env
# 푸드스케치 봇
FSBOT=
FSBOT_CHATID=

# 더이룸 인스타그램 조회용 Apify 토큰
APIFY_TOKEN=
```

`.env` 파일은 저장소에 포함되지 않습니다.
계정 정보는 별도 문의 부탁 드립니다.

## 가상 환경 설치

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## 봇 실행 방법

세 식당(아이밀 → 푸드스케치 → 더이룸) 메뉴를 한 번에 보냅니다.
한 식당이 실패해도 나머지는 계속 처리하며, 하나라도 실패하면 종료 코드 1을 반환합니다.
한국 공휴일에는 전체 실행을 건너뜁니다.

```bash
.venv/bin/python cafeteria/run_all.py
```

식당을 개별 실행할 수도 있습니다.

푸드스케치 메뉴 이미지를 보냅니다.

```bash
.venv/bin/python cafeteria/thefoodsketch.py
```

아이밀 메뉴 이미지만 보냅니다.

```bash
.venv/bin/python cafeteria/imeal.py
```

더이룸(`dae_theirum`) 메뉴 이미지는 [Apify Instagram Post Scraper](https://apify.com/apify/instagram-post-scraper)로 조회합니다.
최대 5개 게시물을 요청하고, 응답 순서에서 고정 게시물을 제외한 첫 게시물의 `displayUrl`을 전송합니다.
여러 장인 게시물은 대표 이미지, 영상은 표지 이미지를 사용합니다.

```bash
.venv/bin/python cafeteria/dae_theirum.py
```

`.env`의 `APIFY_TOKEN`을 사용하며, Apify 실행 시 사용량에 따라 비용이 발생할 수 있습니다.
인스타그램 로그인 세션(`INSTAGRAM_SESSIONID`)은 사용하지 않습니다.
기존 봇과 같은 `FSBOT`·`FSBOT_CHATID`를 사용하고, 한국 공휴일에는 전송하지 않습니다.
게시물 조회 실패 시 같은 채팅에 오류를 알리며, 마지막 원문 응답은 `log/apify_last_response.json`에 저장합니다.

메뉴 조회와 텔레그램 사진 전송 로그는 저장소 루트의 `log/kakao_menu.log`에 기록됩니다.
두 단계에서 오류가 발생하면 같은 텔레그램 채팅에 한 줄로 알립니다.
일시적 오류는 최초 시도 후 최대 3번 더 재시도하며(1초·2초·4초 대기), 최종 실패할 때만 알림을 보냅니다.

### 코드 구성

| 파일 | 역할 |
| --- | --- |
| `cafeteria/run_all.py` | 세 식당 통합 실행 진입점 |
| `cafeteria/config.py` | 식당 설정, 환경변수명·로그 경로, 명시적 초기화 |
| `cafeteria/menu_bot.py` | 조회·전송 연결, 메뉴 오류 알림·재시도·공휴일 처리 |
| `lib/kakao_images.py` | 카카오 채널 이미지 조회 |
| `lib/instagram_images.py` | Apify 인스타그램 이미지 조회 |
| `lib/telegram.py` | 텍스트·사진·투표 전송 API |
| `lib/env.py`, `lib/holidays.py` | 환경 파일·환경변수, 한국 공휴일 조회 |
| `lib/retry.py`, `lib/logging_utils.py` | 재시도 판단·대기, 파일 로그 설정 도구 |
| `cafeteria/imeal.py`, `thefoodsketch.py`, `dae_theirum.py` | 식당별 개별 실행 진입점 |

식당을 추가하거나 채널·계정·문구를 바꾸려면 `config.py`의 식당 설정을 수정합니다.
기존 `common.py`와 `runtime.py`의 기능은 위 모듈들로 분리했습니다.
라이브러리를 import하는 것만으로 `.env`를 읽거나 로그 파일을 설정하지 않습니다.
봇 실행 시 `config.initialize()`가 초기화하며, 기존 로그 경로를 유지합니다.

이미지 라이브러리는 식당 설정에 의존하지 않습니다. 인스타그램의 토큰·고정 게시물 제외·
최대 조회 개수·원문 저장 경로는 호출할 때 지정합니다. 원문 저장은 `debug_path`가 있을 때만 수행합니다.

```python
from lib import instagram_images, kakao_images

kakao_url = kakao_images.find_image_url("_vygYn")
instagram_url = instagram_images.find_image_url(
    "dae_theirum", token=apify_token, skip_pinned=True, results_limit=5,
)
```

`lib/telegram.py`는 API 호출만 수행하며, 실패 재시도와 메뉴봇 오류 알림은 `menu_bot.py`가 담당합니다.

### 메뉴 오류 알림 수동 테스트

다음 명령은 카카오 조회 또는 사진 전송 실패를 강제로 만들고, 로그를 기록하며 알림 문구를 터미널에 보여줍니다. 실제 메뉴 사진은 보내지 않습니다.
기본 실행의 오류 알림 전송 성공 로그는 모의 전송 결과입니다.

```bash
.venv/bin/python tests/manual_error_test.py profile
.venv/bin/python tests/manual_error_test.py photo
tail -n 20 log/kakao_menu.log
```

각 테스트 명령에 `--send`를 붙이면 저장소 루트의 `.env`에 설정된 채팅으로 테스트 오류 알림을 실제로 보냅니다.

```bash
.venv/bin/python tests/manual_error_test.py profile --send
.venv/bin/python tests/manual_error_test.py photo --send
```

## crontab 설정 예시

`crontab -e`에서 `cafeteria/run_all.py`만 실행하도록 등록합니다. `/path/to/telegram`은 실제 저장소 경로로 바꿉니다.

```crontab
# 평일 오전 11시 30분: 세 식당 메뉴 전송
30 11 * * 1-5 cd /path/to/telegram && .venv/bin/python cafeteria/run_all.py
```

기존 `imeal.py`, `thefoodsketch.py`, `dae_theirum.py`의 개별 크론탭 항목은 삭제하고 위 항목 하나만 유지합니다.
