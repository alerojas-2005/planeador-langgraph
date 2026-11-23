﻿<#
ejecutar_pruebas.ps1 - Envia las seis preguntas de prueba al endpoint POST /api/v1/chat
y guarda la respuesta y el tiempo de cada una.

Sirve para los dos backends porque exponen el mismo contrato (question, sessionId):
  - Spring AI (pruebachat, rama taller-agentes): -Backend springai
  - LangGraph (FastAPI):                          -Backend langgraph

Con -Backend springai, despues de la pregunta 4 se envia "confirmo" en la MISMA sesion,
porque el reto implementado en Spring AI (confirmacion humana) deja la reserva pendiente
hasta que el usuario confirma.

Los agentes que llama el supervisor no vienen en la respuesta HTTP: se leen en el log
del backend (docker logs pruebachat_backend), que el .bat guarda junto a los resultados.

Cada pregunta usa un sessionId nuevo para que una pregunta no influya en otra.

Uso:
  powershell -ExecutionPolicy Bypass -File tests\ejecutar_pruebas.ps1 -Backend springai -Salida C:\ruta
#>
param(
    [ValidateSet("langgraph", "springai")]
    [string]$Backend = "springai",
    [string]$Url = "http://localhost:8080",
    [int[]]$Preguntas = @(1, 2, 3, 4, 5, 6),
    [string]$Salida = "",
    [int]$TimeoutSegundos = 600,
    [int]$EsperaBackendSegundos = 900
)

$ErrorActionPreference = "Stop"

$casos = @(
    @{ n = "1"; q = "¿Cómo estará el clima en Guatavita el domingo?";
       esperado = "Lluvioso, 7-15 °C, 80 % de lluvia"; agentes = "clima" },
    @{ n = "2"; q = "Somos 4 amigos con 350000 pesos. ¿Nos alcanza para ir a Zipaquirá?";
       esperado = "Costo `$400.000; faltan `$50.000"; agentes = "presupuesto" },
    @{ n = "3"; q = "Somos 2 y queremos ir a Villa de Leyva el sábado. ¿Cómo estará el clima y cuánto nos cuesta?";
       esperado = "Soleado, 5 % de lluvia; `$230.000 en total"; agentes = "clima, presupuesto" },
    @{ n = "4"; q = "Somos 3 y tenemos 250000. Si no llueve mucho y nos alcanza, reserva Suesca para el sábado a nombre de Laura.";
       esperado = "15 % de lluvia; `$210.000, sobran `$40.000; reserva con código RES-..."; agentes = "clima, presupuesto, reservas" },
    @{ n = "5"; q = "Somos 3 con 150000. Si nos alcanza, reserva Suesca el domingo a nombre de Laura.";
       esperado = "Faltan `$60.000; NO debe reservar"; agentes = "presupuesto (y quizá reservas)" },
    @{ n = "6"; q = "¿Quién ganó el mundial de 2022?";
       esperado = "Explica que solo ayuda con salidas de fin de semana"; agentes = "ninguno" }
) | Where-Object { $Preguntas -contains [int]$_.n }

if (-not $Salida) { $Salida = Join-Path (Split-Path -Parent $PSScriptRoot) "docs" }
New-Item -ItemType Directory -Force -Path $Salida | Out-Null

function Enviar([string]$pregunta, [string]$sesion) {
    $cuerpo = @{ question = $pregunta; sessionId = $sesion } | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($cuerpo)
    $reloj = [System.Diagnostics.Stopwatch]::StartNew()
    $res = @{ respuesta = ""; estado = ""; http = ""; ms_servidor = ""; error = "" }
    try {
        $r = Invoke-WebRequest -Uri "$Url/api/v1/chat" -Method Post -Body $bytes `
             -ContentType "application/json; charset=utf-8" -UseBasicParsing -TimeoutSec $TimeoutSegundos
        $lector = New-Object System.IO.StreamReader($r.RawContentStream, [System.Text.Encoding]::UTF8)
        $json = $lector.ReadToEnd() | ConvertFrom-Json
        $res.respuesta = $json.answer; $res.estado = $json.status; $res.http = [int]$r.StatusCode
        if ($json.elapsedMs) { $res.ms_servidor = [int64]$json.elapsedMs }
    } catch {
        $res.error = $_.Exception.Message; $res.estado = "error"
    }
    $reloj.Stop()
    $res.tiempo_s = [math]::Round($reloj.Elapsed.TotalSeconds, 1)
    return $res
}

# 1) Esperar a que el backend responda (Spring Boot tarda en arrancar la primera vez).
Write-Host "Esperando el backend $Backend en $Url ..."
$limite = (Get-Date).AddSeconds($EsperaBackendSegundos)
$listo = $false
while ((Get-Date) -lt $limite) {
    try {
        $h = Invoke-WebRequest -Uri "$Url/health/llm" -UseBasicParsing -TimeoutSec 10
        if ($h.StatusCode -eq 200) { $listo = $true; break }
    } catch { }
    Start-Sleep -Seconds 10
}
if ($listo) { Write-Host "Backend listo." -ForegroundColor Green }
else { Write-Host "El backend no respondió en $EsperaBackendSegundos s. Se intenta igual." -ForegroundColor Yellow }

# 2) Ejecutar las preguntas.
$resultados = @()
foreach ($c in $casos) {
    $sesion = "prueba-$($c.n)-$([guid]::NewGuid().ToString('N').Substring(0,8))"
    Write-Host ""; Write-Host ("=" * 70)
    Write-Host "Pregunta $($c.n): $($c.q)"
    Write-Host "Esperado: $($c.esperado)  |  Agentes esperados: $($c.agentes)"
    Write-Host "Inicio: $(Get-Date -Format 'HH:mm:ss')  sessionId=$sesion"
    $r = Enviar $c.q $sesion
    if ($r.error) { Write-Host "ERROR: $($r.error)" -ForegroundColor Red }
    Write-Host "Respuesta ($($r.tiempo_s) s):" -ForegroundColor Cyan
    Write-Host $r.respuesta
    $resultados += [pscustomobject]@{ n = $c.n; pregunta = $c.q; sessionId = $sesion; hora = (Get-Date -Format 'HH:mm:ss')
        agentes_esperados = $c.agentes; resultado_esperado = $c.esperado; respuesta = $r.respuesta
        estado = $r.estado; http = $r.http; tiempo_s = $r.tiempo_s; tiempo_servidor_ms = $r.ms_servidor; error = $r.error }

    if ($Backend -eq "springai" -and $c.n -eq "4") {
        Write-Host ""; Write-Host "Pregunta 4 (confirmación del reto): confirmo" -ForegroundColor Magenta
        $r2 = Enviar "confirmo" $sesion
        if ($r2.error) { Write-Host "ERROR: $($r2.error)" -ForegroundColor Red }
        Write-Host "Respuesta ($($r2.tiempo_s) s):" -ForegroundColor Cyan
        Write-Host $r2.respuesta
        $resultados += [pscustomobject]@{ n = "4b"; pregunta = "confirmo"; sessionId = $sesion; hora = (Get-Date -Format 'HH:mm:ss')
            agentes_esperados = "ninguno (la reserva la crea el código)"; resultado_esperado = "Reserva confirmada RES-..."
            respuesta = $r2.respuesta; estado = $r2.estado; http = $r2.http; tiempo_s = $r2.tiempo_s
            tiempo_servidor_ms = $r2.ms_servidor; error = $r2.error }
    }
}

# 3) Guardar CSV (Excel) y JSON.
$csv = Join-Path $Salida "resultados_api_$Backend.csv"
$resultados | Export-Csv -Path $csv -NoTypeInformation -Encoding UTF8
$jsonRuta = Join-Path $Salida "resultados_api_$Backend.json"
$jsonTexto = $resultados | ConvertTo-Json -Depth 4
[System.IO.File]::WriteAllText($jsonRuta, $jsonTexto, (New-Object System.Text.UTF8Encoding($false)))

Write-Host ""; Write-Host ("=" * 70)
$resultados | Format-Table n, tiempo_s, estado, http -AutoSize
Write-Host "Guardado en:`n  $csv`n  $jsonRuta" -ForegroundColor Green
