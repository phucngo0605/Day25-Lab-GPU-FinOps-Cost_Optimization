param(
    [ValidateSet("start", "stop", "tunnel", "status", "test")]
    [string]$Command = "start"
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$NgrokOut = Join-Path $ProjectDir ".ngrok.out.log"
$NgrokErr = Join-Path $ProjectDir ".ngrok.err.log"

function Wait-Docker {
    $deadline = (Get-Date).AddMinutes(3)
    do {
        docker info *> $null
        if ($LASTEXITCODE -eq 0) {
            return
        }
        Start-Sleep -Seconds 5
    } while ((Get-Date) -lt $deadline)

    throw "Docker Desktop is not ready. Start Docker Desktop and try again."
}

function Get-NgrokUrl {
    try {
        $tunnels = (Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 3).tunnels
        return ($tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1).public_url
    } catch {
        return $null
    }
}

function Start-NgrokTunnel {
    $existing = Get-Process -Name ngrok -ErrorAction SilentlyContinue
    if ($existing) {
        $existing | Stop-Process -Force
        Start-Sleep -Seconds 1
    }

    foreach ($file in @($NgrokOut, $NgrokErr)) {
        if (Test-Path $file) {
            Remove-Item -LiteralPath $file -Force
        }
    }

    Start-Process -FilePath "ngrok" `
        -ArgumentList @("http", "8000", "--log=stdout") `
        -RedirectStandardOutput $NgrokOut `
        -RedirectStandardError $NgrokErr `
        -WindowStyle Hidden

    $deadline = (Get-Date).AddSeconds(45)
    do {
        Start-Sleep -Seconds 2
        $url = Get-NgrokUrl
        if ($url) {
            Write-Host ""
            Write-Host "TUNNEL ACTIVE"
            Write-Host "URL: $url"
            Write-Host ""
            Write-Host "Use this in notebook:"
            Write-Host "GATEWAY_URL = `"$url`""
            return
        }
    } while ((Get-Date) -lt $deadline)

    throw "ngrok tunnel URL not found. Check $NgrokErr and $NgrokOut."
}

Push-Location $ProjectDir
try {
    switch ($Command) {
        "start" {
            Wait-Docker
            docker compose up --build -d
            Start-Sleep -Seconds 5
            Invoke-RestMethod -Uri "http://localhost:8000/" -TimeoutSec 10 | Out-Null
            Write-Host "All services running at http://localhost:8000"
        }
        "tunnel" {
            Invoke-RestMethod -Uri "http://localhost:8000/" -TimeoutSec 10 | Out-Null
            Start-NgrokTunnel
        }
        "test" {
            $endpoints = @("/", "/cluster/nodes", "/cluster/metrics", "/billing/pricing", "/spot/pricing", "/autoscaler/policy", "/cost/dashboard")
            foreach ($endpoint in $endpoints) {
                $response = Invoke-WebRequest -Uri "http://localhost:8000$endpoint" -UseBasicParsing -TimeoutSec 10
                Write-Host ("OK {0} {1}" -f $response.StatusCode, $endpoint)
            }
        }
        "status" {
            docker compose ps
            Write-Host ""
            Write-Host "Gateway:"
            Invoke-RestMethod -Uri "http://localhost:8000/" -TimeoutSec 10 | ConvertTo-Json -Depth 5
            Write-Host ""
            $url = Get-NgrokUrl
            if ($url) {
                Write-Host "ngrok: $url"
            } else {
                Write-Host "ngrok: not running"
            }
        }
        "stop" {
            Get-Process -Name ngrok -ErrorAction SilentlyContinue | Stop-Process -Force
            docker compose down
            Write-Host "Stopped Docker services and ngrok."
        }
    }
} finally {
    Pop-Location
}
