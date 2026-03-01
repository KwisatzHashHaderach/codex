<#
.SYNOPSIS
  Policy-based ON/OFF network gate for WSL via Hyper-V Firewall (Windows 11 22H2+).

.DESCRIPTION
  - OFF: sets WSL default outbound to Block (inbound remains Block).
  - ON:  sets WSL default outbound to Allow for a short online window.
  - Optional fallback: applies Windows Firewall rules on "vEthernet (WSL)" if Hyper-V cmdlets are unavailable.
  - Optional OpenClaw hardening: writes a simple policy JSON to keep browser/web tools OFF by default.

.EXAMPLE
  # Block outbound traffic from WSL
  .\wsl-network-gate.ps1 -Mode Off

  # Allow outbound traffic for 15 minutes, then auto-block again
  .\wsl-network-gate.ps1 -Mode On -OnlineMinutes 15 -AutoRevert

.NOTES
  Run as Administrator.
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("On", "Off")]
  [string]$Mode,

  [int]$OnlineMinutes = 15,

  [switch]$AutoRevert,

  # Microsoft's documented default WSL VMCreatorId.
  [string]$VMCreatorId = "{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}",

  [switch]$EnableWindowsFirewallFallback,

  # Optional: write a local policy file to remind OpenClaw/browser tooling to stay OFF by default.
  [string]$OpenClawPolicyPath = "$env:ProgramData\\OpenClaw\\network-policy.json"
)

$ErrorActionPreference = "Stop"

function Test-Administrator {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Set-HyperVDefaultPolicy {
  param(
    [string]$VmCreator,
    [ValidateSet("Allow", "Block")]
    [string]$Outbound
  )

  Write-Host "[Hyper-V Firewall] VMCreatorId=$VmCreator | Outbound=$Outbound | Inbound=Block"

  # Ensure a setting object exists first; then enforce defaults.
  if (-not (Get-NetFirewallHyperVVMSetting -Name $VmCreator -ErrorAction SilentlyContinue)) {
    New-NetFirewallHyperVVMSetting -Name $VmCreator -DefaultInboundAction Block -DefaultOutboundAction $Outbound | Out-Null
  }

  Set-NetFirewallHyperVVMSetting -Name $VmCreator -DefaultInboundAction Block -DefaultOutboundAction $Outbound | Out-Null

  $current = Get-NetFirewallHyperVVMSetting -Name $VmCreator
  Write-Host "  -> Effective: Inbound=$($current.DefaultInboundAction), Outbound=$($current.DefaultOutboundAction)"
}

function Set-WindowsFirewallFallbackRule {
  param(
    [ValidateSet("Allow", "Block")]
    [string]$Outbound
  )

  $ruleName = "WSL-Network-Gate-Outbound"
  $ifAlias = "vEthernet (WSL)"

  Write-Warning "Hyper-V cmdlets not found. Applying fallback Windows Firewall rule on '$ifAlias'."

  $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
  if ($existing) {
    Remove-NetFirewallRule -DisplayName $ruleName | Out-Null
  }

  if ($Outbound -eq "Block") {
    New-NetFirewallRule `
      -DisplayName $ruleName `
      -Direction Outbound `
      -Action Block `
      -Enabled True `
      -Profile Any `
      -InterfaceAlias $ifAlias | Out-Null

    Write-Host "  -> Fallback rule enabled (Outbound Block on $ifAlias)."
  } else {
    Write-Host "  -> Fallback rule removed (Outbound allowed by default policy)."
  }
}

function Set-OpenClawPolicy {
  param(
    [string]$Path,
    [ValidateSet("On", "Off")]
    [string]$GateMode
  )

  $directory = Split-Path -Parent $Path
  if (-not (Test-Path $directory)) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
  }

  $webToolsEnabled = $false
  if ($GateMode -eq "On") {
    # Security default: still keep browser/web tools OFF unless explicitly changed by operator.
    $webToolsEnabled = $false
  }

  $policy = [ordered]@{
    updatedUtc = (Get-Date).ToUniversalTime().ToString("o")
    mode = $GateMode
    wslDefaultOutbound = if ($GateMode -eq "On") { "Allow" } else { "Block" }
    openClaw = [ordered]@{
      browserToolsEnabled = $webToolsEnabled
      note = "Keep browser/web tools off by default; only enable for narrowly scoped tasks."
    }
  }

  $policy | ConvertTo-Json -Depth 5 | Set-Content -Path $Path -Encoding UTF8
  Write-Host "[OpenClaw Policy] Wrote $Path"
}

if (-not (Test-Administrator)) {
  throw "Bitte PowerShell als Administrator starten."
}

$hyperVCmdletsAvailable = (Get-Command Set-NetFirewallHyperVVMSetting -ErrorAction SilentlyContinue) -and
                         (Get-Command Get-NetFirewallHyperVVMSetting -ErrorAction SilentlyContinue)

if ($Mode -eq "Off") {
  if ($hyperVCmdletsAvailable) {
    Set-HyperVDefaultPolicy -VmCreator $VMCreatorId -Outbound Block
  } elseif ($EnableWindowsFirewallFallback) {
    Set-WindowsFirewallFallbackRule -Outbound Block
  } else {
    throw "Hyper-V Firewall Cmdlets nicht gefunden. Nutze -EnableWindowsFirewallFallback für Windows Firewall Fallback."
  }

  Set-OpenClawPolicy -Path $OpenClawPolicyPath -GateMode Off
  Write-Host "✅ WSL Network Gate ist OFFLINE (Outbound blockiert)."
  exit 0
}

if ($Mode -eq "On") {
  if ($hyperVCmdletsAvailable) {
    Set-HyperVDefaultPolicy -VmCreator $VMCreatorId -Outbound Allow
  } elseif ($EnableWindowsFirewallFallback) {
    Set-WindowsFirewallFallbackRule -Outbound Allow
  } else {
    throw "Hyper-V Firewall Cmdlets nicht gefunden. Nutze -EnableWindowsFirewallFallback für Windows Firewall Fallback."
  }

  Set-OpenClawPolicy -Path $OpenClawPolicyPath -GateMode On
  Write-Host "✅ WSL Network Gate ist ONLINE (Outbound erlaubt)."

  if ($AutoRevert) {
    if ($OnlineMinutes -lt 1) {
      throw "OnlineMinutes muss >= 1 sein, wenn -AutoRevert verwendet wird."
    }

    Write-Host "⏱️ Auto-Revert aktiv: Schalte in $OnlineMinutes Minute(n) zurück auf OFFLINE."
    Start-Sleep -Seconds ($OnlineMinutes * 60)

    if ($hyperVCmdletsAvailable) {
      Set-HyperVDefaultPolicy -VmCreator $VMCreatorId -Outbound Block
    } else {
      Set-WindowsFirewallFallbackRule -Outbound Block
    }

    Set-OpenClawPolicy -Path $OpenClawPolicyPath -GateMode Off
    Write-Host "✅ Auto-Revert abgeschlossen: WSL Outbound wieder blockiert."
  }
}
