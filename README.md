# Telegram Bot for MobileDev

파이썬으로 개발한 텔레그램 봇.

## Environment

봇 토큰과 채팅 ID는 저장소 루트의 `.env`에서 관리합니다.

```env
# 푸드스케치 봇
FSBOT=
FSBOT_CHATID=
```

`.env` 파일은 저장소에 포함되지 않습니다.
계정 정보는 별도 문의 부탁 드립니다.

## 가상 환경 설치

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## 봇 실행 방법

푸드스케치 메뉴 이미지를 보냅니다.

```bash
.venv/bin/python cafeteria/thefoodsketch.py
```

아이밀 메뉴 이미지만 보냅니다.

```bash
.venv/bin/python cafeteria/imeal.py
```

카카오 프로필 메뉴 조회와 텔레그램 사진 전송 로그는 저장소 루트의 `log/kakao_menu.log`에 기록됩니다.
두 단계에서 오류가 발생하면 같은 텔레그램 채팅에 한 줄로 알립니다.
일시적 오류는 최초 시도 후 최대 3번 더 재시도하며(1초·2초·4초 대기), 최종 실패할 때만 알림을 보냅니다.

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

`crontab -e`에서 아래처럼 설정할 수 있습니다. `/path/to/telegram`은 저장소 위치를 나타내는 예시 경로입니다.

```crontab
# 평일 오전 11시 30분: 푸드스케치 메뉴 전송
30 11 * * 1-5 cd /path/to/telegram && .venv/bin/python cafeteria/thefoodsketch.py
```
