# SPDX-License-Identifier: GPL-3.0-only
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string[]]$FilePath,
    [string]$CertificateThumbprint,
    [string]$SignToolPath
)

$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
$certificateDirectory = Join-Path $repoPath 'certificates'
$infoPath = Join-Path $certificateDirectory 'signing-info.json'

# WinVerifyTrust separates an untrusted self-signed root from a broken file digest.
# Verification is offline and does not install the certificate as a trusted root.
if (-not ('UniversalDownloader.SignatureVerifier' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace UniversalDownloader {
    public static class SignatureVerifier {
        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        struct FileInfo {
            public uint Size;
            [MarshalAs(UnmanagedType.LPWStr)] public string Path;
            public IntPtr Handle;
            public IntPtr KnownSubject;
        }
        [StructLayout(LayoutKind.Sequential)]
        struct TrustData {
            public uint Size;
            public IntPtr PolicyCallback, SipClient;
            public uint UiChoice, RevocationChecks, UnionChoice;
            public IntPtr FileInfo;
            public uint StateAction;
            public IntPtr StateData, UrlReference;
            public uint ProviderFlags, UiContext;
        }
        [DllImport("wintrust.dll", ExactSpelling = true, CharSet = CharSet.Unicode)]
        static extern int WinVerifyTrust(IntPtr window, ref Guid action, ref TrustData data);
        public static uint Verify(string path) {
            var file = new FileInfo { Size = (uint)Marshal.SizeOf(typeof(FileInfo)), Path = path };
            var pointer = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(FileInfo)));
            try {
                Marshal.StructureToPtr(file, pointer, false);
                var data = new TrustData {
                    Size = (uint)Marshal.SizeOf(typeof(TrustData)), UiChoice = 2,
                    UnionChoice = 1, FileInfo = pointer, ProviderFlags = 0x1010
                };
                var action = new Guid("00AAC56B-CD44-11D0-8CC2-00C04FC295EE");
                return unchecked((uint)WinVerifyTrust(new IntPtr(-1), ref action, ref data));
            } finally {
                Marshal.DestroyStructure(pointer, typeof(FileInfo));
                Marshal.FreeHGlobal(pointer);
            }
        }
    }
}
'@
}

if (-not $SignToolPath) {
    $sdkPath = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits/10/bin'
    $SignToolPath = Get-ChildItem -LiteralPath $sdkPath -Filter signtool.exe -Recurse |
        Where-Object { $_.Directory.Name -eq 'x64' } |
        Sort-Object FullName -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $SignToolPath -or -not (Test-Path -LiteralPath $SignToolPath)) {
    throw 'Install the Windows SDK signing tools or pass -SignToolPath.'
}

if (-not $CertificateThumbprint -and (Test-Path -LiteralPath $infoPath)) {
    $CertificateThumbprint = (Get-Content -LiteralPath $infoPath -Raw | ConvertFrom-Json).thumbprint
}

if ($CertificateThumbprint) {
    $certificate = Get-Item -LiteralPath "Cert:\CurrentUser\My\$CertificateThumbprint"
} else {
    $certificate = New-SelfSignedCertificate -Type CodeSigningCert `
        -Subject 'CN=Sergio5331' `
        -FriendlyName 'Universal Media Downloader - development signing' `
        -CertStoreLocation 'Cert:\CurrentUser\My' `
        -KeyAlgorithm RSA -KeyLength 3072 -HashAlgorithm SHA256 `
        -KeyExportPolicy NonExportable -NotAfter (Get-Date).AddYears(3)
}
if (-not $certificate.HasPrivateKey -or $certificate.NotAfter -le (Get-Date)) {
    throw 'The certificate must have a private key on this computer and must not be expired.'
}

New-Item -ItemType Directory -Path $certificateDirectory -Force | Out-Null
Export-Certificate -Cert $certificate `
    -FilePath (Join-Path $certificateDirectory 'UniversalDownloader-development.cer') -Force | Out-Null
[ordered]@{
    type = 'self-signed-development'
    subject = $certificate.Subject
    thumbprint = $certificate.Thumbprint
    valid_from = $certificate.NotBefore.ToUniversalTime().ToString('o')
    valid_until = $certificate.NotAfter.ToUniversalTime().ToString('o')
    public_certificate = 'UniversalDownloader-development.cer'
    timestamped = $false
} | ConvertTo-Json | Set-Content -LiteralPath $infoPath -Encoding utf8

foreach ($target in $FilePath) {
    $resolvedPath = (Resolve-Path -LiteralPath $target).Path
    & $SignToolPath sign /fd SHA256 /s My /sha1 $certificate.Thumbprint $resolvedPath
    if ($LASTEXITCODE -ne 0) { throw "Signing failed: $resolvedPath" }
    $signature = Get-AuthenticodeSignature -LiteralPath $resolvedPath
    $verificationResult = [UniversalDownloader.SignatureVerifier]::Verify($resolvedPath)
    $verificationHex = $verificationResult.ToString('X8')
    if ($signature.SignerCertificate.Thumbprint -ne $certificate.Thumbprint -or
        $verificationHex -notin @('00000000', '800B0109')) {
        throw "Unexpected signature result: $($signature.Status), WinVerifyTrust 0x$verificationHex"
    }
    Write-Output "Signed: $resolvedPath; Windows trust status: $($signature.Status), WinVerifyTrust 0x$verificationHex"
}

Write-Output 'Self-signed development certificate. SmartScreen warnings may remain.'
