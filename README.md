# edraw
inkscape extension for creating ely files used for electron beam lithography

This is an inkscape extension for creating .ely files from drawings. It is meant to use for creating electron beam lithography files.

INSTALLATION:
* find the path where inkscape extensions are located. In Inkscape go to  Edit > Preferences > System: User extensions for the getting the path
* copy the the edraw.py and edraw.inx file to your inkscape extension folder. 
* after a restart of inkscape this extension should be visible in the extensions/export menu.

USAGE:
* create some shapes and run the extension
* the units doesn't matter the document units will be interpreted as µm
* choose the path where the .ely file should be stored
* check the output file with another viewer, to make sure the output is that what you want
* if you use a grid make sure the grid units match the document units

ISSUES:
* there are stil a lot of issues. See TODO section in edraw.py for further details
* the program is not fully tested. Be careful
* since I'm not a professional programer the code is not written in a good shape. The program is just a quick approach.
