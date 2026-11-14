# .latexmkrc -- Konfigurasi latexmk untuk VS Code (LaTeX Workshop) & CLI
# Dibaca otomatis ketika latexmk dijalankan dari ipb-thesis-latex/.

ensure_path('TEXINPUTS', './src/config//', './config//', './src//', './/', '..//');
ensure_path('BIBINPUTS', './/', '..//', './src//', './src/refs//');
ensure_path('BSTINPUTS', './src/config//', './config//', './src//', './/');

# Gunakan LuaLaTeX (sesuai PPTA IPB 2026 agar Times New Roman asli dipakai),
# termasuk ketika VS Code LaTeX Workshop memanggil latexmk dengan flag -pdf.
$pdf_mode = 4;
$pdflatex = 'lualatex -file-line-error -interaction=nonstopmode -synctex=1 %O %S';
$lualatex = 'lualatex -file-line-error -interaction=nonstopmode -synctex=1 %O %S';
$biber    = 'biber %O %B';
