# 사내망 Nginx 운영

루트 `docker-compose.yml`은 Nginx를 사내망 진입점으로 실행한다. Nginx는 호스트의
80번 포트에서 요청을 받고 웹 UI와 `/api/*` 요청을 통합 FastAPI 서버로 전달한다.
애플리케이션의 8000번 포트는 호스트의 `127.0.0.1`에만 열려 있어 다른 PC에서
직접 접근할 수 없다.

## 실행

Docker Desktop이 실행 중인 서버에서 저장소 루트를 열고 다음 명령을 실행한다.

```powershell
docker compose up -d --build
docker compose ps
```

서버에서는 `http://localhost`, 사내 다른 PC에서는 `http://서버의-사내-IP`로
접속한다. API 문서는 `http://서버의-사내-IP/api/v1/docs`에서 확인한다.

서버의 IPv4 주소는 다음 명령으로 확인할 수 있다.

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike '127.*' -and $_.AddressState -eq 'Preferred' } |
  Select-Object InterfaceAlias,IPAddress
```

## Windows 방화벽

관리자 권한 PowerShell에서 Domain/Private 네트워크와 같은 로컬 서브넷에만
HTTP 80번 포트를 허용한다.

```powershell
New-NetFirewallRule `
  -DisplayName "Synthetic Data Studio HTTP" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 80 `
  -Action Allow `
  -Profile Domain,Private `
  -RemoteAddress LocalSubnet
```

회사 네트워크가 별도 대역을 사용하면 네트워크 관리자에게 승인된 CIDR을 확인한 뒤
`-RemoteAddress` 값을 해당 대역으로 바꾼다. Public 프로필에는 포트를 열지 않는다.

## 점검과 운영

```powershell
curl.exe http://localhost/nginx-health
docker compose logs -f nginx
docker compose restart nginx
docker compose down
```

정상 상태에서는 헬스 체크가 `ok`를 반환한다. 80번 포트를 다른 프로그램이 사용하면
`docker-compose.yml`의 `"80:80"`을 `"8080:80"`으로 변경하고
`http://서버의-사내-IP:8080`으로 접속한다.

현재 설정은 사내망 HTTP용이다. 조직 정책상 HTTPS가 필요하면 사내 DNS 이름과
조직에서 발급한 인증서를 받은 뒤 Nginx에 443번 TLS 설정을 추가한다.
