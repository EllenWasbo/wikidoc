#!/usr/bin/python

##############################################################################
#                                                                            #
# Copyright 2016, John Bieling                                               #
#   modified 2023 by Ellen Wasbo to fix for Python 3         ................#
#                                       + fix page links and images          #
#                                                                            #
# This program is free software; you can redistribute it and/or modify       #
# it under the terms of the GNU General Public License as published by       #
# the Free Software Foundation; either version 2 of the License, or          #
# any later version.                                                         #
#                                                                            #
# This program is distributed in the hope that it will be useful,            #
# but WITHOUT ANY WARRANTY; without even the implied warranty of             #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the              #
# GNU General Public License for more details.                               #
#                                                                            #
# You should have received a copy of the GNU General Public License          #
# along with this program; if not, write to the Free Software                #
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA #
#                                                                            #
##############################################################################

import sys
import os
import time
import subprocess
import re
import os.path

import tkinter as tk
from tkinter import filedialog


def fix_page_links(html_strings, github_img_path=None, local_img_path=None):
    for lineno, line in enumerate(html_strings):
        if 'class="breakbefore"' in line:
            if line[0:3] == '<h1':
                splitline = line.split('>')
                splitline_name = splitline[1].split('<')
                page_name = splitline_name[0]
                page_name = page_name.replace(' ', '-')
                line = f'{splitline[0]} id="{page_name}">{splitline[1]}>'
                html_strings[lineno] = line
        if 'href="' in line:
            splitline = line.split('href="')
            change = False
            for i in range(1, len(splitline)):
                if splitline[i][0] not in ['h', '#', '"']:
                    splitline[i] = '#' + splitline[i]
                    change = True
            if change:
                line = 'href="'.join(splitline)
                html_strings[lineno] = line
        if github_img_path:
            if github_img_path in line:
                line = line.replace(github_img_path, local_img_path)
                line = line.replace("?raw=true", "")
                html_strings[lineno] = line
    return html_strings


def getFilesInDirectory(directory, failOnError=True):
    if os.path.exists(directory):
        return next(os.walk(directory))[2]
    elif not failOnError:
        return False
    else:
        print(f"Folder <{directory}> does not exist. Aborting.")
        sys.exit(0)


def getTitleFromFilename(file):
    base = os.path.splitext(file)[0]
    return base.replace("-", " ")


def substitute(section, filename):
    section = section.replace("###_WIKIDOC_GENDATE_###", time.strftime("%d.%m.%Y"))
    section = section.replace("###_WIKIDOC_TITLE_###", getTitleFromFilename(filename))
    return section


def parseFile(path, file, generateImages, wikidocConfig,
              pathWkhtmltoimage, pathWiki):
    print(f'parseFile {file}')
    html = ""
    # Try to convert the source via pandoc to html, otherwise simply
    # open it and treat as pure html
    try:
        html = subprocess.check_output(
            "pandoc --ascii --extract-media=downloaded_imgs -r gfm --mathjax " + path + file, shell=True)
    except subprocess.CalledProcessError:
        print(
            f"Could not convert {file} with pandoc from github markdown to html, trying to open it as plain html.")
        with open(path + file, "r") as myfile:
            html = myfile.read()

    if len(html) == 0:
        print(f"Could not read {file}.")
        return ""

    html = html.decode('UTF-8')

    # define search strings
    startstring = '<!-- WIKIDOC PDFONLY' #bytes('<!-- WIKIDOC PDFONLY', 'UTF-8')
    endstring = 'WIKIDOC PDFONLY -->' #bytes('WIKIDOC PDFONLY -->', 'UTF-8')

    # reverse loop through all PDFONLY sections
    start = html.rfind(startstring)
    end = html.rfind(endstring) + len(endstring)
    while not start == -1 and not end == -1 and start < end:
        # get arary of lines of section - first and last line is to be dropped
        sectionlines = html[start:end].splitlines()

        # get name of section (if any) from first line
        #name = (sectionlines[0].replace(startstring, bytes('', 'UTF-8'))).strip()
        name = (sectionlines[0].replace(startstring, "")).strip()

        # get section without enclosing html comment tags
        section = substitute("\n".join(sectionlines[1:-1]), file).strip()

        # generate images from PDFONLY segments
        if (generateImages and name):
            with open("wikidoc_image.html", "w") as image_file:
                image_file.write(wikidocConfig["HEAD"] + "\n" + section + "\n" + wikidocConfig["FOOT"])

            # Convert HTML to IMAGE
            print(f" -> Converting PDFONLY section < {name} > to PNG.")
            cmd = pathWkhtmltoimage + " --width 700 wikidoc_image.html " + pathWiki + "generated-images/" + name + ".PNG"
            try:
                subprocess.call(cmd, shell=True)
            except OSError:
                print("Something went wrong converting PDFONLY section to PNG.")

            # Delete temp file
            os.unlink("wikidoc_image.html")

        # replace section by modified section
        html = html[:start] + section + html[end:]
        start = html.rfind(startstring)
        end = html.rfind(endstring) + len(endstring)

    return substitute(html, file)


def extractStartStop(startString, endString, filestr):
    start = filestr.find(startString)
    end = filestr.find(endString)
    if start == -1 or end == -1 or start > end:
        return ""

    return filestr[start + len(startString):end].strip('\n\r ')


def readGlobalWikidocComments(file):
    wikidocConfig = {}
    wkhtmltopdfConfig = []

    try:
        with open(file, "r") as myfile:
            filecontent = myfile.read()
            wikidocConfig["HEAD"] = extractStartStop("<!-- WIKIDOC HTMLHEAD", "WIKIDOC HTMLHEAD -->", filecontent)
            wikidocConfig["FOOT"] = extractStartStop("<!-- WIKIDOC HTMLFOOT", "WIKIDOC HTMLFOOT -->", filecontent)
            if (not wikidocConfig["HEAD"] or not wikidocConfig["FOOT"]):
                print("Could not find HTMLHEAD and/or HTMLFOOT comment in home.md. Aborting.\n")
                exit()

            wikidocConfig["COVER"] = extractStartStop("<!-- WIKIDOC COVER", "WIKIDOC COVER -->", filecontent)
            wikidocConfig["COVER"] = substitute(wikidocConfig["COVER"], "Cover.md")

            wikidocConfig["TOCXSL"] = extractStartStop("<!-- WIKIDOC TOCXSL", "WIKIDOC TOCXSL -->", filecontent)

            parameters = extractStartStop("<!-- WIKIDOC CONFIG", "WIKIDOC CONFIG -->", filecontent).splitlines()
            for line in parameters:
                stripline = line.strip()
                if stripline.startswith("--filename "):
                    wikidocConfig["filename"] = stripline.replace("--filename ", "").strip()
                else:
                    wkhtmltopdfConfig.append(stripline)

            if not "filename" in wikidocConfig:
                wikidocConfig["filename"] = "wikidoc.pdf"
            wkhtmltopdfConfig.append("--enable-local-file-access ")
            return (wikidocConfig, wkhtmltopdfConfig)

    except:
        print(f"Could not read file {file} or did not find required wikidoc comments!\n")
        exit()


def convert_md_to_pdf(pathWkhtmltopdf, pathWiki, github_img_path, local_img_path):

    generateImages = True

    # Check if wkhtmltoimage is present
    pathWkhtmltoimage = os.path.dirname(pathWkhtmltopdf) + os.sep + "wkhtmltoimage"

    # In order to handle windows-executables also check for exe files
    if (not os.path.isfile(pathWkhtmltoimage)):
        pathWkhtmltoimage = pathWkhtmltoimage + ".exe"

    if (not os.path.isfile(pathWkhtmltoimage)):
        print("PDFONLY segements will not be saved as images, because 'wkhtmltoimage'")
        print("is not found next to wkhtmltopdf.\n")
        generateImages = False

    # Check, if generated-images folder exists in pathWiki
    if (generateImages and not os.path.isdir(pathWiki + "generated-images")):
        print("PDFONLY segements will not be saved as images, because 'generated-images'")
        print("folder not found in wiki repository.\n")
        generateImages = False

    # Home.md must be present and it must contain special comments with additional
    # informations
    (wikidocConfig, wkhtmltopdfConfig) = readGlobalWikidocComments(pathWiki + "Home.md")

    # Build html, start with global head
    html = list()
    html.append(wikidocConfig["HEAD"])

    # Append Home.md
    html.append(parseFile(pathWiki, "Home.md", generateImages, wikidocConfig, 
                          pathWkhtmltoimage, pathWiki))

    if os.path.exists(pathWiki + '_Sidebar.md'):
        print('Using _Sidebar.md for ordering of md-files')
        # Read entries in sidebar file to determine the ordering of chapters for the compiled 
        # pdf-document
        with open(pathWiki + '_Sidebar.md', 'r') as myfile:
            sidebarContent = myfile.read().replace('\n', '')

        sidebarEntries = re.findall("((.*?))", sidebarContent)

        # make a list of the markdown-files referenced from the sidebar
        files = []
        for entry in sidebarEntries:
            filename = entry

            if not entry.lower().endswith(".md"):
                filename = filename + ".md"

            # Only append to the list of files if a corresponding file exists
            if os.path.exists(pathWiki + filename):
                files.append(filename)
            else:
                print("Ignoring _Sidebar.md-entry \"" + entry + "\"")
    else:
        print('Using alphabetical ordering of md-files')
        files = sorted(getFilesInDirectory(pathWiki), key=lambda s: s.lower())

    # Append all other files to the document except Home.md
    for file in files:
        if file.endswith(".md") and not file == "Home.md" and not file == "_Sidebar.md":
            html.append(parseFile(pathWiki, file,
                                  generateImages, wikidocConfig,
                                  pathWkhtmltoimage, pathWiki))

    # Append global foot
    html.append(wikidocConfig["FOOT"])

    tempfiles = dict()
    keepfiles = dict()

    # Write html into temp file
    keepfiles["main"] = "wikidoc.html"
    with open(keepfiles["main"], "w") as html_file:
        html_file.write("\n".join(html))

    # Write cover into temp file - if present
    if "COVER" in wikidocConfig:
        tempfiles["cover"] = "wikidoc_cover.html"
        fix_cover = fix_page_links(
            wikidocConfig["COVER"].split("/n"),
            github_img_path, local_img_path)
        wikidocConfig["COVER"] = "\n".join(fix_cover)
        with open(tempfiles["cover"], "w") as cover_file:
            cover_file.write(
                wikidocConfig["HEAD"] + "\n"
                + wikidocConfig["COVER"] + "\n"
                + wikidocConfig["FOOT"]
                )

    # Write tocxsl into temp file - if present
    if "TOCXSL" in wikidocConfig:
        tempfiles["toc"] = "wikidoc_toc.xsl"
        with open(tempfiles["toc"], "w") as toc_file:
            toc_file.write(wikidocConfig["TOCXSL"])

    # Build cmd for wkhtmltopdf
    cmd = pathWkhtmltopdf + " " + " ".join(wkhtmltopdfConfig) + " "
    if "cover" in tempfiles:
        cmd = cmd + "cover " + tempfiles["cover"] + " "
    if "toc" in tempfiles:
        cmd = cmd + "toc --xsl-style-sheet " + tempfiles["toc"] + " "
    cmd = cmd + keepfiles["main"] + " " + pathWiki + wikidocConfig["filename"]

    # add relative links to pages
    html_strings = ''
    with open("wikidoc.html", "r") as html_file:
        html = html_file.read()
        html_strings = fix_page_links(
            html.split("\n"), github_img_path, local_img_path)
    with open("wikidoc.html", "w") as html_file:
        html_file.write("\n".join(html_strings))

    # Convert HTML to PDF
    try:
        subprocess.call(cmd, shell=True)
    except OSError:
        print("Something went wrong calling " + pathWkhtmltopdf + " on " + wikidocConfig["filename"] + ".html")

    # Delete all created temp files
    for tempfile in tempfiles.values():
        if (os.path.isfile(tempfile)):
            os.unlink(tempfile)

    exit()

##############################################################################
### Main #####################################################################
##############################################################################
input_path_wk = ''
input_path_wiki = ''
input_url = ''
input_path_images = ''

try:
    input_path_wk = sys.argv[1]
except IndexError:
    pass
try:
    input_path_wiki = sys.argv[2]
except IndexError:
    pass
try:
    input_url = sys.argv[3]
except IndexError:
    pass
try:
    input_path_images = sys.argv[4]
except IndexError:
    pass

master = tk.Tk()
master.title('Convert Github Wiki to pdf manual')

def set_wk_path():
    dirpath = filedialog.askopenfilename(
        title="Select file wkhtmltopdf.exe")
    if dirpath:
        path_wk = dirpath.replace("/", os.sep)
        entry_wk.delete(0, tk.END)
        entry_wk.insert(0, path_wk)

def set_wiki_path():
    dirpath = filedialog.askdirectory(
        title="Select local path with your cloned Wiki directory")
    if dirpath:
        path_wiki = dirpath.replace("/", os.sep) + os.sep
        entry_wiki_path.delete(0, tk.END)
        entry_wiki_path.insert(0, path_wiki)

def set_image_path():
    dirpath = filedialog.askdirectory(
        title="Select local path to images")
    if dirpath:
        path_images = dirpath.replace("/", os.sep) + os.sep
        entry_image_path.delete(0, tk.END)
        entry_image_path.insert(0, path_images)

def exit_app():
    exit()

def proceed_to_convert():
    # because windows does not handle POSIX paths for calls to exe-files, we replace / with \
    # this way passing a relative path in POSIX-style is still possible
    pathWkhtmltopdf = entry_wk.get().replace("/", os.sep)
    path_wiki = entry_wiki_path.get().replace("/", os.sep)
    if path_wiki:
        path_url = entry_url.get()
        if path_url:
            if path_url[-1] != '/':
                path_url = path_url + '/'
        path_images = 'file:///' + entry_image_path.get().replace('\\', '/')
        if path_images:
            if path_images[-1] != '/':
                path_images = path_images + '/'
        convert_md_to_pdf(pathWkhtmltopdf, path_wiki, path_url, path_images)

tk.Label(master, text='Path to wkhtmltopdf.exe').grid(row=0, column=0)
entry_wk = tk.Entry(master, width=100)
entry_wk.grid(row=0, column=1)
entry_wk.insert(0, input_path_wk)
btn_wk = tk.Button(master, text='Browse...', command=set_wk_path)
btn_wk.grid(row=0, column=2, sticky='W', padx=10)

tk.Label(master,
      text='Make sure to clone your GitHub Wiki to access the .md files').grid(
          columnspan=3, row=1, pady=10)
tk.Label(master, text='Local path to Wiki files').grid(row=2, column=0)
entry_wiki_path = tk.Entry(master, width=100)
entry_wiki_path.grid(row=2, column=1)
entry_wiki_path.insert(0, input_path_wiki)
btn_wiki_path = tk.Button(master, text='Browse...', command=set_wiki_path)
btn_wiki_path.grid(row=2, column=2, sticky='W', padx=10)
tk.Label(master,
      text=('Replacing image paths from github path to local path to avoid '
            'issues with too slow downloads. (Optional)')
      ).grid(columnspan=3, row=3, pady=10)
tk.Label(master, text='URL part to be replaced').grid(row=4)
tk.Label(master, text="Replace with local folder path (file: ///...)").grid(
    row=5, padx=10)
entry_url = tk.Entry(master, width=100)
entry_image_path = tk.Entry(master, width=100)
entry_url.grid(row=4, column=1)
entry_url.insert(0, input_url)
entry_image_path.grid(row=5, column=1)
entry_image_path.insert(0, input_path_images)
btn_image_path = tk.Button(master, text='Browse...', command=set_image_path)
btn_image_path.grid(row=5, column=2, sticky='W', padx=10)

btn_proceed = tk.Button(
    master, text='Proceed to convert .md files to .pdf',
    command=proceed_to_convert)
btn_proceed.grid(row=6, column=1, padx=10, pady=30)

master.mainloop()
