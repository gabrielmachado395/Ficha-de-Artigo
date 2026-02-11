$ErrorActionPreference = 'Continue'

# Melhorar saída no Windows Terminal/PowerShell (acentos)
try {
  $utf8 = [System.Text.UTF8Encoding]::new($false)
  [Console]::OutputEncoding = $utf8
  $OutputEncoding = $utf8
} catch {}

Write-Output "== Capacitor Android Doctor =="
Write-Output "Pasta: $PSScriptRoot"
Write-Output ""

function Find-Java {
  $candidates = @()

  try { $candidates += (Get-Command java -ErrorAction Stop).Source } catch {}

  $globs = @(
    "$env:ProgramFiles\\Eclipse Adoptium\\*\\bin\\java.exe",
    "$env:ProgramFiles\\Java\\*\\bin\\java.exe",
    "$env:ProgramFiles\\Android\\Android Studio\\jbr\\bin\\java.exe",
    "$env:LocalAppData\\Programs\\Android Studio\\jbr\\bin\\java.exe"
  )

  foreach ($g in $globs) {
    $items = Get-Item $g -ErrorAction SilentlyContinue
    if ($items) { $candidates += ($items | Select-Object -ExpandProperty FullName) }
  }

  $candidates | Select-Object -Unique
}

function Find-AndroidSdk {
  $sdkCandidates = @(
    "$env:ANDROID_SDK_ROOT",
    "$env:ANDROID_HOME",
    "$env:LocalAppData\\Android\\Sdk",
    "$env:UserProfile\\AppData\\Local\\Android\\Sdk"
  ) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique

  return $sdkCandidates
}

Write-Output "== Java =="
$java = Find-Java
if (-not $java -or $java.Count -eq 0) {
  Write-Output "Java nao encontrado (nem no PATH, nem em locais comuns)."
  Write-Output "Instale o JDK 17 (recomendado) ou instale o Android Studio (que vem com 'jbr')."
} else {
  Write-Output "Encontrado(s):"
  $java | ForEach-Object { Write-Output "- $_" }
  Write-Output ""
  try {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    & ($java | Select-Object -First 1) -version 2>&1 | ForEach-Object { Write-Output $_ }
    $ErrorActionPreference = $prev
  } catch {
    $ErrorActionPreference = $prev
  }
}

Write-Output ""
Write-Output "== Android SDK =="
$sdk = Find-AndroidSdk
if (-not $sdk -or $sdk.Count -eq 0) {
  Write-Output "Android SDK nao encontrado em locais comuns."
  Write-Output "Instale o Android Studio e, no SDK Manager, instale pelo menos:"
  Write-Output "- Android SDK Platform (uma versao recente)"
  Write-Output "- Android SDK Build-Tools"
  Write-Output "- Android SDK Command-line Tools (latest)"
} else {
  Write-Output "Encontrado(s):"
  $sdk | ForEach-Object { Write-Output "- $_" }
}

Write-Output ""
Write-Output "== Proximos passos (Windows) =="
Write-Output "1) Se tiver Android Studio, voce pode usar o Java dele:"
Write-Output "   Exemplo (PowerShell):"
Write-Output '   $env:JAVA_HOME="C:\Program Files\Android\Android Studio\jbr"'
Write-Output '   $env:Path="$env:JAVA_HOME\bin;" + $env:Path'
Write-Output ""
Write-Output "2) Gerar APK debug:"
Write-Output "   cd frontend"
Write-Output "   npm run android:apk:debug"
Write-Output ""
Write-Output "Se o build passar, o APK fica em:"
Write-Output "frontend\\android\\app\\build\\outputs\\apk\\debug\\app-debug.apk"
