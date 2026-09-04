param([string]$TemplateDirectory = (Join-Path $PSScriptRoot '../storage/templates'))
$ErrorActionPreference = 'Stop'
$templateRoot = (Resolve-Path -LiteralPath $TemplateDirectory).Path
$names = @('원본데이터 명세서', '합성데이터 명세서', '측정결과서')
$hwp = New-Object -ComObject HWPFrame.HwpObject
try {
    $hwp.XHwpWindows.Item(0).Visible = $false
    foreach ($name in $names) {
        $source = Join-Path $templateRoot ($name + '.hwp')
        $target = Join-Path $templateRoot ($name + '.hwpx')
        Write-Output "Opening: $source"
        if (-not $hwp.Open($source, 'HWP', '')) { throw "Failed to open $source" }
        if (-not $hwp.SaveAs($target, 'HWPX', '')) { throw "Failed to save $target" }
        Write-Output "Saved: $target"
        $hwp.Clear(1)
    }
} finally {
    $hwp.Quit()
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($hwp)
}
