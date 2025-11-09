# wikidoc
Modified https://github.com/jobisoft/wikidoc to python 3 and adjustments to create pdf manuals for my own applications using images in a separate repository

Prepare your Github wiki from which a .pdf should be generated
- at start of first page (Home) add code in cover.txt
- Customize cover page title and image of the pasted content from cover.txt in section `WIKIDOC COVER`
- at start of the remaining pages, add this code (remove class="breakbefore" if pagebreak is not desired):
```
<!-- WIKIDOC PDFONLY
<h1 class="breakbefore">###_WIKIDOC_TITLE_###</h1>
WIKIDOC PDFONLY -->
```
- clone your Github wiki to your computer

Requirements before running wikidoc:
- install [pandoc](https://pandoc.org/installing.html)
- install [wkhtmltopdf](https://wkhtmltopdf.org/)

Prepare images:
- To prepare images both for the Wiki and the pdf, you may create a repository holding the images
- Clone the image repository to your computer

To run wikidoc using python 3:
```
python wikidoc.py <path to wkhtmltopdf.exe> <path to local cloned wiki> <url to images for wiki> <local path to images for wiki>
```
example:
```
python wikidoc.py C:\Programfiles\wkhtmltopdf\bin\wkhtmltopdf.exe C:\Users\ellen\Documents\GitHub\imageQCpy_wiki\ https://github.com/EllenWasbo/wiki_images/blob/main/ C:\Users\ellen\Documents\GitHub\wiki_images
```
A dialog will open with the paths set as indicated (if indicated). Press "Proceed to convert .md files to .pdf"


Tip:
To force pagebreaks, add this code to your Wiki files:
```
<!-- WIKIDOC PDFONLY
<div class="breakbefore"> </div>
WIKIDOC PDFONLY -->
```
