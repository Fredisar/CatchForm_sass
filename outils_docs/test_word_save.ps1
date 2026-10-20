# Test minimal : Word peut-il enregistrer un document en automatisation ?
$log = Join-Path $env:TEMP "test_word_save.log"
Set-Content $log "Debut $(Get-Date -Format HH:mm:ss)"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
Add-Content $log "$(Get-Date -Format HH:mm:ss) Word demarre"
$doc = $word.Documents.Add()
$doc.Range().Text = "Test"
Add-Content $log "$(Get-Date -Format HH:mm:ss) Document cree"
$out = Join-Path $env:TEMP "test_word_save.docx"
$doc.SaveAs2($out, 16)
Add-Content $log "$(Get-Date -Format HH:mm:ss) Enregistre"
$doc.Close(0)
if ($word.Documents.Count -eq 0) { $word.Quit() }
Add-Content $log "$(Get-Date -Format HH:mm:ss) Fin"
