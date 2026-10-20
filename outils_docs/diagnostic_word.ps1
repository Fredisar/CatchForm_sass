# Diagnostic : lance Word VISIBLE, tente un enregistrement, et capture l'ecran pendant le blocage.
Add-Type -AssemblyName System.Windows.Forms, System.Drawing

$out  = Join-Path $env:TEMP "test_word_save.docx"
$shot = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "capture_word.png"

# L'enregistrement est lance dans un job separe pour pouvoir capturer l'ecran pendant qu'il bloque.
$job = Start-Job -ScriptBlock {
    param($out)
    $word = New-Object -ComObject Word.Application
    $word.Visible = $true
    $doc = $word.Documents.Add()
    $doc.Range().Text = "Test CatchForm : enregistrement automatique"
    $doc.SaveAs2($out, 16)
    $doc.Close(0)
    if ($word.Documents.Count -eq 0) { $word.Quit() }
    "ENREGISTRE"
} -ArgumentList $out

Start-Sleep -Seconds 25
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$bmp.Save($shot, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()

"Etat du job : $($job.State)"
Receive-Job $job -ErrorAction SilentlyContinue
"Capture : $shot"
