rem lupdate is a command line tool that finds the translatable strings in the specified source, 
rem header and Qt Designer interface files, and produces or updates .ts translation files.
rem Usage:
rem     lupdate [options] [project-file]...
rem     lupdate [options] [source-file|path|@lst-file]... -ts ts-files|@lst-file
rem 
rem lupdate is part of Qt's Linguist tool chain. It extracts translatable
rem messages from Qt UI files, C++, Java and JavaScript/QtScript source code.
rem Extracted messages are stored in textual translation source files (typically
rem Qt TS XML). New and modified messages can be merged into existing TS files.
rem 
rem Options:
rem     -help  Display this information and exit.
rem     -no-obsolete
rem            Drop all obsolete strings.
rem     -extensions <ext>[,<ext>]...
rem            Process files with the given extensions only.
rem            The extension list must be separated with commas, not with whitespace
rem            Default: 'java,jui,ui,c,c++,cc,cpp,cxx,ch,h,h++,hh,hpp,hxx,js,qs,qml'
rem     -pluralonly
rem            Only include plural form messages.
rem     -silent
rem            Do not explain what is being done.
rem     -no-sort
rem            Do not sort contexts in TS files.
rem     -no-recursive
rem            Do not recursively scan the following directories.
rem     -recursive
rem            Recursively scan the following directories (default).
rem     -I <includepath> or -I<includepath>
rem            Additional location to look for include files.
rem            May be specified multiple times.
rem     -locations {absolute|relative|none}
rem            Specify/override how source code references are saved in TS files.
rem            Default is absolute.
rem     -no-ui-lines
rem            Do not record line numbers in references to UI files.
rem     -disable-heuristic {sametext|similartext|number}
rem            Disable the named merge heuristic. Can be specified multiple times.
rem     -pro <filename>
rem            Name of a .pro file. Useful for files with .pro file syntax but
rem            different file suffix. Projects are recursed into and merged.
rem     -source-language <language>[_<region>]
rem            Specify the language of the source strings for new files.
rem            Defaults to POSIX if not specified.
rem     -target-language <language>[_<region>]
rem            Specify the language of the translations for new files.
rem            Guessed from the file name if not specified.
rem     -ts <ts-file>...
rem            Specify the output file(s). This will override the TRANSLATIONS
rem            and nullify the CODECFORTR from possibly specified project files.
rem     -codecfortr <codec>
rem            Specify the codec assumed for tr() calls. Effective only with -ts.
rem     -version
rem            Display the version of lupdate and exit.
rem     @lst-file
rem            Read additional file names (one per line) from lst-file.

rem prima avviare OSGeo4W Shell e da lì:
rem cd "%AppData%\QGIS\QGIS3\profiles\default\python\plugins\qad\i18n"
rem "lupdate drop obsolete"
"C:\Program Files\QGIS 3.22.6\Library\bin\lupdate.exe" -no-obsolete Qad.pro
pause