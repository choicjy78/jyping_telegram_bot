# Telegram Bot for MobileDev

파이썬으로 개발한 텔레그램 봇.

## Environment

봇 토큰과 채팅 ID는 저장소 루트의 `.env`에서 관리합니다.

```env
# 푸드스케치 봇
FSBOT=
FSBOT_CHATID=

# 모바일팀 봇
MDEVBOT=
MDEV_CHATID=

# AI 주말 메시지 생성
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.2
```

`.env` 파일은 저장소에 포함되지 않습니다.
계정 정보는 별도 문의 부탁 드립니다.

## 봇 실행 방법

푸드스케치 메뉴 이미지를 보냅니다.

```bash
/usr/bin/python3 cafeteria/thefoodsketch.py
```

아이밀 메뉴 이미지만 보냅니다.

```bash
/usr/bin/python3 cafeteria/imeal.py
```

카카오 프로필 메뉴 조회와 텔레그램 사진 전송 로그는 저장소 루트의 `log/kakao_menu.log`에 기록됩니다.
두 단계에서 오류가 발생하면 같은 텔레그램 채팅에 한 줄로 알립니다.

서버 상태 메시지를 보냅니다.

```bash
/usr/bin/python3 -m manage.serverstatus
```

서버 상태 메시지를 텔레그램으로 보내지 않고 터미널에만 출력합니다.

```bash
cd telegram
/usr/bin/python3 -m manage.serverstatus --dry-run
```

## crontab 설정 예시

`crontab -e`에서 아래처럼 설정할 수 있습니다. `/path/to/telegram`은 저장소 위치를 나타내는 예시 경로입니다.

```crontab
# 평일 오전 11시 30분: 푸드스케치 메뉴 전송
30 11 * * 1-5 cd /path/to/telegram && /usr/bin/python3 cafeteria/thefoodsketch.py

# 평일 오전 9시: 서버 상태 전송
0 9 * * 1-5 cd /path/to/telegram && /usr/bin/python3 -m manage.serverstatus
```
