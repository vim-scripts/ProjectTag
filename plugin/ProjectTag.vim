" File: plugin/ProjectTag.vim
" Version: 0.1.3
" GetLatestVimScripts: 3219 1 :AutoInstall: ProjectTag.zip
" check doc/ProjectTag.txt for more version information

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

" this variables is used as a flag showing whether to finish the script, since
" in python code, vim.command('finish') is not allowed
let s:does_finish_flag = 0 

python << EEOOFF

try:
    # import required libraries
    import vim
    import threading
    import sys
    import os

    # add $VIMRUNTIME/ProjectTag to module search directory
    sys.path.append( os.path.abspath( vim.eval('s:py_dir')) )

    import ProjectTag

    # used to restore global variables
    class ProjectTagGlobal:
        # the ctags thread
        tag_thread = None

    # add the tag file
    pc = ProjectTag.ProjectConfig( vim.eval('s:default_project_name') )
    pc.add_tag_file()
    del pc

except ImportError: # if required python packages are not found, then don't generate tags.
    vim.command( '''
    command GenProTags echohl ErrorMsg | echo "Some python packages required by
                \\ ProjectTag are missing on your system. Install these missing packages and
                \\ restart vim to enable this plugin." | echohl None''')

    vim.command( '''
    command GenProTagsBg echohl ErrorMsg | echo "Some python packages required by
                \\ ProjectTag are missing on your system. Install these missing packages and
                \\ restart vim to enable this plugin." | echohl None''')

    vim.command('let s:does_finish_flag = 1') # if need to finish, set s:does_finish to 1

EEOOFF

" if the python code above calls for a finish, then finish
if s:does_finish_flag
    finish
endif

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
