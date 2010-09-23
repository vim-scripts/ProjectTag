# File: ProjectTag/ProjectTag.py
# Version: 0.1.5

import sys
import re
import os
import ConfigParser
import subprocess
import tempfile
import shutil
import vim


# search for the file from current directory to upper dir until meet the root directory,
# return the file's absolute path if found, or return None if not found
def search_for_file_upper( cur_dir, file_name ):

    cur_dir_local = os.path.abspath( cur_dir )
    
    while True:
        cur_check = cur_dir_local + os.path.sep + file_name
        if os.path.isfile( cur_check ): # if cur path meets the condition, then return the path
            return cur_check

        # if condition does not meet, go upper
        upper_cur_dir_local = os.path.dirname( cur_dir_local )
        if upper_cur_dir_local == cur_dir_local: # if this is the root directory
            return None

        cur_dir_local = upper_cur_dir_local



# get include files (#include <somefile> or #include "somefile")
# from a list of file lines
def get_included_files( filelines ): 

    ret = set()

    rematch = re.compile( r'#include[ \t]*[<"][^<>"]+[>"]' )
    refind = re.compile( r'(?<=[<"])[^<>"]+(?=[>"])' )

    for line in filelines:
        trimmed_line = line.strip()
        rem = rematch.match( trimmed_line )

        if rem == None:
            continue

        rem = refind.search( trimmed_line );
        if rem == None:
            continue

        ret.add( rem.group( 0 ) )

    return ret

# get the included file of a c/c++ source file and it's included file(internal use)
def __get_included_files_reclusively( src, include_dirs, checked_files ):
    # if current file has been checked, return an empty set
    if src in checked_files:
        return set()
    
    # set current file as checked
    checked_files.add( src )

    try:
        f = open( src,'r' )
    except IOError, message:
        print >> sys.stderr, "can not open file "+src, message
        return set()

    ret = set()

    # get the included file paths
    header_files = get_included_files( f.readlines() )

    # add the directory where the source file locates to include directory list
    include_dirs2 = include_dirs[:]
    include_dirs2.append( os.path.dirname( src ) )
    for include_dir in include_dirs2:
        for header_file in header_files:

            file_path = include_dir + os.path.sep + header_file # the path of new file

            # make the file path seperator be consitent with the os'
            if os.path.sep == '/':
                file_path = file_path.replace( '\\','/' )
            else:
                file_path = file_path.replace( '/','\\' )

            # if the file exists, then add this file to ret
            if os.path.isfile( file_path ) :
                ret.add( file_path )
                ret |= __get_included_files_reclusively( file_path, include_dirs, checked_files )

    return ret

# get the included file of a c/c++ source file and it's included file
def get_included_files_reclusively( src, include_dirs ):
    return __get_included_files_reclusively( src, include_dirs, set() )



# generate tags from file_set, write the result to outfile
# params: 
# file_set: file to generate tags for
# outfile: the output file
# tag_prog_cmd: command to call the tag program, such as /usr/bin/ctags, etc
# flags: tag generation flags
def generate_tags_ctags( file_set, outfile, flags, tag_prog_cmd='ctags' ):
    # append every file to the outfile
    sp = subprocess.Popen( tag_prog_cmd + ' -L - ' + flags + ' -f '+ outfile, shell=True, stdin=subprocess.PIPE )

    file_list = ''
    for fi in file_set:
        file_list += fi
        file_list += '\n'

    sp.communicate( input = file_list )

    return

# the config parser for project ini file
class ProjectConfig( ConfigParser.ConfigParser ):
    # init, the argument project_file_name is the name of project file, not the full path. the function will
    # search upper to find this file

    # the directory where the project file locates
    project_dir = None

    def does_config_file_exist( self ):
        return self.project_dir != None

    def __init__( self, project_file_name ):

        ConfigParser.ConfigParser.__init__( self )

        project_file_path = search_for_file_upper( vim.eval( "expand('%:p:h')" ), project_file_name )
        if project_file_path == None:
            return

        self.project_dir = os.path.dirname( project_file_path )

        self.read( project_file_path )
        self.set_project_config_parser_default_value()


    # generate tags
    def generate_tags( self ):

        # do nothing if config file does not exist
        if not self.does_config_file_exist():
            return

        tagoutput = self.get( 'general', 'tagoutput' )
        tagoutput = self.project_dir + os.path.sep + tagoutput
        tagflag = self.get( 'general', 'tagflag' )
        tagprog = self.get( 'general', 'tagprog' )
        temp_tagoutput = tagoutput + '.tmp'
        file_set = self.get_files_to_tag()
        generate_tags_ctags( file_set, temp_tagoutput, tagflag, tagprog )
        
        if os.path.isfile( tagoutput ):
            try:
                os.remove( tagoutput )
            except OSError, message:
                print >> sys.stderr, 'Can not delete '+tagoutput, message
                return False

        shutil.move( temp_tagoutput, tagoutput )

        return True
        

    # set the option to default value if the user does not set it
    def __set_option_if_not_have( self, section, option, defaultval ):
        if not self.has_section( section ):
            self.add_section( section )

        if not self.has_option( section, option ):
            self.set( section, option, defaultval )

        return

    # find the tags output file and add it to tags
    def add_tag_file( self ):
        # do nothing if config file does not exist
        if not self.does_config_file_exist():
            return

        tagoutput = self.get( 'general', 'tagoutput' ).strip()
        tag_path = self.project_dir + os.path.sep + tagoutput
        vim.command( 'setlocal tags+='+tag_path )


    def set_project_config_parser_default_value( self ):
        self.__set_option_if_not_have( 'general','include_dirs','' )
        self.__set_option_if_not_have( 'general','sources','' )
        self.__set_option_if_not_have( 'general','tagprog','ctags' )
        self.__set_option_if_not_have( 'general','tagflag','--c-kinds=+px --c++-kinds=+px' )
        self.__set_option_if_not_have( 'general','tagoutput','tags.prom' )
        
    # return a list of files to tag
    def get_files_to_tag( self ):

        # do nothing if config file does not exist
        if not self.does_config_file_exist():
            return

        sources = [s.strip() for s in self.get( 'general','sources' ).split( ',' )]
        include_dirs = [s.strip() for s in self.get( 'general','include_dirs' ).split( ',' )]
        ret = set()

        # the full path of sources
        sources_full_path = [ self.project_dir + os.path.sep + s for s in sources ]

        # first add the sources
        ret |= set( sources_full_path )

        # now it's time to get the path of all included headers
        for src in sources_full_path:
            # if it's not a C/C++ source file, then skip
            if re.match( r'.*\.(c|C|cpp|cxx|cc|c\+\+)', src ) == None:
                continue

            ret |= get_included_files_reclusively( src, include_dirs )

        return ret
