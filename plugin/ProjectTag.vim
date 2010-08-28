" File: plugin/ProjectTag.vim
" Version: 0.1.2
" check doc/ProjectTag.txt for more version information
" GetLatestVimScripts: 3219 1 :AutoInstall: ProjectTag.zip

if v:version < 700
    finish
endif

if !has('python')
    finish
endif

" check whether this script is already loaded
if exists("g:loaded_ProjectTag")
    finish
endif
let g:loaded_ProjectTag = 1

let s:saved_cpo = &cpo
set cpo&vim

" initialization {{{1
let s:py_dir = substitute(findfile('ProjectTag/ProjectTag.py', &rtp), '/ProjectTag.py', '', '')

let s:default_project_name = 'project.prom'

python << EEOOFF

import sys
import vim
import os

# add $VIMRUNTIME/ProjectTag to module search directory
sys.path.append( os.path.abspath( vim.eval('s:py_dir')) )

# import required libraries
import ProjectTag
import threading

# used to restore global varibles
class ProjectTagGlobal:
    # the ctags thread
    tag_thread = None

# add the ctag file
pc = ProjectTag.ProjectConfig( vim.eval('s:default_project_name') )
pc.add_tag_file()
del pc

EEOOFF

" autocmd {{{1
" automatically add the tags file when entering a buffer
autocmd BufEnter * python ProjectTag.ProjectConfig( vim.eval('s:default_project_name') ).add_tag_file()

" functions {{{1

" generate tags
function s:GenerateProjectTags( back_ground )

python << EEOOFF
pc = ProjectTag.ProjectConfig( vim.eval('s:default_project_name') )

# if the config file does not exist, return immediately
if not pc.does_config_file_exist():
    vim.command('echohl ErrorMsg | echo "project file not found!" | echohl None')
    vim.command('return')

if ProjectTagGlobal.tag_thread != None and ProjectTagGlobal.tag_thread.isAlive():
    vim.command('return')

ProjectTagGlobal.tag_thread = threading.Thread( target=ProjectTag.ProjectConfig.generate_tags, args=(pc,) )
ProjectTagGlobal.tag_thread.daemon = True
ProjectTagGlobal.tag_thread.start()

EEOOFF
    
    " if run foreground
    if a:back_ground == 0

python << EEOOFF

ProjectTagGlobal.tag_thread.join()

EEOOFF

    endif

python << EEOOFF

# after generating the tag, add the tag file to tags
pc.add_tag_file()

EEOOFF

endfunction


" commands {{{1
command GenProTags call s:GenerateProjectTags(0)
command GenProTagsBg call s:GenerateProjectTags(1)

" }}}


let &cpo = s:saved_cpo

" vim: fdm=marker
