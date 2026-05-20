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
```

`.env` 파일은 저장소에 포함되지 않습니다.
계정 정보는 별도 문의 부탁 드립니다.

## 봇 실행 방법

푸드스케치 메뉴 이미지와 투표를 보냅니다.

```bash
/usr/bin/python3 thefoodsketch.py
```

푸드스케치 투표를 종료하고 결과에 따라 출발 메시지 또는 주변 맛집 링크를 보냅니다.

```bash
/usr/bin/python3 thefoodsketch.py finish
```

서버 상태 메시지를 보냅니다.

```bash
/usr/bin/python3 serverstatus.py
```

서버 상태 메시지를 텔레그램으로 보내지 않고 터미널에만 출력합니다.

```bash
cd telegram
/usr/bin/python3 serverstatus.py --dry-run
```