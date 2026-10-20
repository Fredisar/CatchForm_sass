# Convertit cahier_source.html en vrai .docx avec Microsoft Word, puis exporte un PDF de controle.
# Usage : powershell -NoProfile -ExecutionPolicy Bypass -File convertir_word.ps1
#
# Sur ce poste, Word pilote directement par le script bloque a l'enregistrement.
# Le travail est donc fait dans un processus separe (Start-Job), avec Word visible mais reduit,
# conditions dans lesquelles l'enregistrement fonctionne.
$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$src  = Join-Path $here "cahier_source.html"
$dst  = Join-Path (Split-Path -Parent $here) "catchform\docs\CatchForm_Cahier_des_charges.docx"
$pdf  = Join-Path $here "apercu_cahier.pdf"
$log  = Join-Path $here "convertir_word.log"
Set-Content -Path $log -Value "Debut $(Get-Date -Format HH:mm:ss)"

$job = Start-Job -ArgumentList $src, $dst, $pdf, $log -ScriptBlock {
    param($src, $dst, $pdf, $log)
    $ErrorActionPreference = "Stop"

    function Log($message) { Add-Content -Path $log -Value "$(Get-Date -Format HH:mm:ss) $message" }

    function Add-TextAtEnd($hf, $text) {
        $r = $hf.Range
        $r.MoveEnd(1, -1) | Out-Null
        $r.Collapse(0)
        $r.InsertAfter($text)
    }

    function Add-FieldAtEnd($hf, $fieldType) {
        $r = $hf.Range
        $r.MoveEnd(1, -1) | Out-Null
        $r.Collapse(0)
        $r.Fields.Add($r, $fieldType) | Out-Null
    }

    $dot  = [char]0x00B7   # point median
    $dash = [char]0x2014   # tiret cadratin
    $gray = 9139300        # #64748B au format BGR de Word

    $word = New-Object -ComObject Word.Application
    $word.Visible = $true
    try { $word.WindowState = 2 } catch { }
    Log "Word demarre"
    $doc = $null
    try {
        $doc = $word.Documents.Open($src, $false, $true, $false)
        try { $doc.ActiveWindow.View.Type = 3 } catch { }   # mode Page
        Log "Document ouvert"

        # Format A4, marges de 2 cm, premiere page sans en-tete ni pied de page.
        $ps = $doc.PageSetup
        $ps.PageWidth = 595.3
        $ps.PageHeight = 841.9
        $ps.TopMargin = 56.7
        $ps.BottomMargin = 56.7
        $ps.LeftMargin = 56.7
        $ps.RightMargin = 56.7
        $ps.HeaderDistance = 28.35
        $ps.FooterDistance = 28.35
        $ps.DifferentFirstPageHeaderFooter = -1
        Log "Mise en page appliquee"

        $section = $doc.Sections.Item(1)

        # En-tete : titre du document, aligne a droite, filet bas.
        $header = $section.Headers.Item(1)
        $header.Range.Text = "CatchForm $dot Cahier des charges $dot version 1.1"
        $header.Range.Font.Name = "Calibri"
        $header.Range.Font.Size = 8
        $header.Range.Font.Color = $gray
        $header.Range.ParagraphFormat.Alignment = 2
        $header.Range.ParagraphFormat.Borders.Item(-3).LineStyle = 1

        # Pied de page : "Document interne - Page X sur Y".
        $footer = $section.Footers.Item(1)
        $footer.Range.Text = "Document interne $dash Page "
        Add-FieldAtEnd $footer 33          # PAGE
        Add-TextAtEnd  $footer " sur "
        Add-FieldAtEnd $footer 26          # NUMPAGES
        $footer.Range.Font.Name = "Calibri"
        $footer.Range.Font.Size = 8
        $footer.Range.Font.Color = $gray
        $footer.Range.ParagraphFormat.Alignment = 1
        Log "En-tete et pied de page ajoutes"

        # Sommaire automatique (titres de niveaux 1 et 2) a l'emplacement du repere.
        $range = $doc.Content
        if ($range.Find.Execute("[[SOMMAIRE]]")) {
            $range.Text = ""
            $doc.TablesOfContents.Add($range, $true, 1, 2) | Out-Null
        } else {
            Log "ATTENTION : repere [[SOMMAIRE]] introuvable"
        }

        # Sommaire en Calibri, comme le reste du document (styles integres TOC 1 et TOC 2).
        foreach ($tocStyle in -20, -21) { $doc.Styles.Item($tocStyle).Font.Name = "Calibri" }

        # Ligne d'en-tete repetee en haut de page quand un tableau est coupe.
        $accent = 15025743   # #4F46E5 au format BGR de Word
        $repeated = 0
        foreach ($t in $doc.Tables) {
            try {
                if ($t.Rows.Count -gt 2 -and $t.Cell(1, 1).Shading.BackgroundPatternColor -eq $accent) {
                    $t.Rows.Item(1).HeadingFormat = -1
                    $repeated++
                }
            } catch { }
        }
        Log "Tableaux avec en-tete repete : $repeated"

        $doc.Fields.Update() | Out-Null
        if ($doc.TablesOfContents.Count -gt 0) { $doc.TablesOfContents.Item(1).Update() }
        Log "Sommaire et champs mis a jour"

        $doc.SaveAs2($dst, 16)                   # .docx
        Log "DOCX enregistre"
        $doc.ExportAsFixedFormat($pdf, 17)       # PDF de controle
        Log "PDF exporte"
        Log ("Pages : " + $doc.ComputeStatistics(2))
        if ($doc.TablesOfContents.Count -gt 0) {
            Log ("Lignes du sommaire : " + $doc.TablesOfContents.Item(1).Range.Paragraphs.Count)
        }
    }
    catch {
        Log ("ERREUR : " + $_.Exception.Message)
    }
    finally {
        if ($doc -ne $null) { $doc.Close(0) }
        # Ne ferme Word que si aucun autre document n'y est ouvert.
        if ($word.Documents.Count -eq 0) { $word.Quit() }
        Log "Fin"
    }
}

if (-not (Wait-Job $job -Timeout 300)) {
    Add-Content -Path $log -Value "$(Get-Date -Format HH:mm:ss) DELAI DEPASSE (5 min)"
}
Receive-Job $job -ErrorAction SilentlyContinue
Get-Content $log
