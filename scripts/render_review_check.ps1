param([string]$InputDirectory = (Join-Path $PSScriptRoot '../storage/outputs/review-example'),
      [string]$OutputDirectory = (Join-Path $PSScriptRoot '../storage/temp/review-layout'))
$ErrorActionPreference = 'Stop'
$inputRoot = (Resolve-Path -LiteralPath $InputDirectory).Path
[void](New-Item -ItemType Directory -Force -Path $OutputDirectory)
$outputRoot = (Resolve-Path -LiteralPath $OutputDirectory).Path
$hwp = New-Object -ComObject HWPFrame.HwpObject
try {
    $hwp.XHwpWindows.Item(0).Visible = $false
    foreach ($file in (Get-ChildItem -LiteralPath $inputRoot -Filter '*.hwpx')) {
        Write-Output "Opening: $($file.Name)"
        if (-not $hwp.Open($file.FullName, 'HWPX', '')) { throw "Failed to open $($file.Name)" }
        $target = Join-Path $outputRoot ($file.BaseName + '.pdf')
        if (-not $hwp.SaveAs($target, 'PDF', '')) { throw "Failed to render $target" }
        Write-Output "Rendered: $target"
        $hwp.Clear(1)
    }
} finally {
    $hwp.Quit()
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($hwp)
}
