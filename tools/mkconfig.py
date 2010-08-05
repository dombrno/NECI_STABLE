#!/usr/bin/python
'''Produce a makefile for compiling the neci source code for a specified target/configuration.

Usage:
    mkconfig.py [options] [configuration_file]

Use the --help option to see more details.

A platform is defined using a simple ini file, consisting of three sections:
main, opt and dbg.  For instance::

    [main]
    cc = gcc
    ld = gcc
    libs = -llapack -lblas

    [opt]
    cflags = -O3

    [dbg]
    cflags = -g

The 'opt' and 'dbg' sections inherit settings from the 'main' section unless
that option is explicitly set, in which case the value in 'main' is overridden.
The settings in 'opt' are used by default; the debug options can be selected by
passing the -g option to mkconfig.py.

Available options for use in the ini file are:

fc [required]
    Set the fortran compiler.
fflags
    Set flags to be passed to the fortran compiler during compilation.
f77flags
    Set flags to be passed to the fortran compiler during compilation of *.F files.
f90flags
    Set flags to be passed to the fortran compiler during compilation of *.F90 files.
cc [required]
    Set the C compiler.
cflags
    Set flags to be passed to the C compiler during compilation.
ccd
    Set the C compiler to be used to generate the dependencies.  The default behaviour
    is to use the compiler defined by cc.  This is useful for compiling in parallel
    if mpicc does not like the flags needed for producing the dependencies.
cpp [required]
    Set the C pre-processor (only used with *.F and *.F90 files, as the
    C compiler handles pre-processing of C source files).
cppdefs
    Set definitions and flags to be used in the C pre-processing step.
    Those for setting the VCS information and memory availability are already
    included.
ld [required]
    Set the linker program.
ldflags
    Set flags to be passed to the linker during linking of the compiled objects.
libs [required]
    Set libraries to be used during the linking step.
module_flag [required]
    Set the flag used by the compiler which is used to specify the directory
    where module (.mod) files are placed when created and where they should be
    searched for.
compiler
    Set the compiler name used by compare_module_files.pl to avoid cascade
    compilation.
max_mem
    The amount of available memory (per core) in MB.  Used for logging purposes.
'''

import ConfigParser
import optparse
import os
import pprint
import sys

#======================================================================

MAKEFILE_TEMPLATE='''# Generated by mkconfig.py.
# Using the %(config)s %(opt_level)s configuration. 

SHELL = /bin/bash # For our sanity!

# Name of this makefile.
my_makefile := $(word $(words $(MAKEFILE_LIST)), $(MAKEFILE_LIST))
# Command used to recursively call *this* makefile.
my_make := $(MAKE) -f $(my_makefile)

#-----
# Compiler configuration

# pre-processing.
CPP = %(cpp)s
CPPFLAGS = -DMAXMEM='$(MAXMEM)' -D_VCS_VER='$(VCS_VERSION)' $(WORKING_DIR_CHANGES) -D_CONFIG='"$(CONFIG).($(OPT))"' -DDSFMT_MEXP=19937 %(cppflags)s
GCPPFLAG = -DHElement_t="real(dp)"
KCPPFLAG = -DHElement_t="complex(dp)"

# use compiler with perl scripts to avoid cascade compilation.
compiler = %(compiler)s

# fortran compiler and flags.
FC = %(fc)s
FFLAGS = %(fflags)s
F77FLAGS = %(f77flags)s
F90FLAGS = %(f90flags)s

# c compiler and flags.
CC = %(cc)s
CFLAGS = %(cflags)s

# Some servers (I'm looking at you, darwin) have a buggy implementation of the
# mpicc wrapper which doesn't like being passed the necessary flags to produce
# C dependencies.  If this is the case, we use the C compiler directly.
CCD = %(ccd)s
ifndef CCD
CCD = $(CC)
endif

# linker, linker flags and libraries.
LD = %(ld)s
LDFLAGS = %(ldflags)s
LIBS = %(libs)s

# For building neci library.
AR = ar
ARFLAGS = -rcs

#-----
# Directory structure and setup

# Config info
CONFIG = %(config)s
OPT = %(opt_level)s

# Directories containing source files (space separated list).
SRC = src src/lib

# Directories in which compiled objects are placed.
DEST = dest/$(CONFIG)/$(OPT)
# REAL (molecular and gamma-point) objects
GDEST = $(DEST)/real
# COMPLEX (k-point) objects
KDEST = $(DEST)/cmplx
# .F90 files produced from .F90.template files.
TDEST = $(DEST)/template

# Directories for dependencies.  It's safer to share them between all
# config directories.
GDEP_DEST = dest/depend/real
KDEP_DEST = dest/depend/cmplx

# Directory for compiled executable.
EXE = bin

# Directory for neci libraries.
LIB = lib

# Directory containing scripts to avoid cascade compilation
TOOLS = tools

# Directories that make searches for pre-requisites in addition to the local directory (./).
# Colon separated list.
# We include $(DEST) in this so we can do pre-processing and compilation in 2 steps.
empty :=
space := $(empty) $(empty) # stupid make language...
VPATH = $(subst $(space),:,$(SRC) $(DEST))

# Create output directories if they don't exist.
DIRS = $(GDEST) $(KDEST) $(TDEST) $(GDEP_DEST) $(KDEP_DEST) $(EXE) $(LIB)
make_dirs := $(foreach outdir, $(DIRS), $(shell test -e $(outdir) || mkdir -p $(outdir)))

#-----
# Executables and libraries.

# Main programs
PROGS = $(addprefix $(EXE)/,neci.x kneci.x)

# Library versions of neci.
CPMDLIBS = $(addprefix $(LIB)/,gneci-cpmd.a kneci-cpmd.a)
VASPLIBS = $(addprefix $(LIB)/,gneci-vasp.a kneci-vasp.a)
NECILIBS = $(CPMDLIBS) $(VASPLIBS)

# Utility programs.
# We assume that the utility program is written in fortran, resides in the
# utils subdirectory with the source filename (e.g.) utils/a.f90, that the
# program name is (e.g.) bin/a.x and that the utility program requires (at
# most) the same libraries as neci.
UTILS = $(addprefix $(EXE)/, TransLz.x BlockFCIMC.x ModelCompFCIQMC.x ModelFCIQMC.x ConvertMolpFCID.x ConvertPOPSFILE.x)
UTILS_C = $(addprefix $(EXE)/, clean_shared_mem.x)

#-----
# VCS info.

# Get the version control id.  Git only.  Outputs a string.
VCS_VERSION := $(shell set -o pipefail && echo -n \\" && ( git log --max-count=1 --pretty=format:%%H || echo -n 'Not under version control.' ) 2> /dev/null | tr -d '\\r\\n'  && echo -n \\")

# Test to see if the working directory contains changes.  Git only.  If the
# working directory contains changes (or is not under version control) then
# the _WORKING_DIR_CHANGES flag is set.
WORKING_DIR_CHANGES := $(shell git diff --quiet --cached -- $(SRCDIRS) && git diff --quiet 2> /dev/null -- $(SRCDIRS) || echo -n "-D_WORKING_DIR_CHANGES")

#-----
# Additional info.

MAXMEM = %(max_mem)i # RAM available, in MB.  Used by the memory logger.

#-----
# Find source files and resultant object files.

# Source extensions.
EXTS = .F90 .F .c .cpp .F90.template

# Source filenames.
find_files = $(wildcard $(1)/*$(2))
FSRCFILES := $(foreach dir,$(SRC),$(call find_files,$(dir),.F))
F90SRCFILES := $(foreach dir,$(SRC),$(call find_files,$(dir),.F90))
F90TMPSRCFILES := $(foreach dir,$(SRC),$(call find_files,$(dir),.F90.template))
cppSRCFILES := $(foreach dir,$(SRC),$(call find_files,$(dir),.cpp))
cSRCFILES := $(foreach dir,$(SRC),$(call find_files,$(dir),.c))
SRCFILES := $(FSRCFILES) $(F90SRCFILES) $(F90TMPSRCFILES) $(cppSRCFILES) $(cSRCFILES)

# Objects (strip path and replace extension of source files with .o).
FOBJ_bare := $(addsuffix .o,$(basename $(notdir $(FSRCFILES))))
F90OBJ_bare := $(addsuffix .o,$(basename $(notdir $(F90SRCFILES))))
F90TMPOBJ_bare := $(addsuffix .o,$(basename $(basename $(notdir $(F90TMPSRCFILES)))))
cppOBJ_bare := $(addsuffix .o,$(basename $(notdir $(cppSRCFILES))))
cOBJ_bare := $(addsuffix .o,$(basename $(notdir $(cSRCFILES))))

# Full path to all objects (gamma-point).
FOBJ := $(addprefix $(GDEST)/, $(FOBJ_bare))
F90OBJ := $(addprefix $(GDEST)/, $(F90OBJ_bare))
F90TMPOBJ := $(addprefix $(GDEST)/, $(F90TMPOBJ_bare))
cppOBJ := $(addprefix $(GDEST)/, $(cppOBJ_bare))
cOBJ := $(addprefix $(GDEST)/, $(cOBJ_bare))
OBJECTS := $(FOBJ) $(F90OBJ) $(F90TMPOBJ) $(cppOBJ) $(cOBJ)

# Similarly for the kpoint objects.
KFOBJ := $(addprefix $(KDEST)/, $(FOBJ_bare))
KF90OBJ := $(addprefix $(KDEST)/, $(F90OBJ_bare))
KF90TMPOBJ := $(addprefix $(KDEST)/, $(F90TMPOBJ_bare))
KcppOBJ := $(addprefix $(KDEST)/, $(cppOBJ_bare))
KcOBJ := $(addprefix $(KDEST)/, $(cOBJ_bare))

# Objects for standalone NECI.
# We don't need libstub.
OBJECTS_NECI := $(filter-out %%libstub.o,$(OBJECTS))
OBJECTS_KNECI := $(addprefix $(KDEST)/,$(notdir $(OBJECTS_NECI)))

# Objects for CPMD library.
# We don't need necimain.o, cpmdstub.o, init_coul.o, init_coul2D.o.  We keep libstub though.
OBJECTS_RCPMD := $(filter-out %%necimain.o %%cpmdstub.o %%init_coul.o %%init_coul2D.o,$(OBJECTS)) 
OBJECTS_KCPMD := $(addprefix $(KDEST)/,$(notdir $(OBJECTS_RCPMD)))

# Objects for VASP library.
# We don't need necimain.o, vaspstub.o, init_coul.o, init_coul2D.o.  We keep libstub though.
OBJECTS_RVASP := $(filter-out %%necimain.o %%vaspstub.o %% %%init_coul.o %%init_coul2D.o, $(OBJECTS)) 
OBJECTS_KVASP := $(addprefix $(KDEST)/,$(notdir $(OBJECTS_RVASP)))

#-----
# Dependency files.

# Fortran dependencies.
# We need these before compiling any fortran files.
# Some compilers (I'm looking at you pathscale) create module files with
# UPPERCASE names.  It is useful to always compile with a consistent set of
# dependencies (no matter what the platform) so we create dependency files which
# have use uppercase and lowercase module names. 
FRDEPEND = $(GDEP_DEST)/ldepend
FCDEPEND = $(KDEP_DEST)/ldepend
FDEPEND = $(FRDEPEND) $(FCDEPEND)
FRDEPENDUP = $(GDEP_DEST)/UDEPEND
FCDEPENDUP = $(KDEP_DEST)/UDEPEND
FDEPENDUP = $(FRDEPENDUP) $(FCDEPENDUP)

# C dependencies.
# We don't need these when we first compile, only when we recompile.
# We achieve this (most of the time) by recompiling the C dependencies every
# time we compile.
cppDEPEND_FILES = $(addprefix $(GDEP_DEST)/,$(notdir $(cppOBJ:.o=.d)))
cDEPEND_FILES = $(addprefix $(GDEP_DEST)/,$(notdir $(cOBJ:.o=.d)))
KcppDEPEND_FILES = $(addprefix $(KDEP_DEST)/,$(notdir $(KcppOBJ:.o=.d)))
KcDEPEND_FILES = $(addprefix $(KDEP_DEST)/,$(notdir $(KcOBJ:.o=.d)))
CDEPEND = $(cppDEPEND_FILES) $(cDEPEND_FILES) $(KcppDEPEND_FILES) $(KcDEPEND_FILES)

#-----
# Set make's special rules

# Rules which don't actually produce any files...
.PHONY: clean cleanall depend rmdeps help utils

# Compile neci.x by default.
.DEFAULT_GOAL := neci.x

# Don't delete any intermediate files (e.g. bin/*.x when the goal doesn't
# include the full path; .F90 files produced from template files).
.SECONDARY: $(addprefix $(TDEST)/,$(notdir $(basename $(F90TMPSRCFILES)))) $(PROGS) $(NECILIBS) $(UTILS)

# Extensions of files to compile.
.SUFFIXES:
.SUFFIXES: $(EXTS) .f .f90

#-----
# Goals

# First, some helpful macros.

# Rebuild of environment_report.
GBLD_ENV = rm $(GDEST)/environment_report.* && $(my_make) $(GDEST)/environment_report.o
KBLD_ENV = rm $(KDEST)/environment_report.* && $(my_make) $(KDEST)/environment_report.o

# Creating an archive from *.o files.
ARCHIVE = $(AR) $(ARFLAGS) $@ $^

# Link target to prerequisite.
LINK = cd $(dir $<) && ln -s -f $(<F) $(@F)

# We compile all binaries and libraries to platform-specific filenames and link
# the most recently compiled one to (e.g.) neci.x or gneci-cpmd.a. 
$(EXE)/%%.x: $(EXE)/%%.$(CONFIG).$(OPT).x
\t$(LINK)

$(LIB)/%%.a: $(LIB)/%%.$(CONFIG).$(OPT).a
\t$(LINK)

# Compiling *.x
$(EXE)/neci.$(CONFIG).$(OPT).x: $(OBJECTS_NECI)
\t$(GBLD_ENV)
\t$(LD) $(LDFLAGS) -o $@ $(OBJECTS_NECI) $(LIBS)

$(EXE)/kneci.$(CONFIG).$(OPT).x: $(OBJECTS_KNECI)
\t$(KBLD_ENV)
\t$(LD) $(LDFLAGS) -o $@ $(OBJECTS_KNECI) $(LIBS)

# Compiling libraries.
$(LIB)/gneci-cpmd.$(CONFIG).$(OPT).a: $(OBJECTS_RCPMD)
\t$(GBLD_ENV)
\t$(ARCHIVE)

$(LIB)/kneci-cpmd.$(CONFIG).$(OPT).a: $(OBJECTS_KCPMD)
\t$(KBLD_ENV)
\t$(ARCHIVE)

$(LIB)/gneci-vasp.$(CONFIG).$(OPT).a: $(OBJECTS_RVASP)
\t$(GBLD_ENV)
\t$(ARCHIVE)

$(LIB)/kneci-vasp.$(CONFIG).$(OPT).a: $(OBJECTS_KVASP)
\t$(KBLD_ENV)
\t$(ARCHIVE)

clean: 
\trm -f {$(GDEST),$(KDEST),$(TDEST)}/* $(EXE)/*.$(CONFIG).$(OPT).x $(LIB)/*.$(CONFIG).$(OPT).a

cleanall:
\trm -rf dest lib bin

# Generate dependency files for Fortran source files.
# We assume that all module files are in *.F90 files.
# This requires the JSS modified version of sfmakepend (supplied with neci).
# sds50: sed command to avoid tinkering with sfmakedepend to work with templates.
MKDEPEND = $(TOOLS)/sfmakedepend --file - --cpp --fext=f90 --depend=mod --silent $(FSRCFILES) $(F90SRCFILES) $(F90TMPSRCFILES) 
RMTEMPLATE = sed -e 's/\.F90\.template//g'
$(FRDEPEND):
\t$(MKDEPEND) --objdir \$$\(GDEST\) --moddir \$$\(GDEST\) | $(RMTEMPLATE) > $@

$(FCDEPEND):
\t$(MKDEPEND) --objdir \$$\(KDEST\) --moddir \$$\(KDEST\) | $(RMTEMPLATE) > $@
$(FRDEPENDUP):
\t$(MKDEPEND) --case=upper --objdir \$$\(GDEST\) --moddir \$$\(GDEST\) | $(RMTEMPLATE) > $@
$(FCDEPENDUP):
\t$(MKDEPEND) --case=upper --objdir \$$\(KDEST\) --moddir \$$\(KDEST\) | $(RMTEMPLATE) > $@

# Generate all dependency files.
depend: 
\t$(my_make) -B $(FDEPEND) $(FDEPENDUP) $(CDEPEND)

# Delete dependency files.
rmdeps:
\trm -f $(FDEPEND) $(FDEPENDUP) $(CDEPEND)

tags: null_goal
\tctags --langmap=fortran:.F90.template $(SRCFILES)

# Empty goal.  Depending on this will force a rule to be run.
null_goal: ;

#-----
# Shortcut goals

# Target to point *.x to bin/*.x.
# Because we use an implicit rule, make attempts to find an implicit command
# associated with .x files (and one does not exist).  The semi-colon defines an
# empty command and hence prevents make seeking the non-existant command to
# execute when we attempt to build .x files...
# (Helpfully documented for the future as figured out that aspect of make was "fun".)
%%.x: $(EXE)/%%.x ;

new: clean neci.x

both: neci.x kneci.x

cpmdlibs: $(CPMDLIBS)

vasplibs: $(VASPLIBS)

libs: $(NECILIBS)

utils: $(UTILS) $(UTILS_C)

all: $(PROGS) libs utils

#-----
# Help message.

help:
\t@echo "make [target(s)]"
\t@echo
\t@echo "Targets:"
\t@echo "neci.x        compile neci.x."
\t@echo "kneci.x       compile kneci.x."
\t@echo "both          compile neci.x AND kneci.x."
\t@echo "new           run clean and then compile neci.x."
\t@echo "gneci-cpmd    compile neci library for integration with gamma-point version of cpmd."
\t@echo "kneci-cpmd    compile neci library for integration with k-point version of cpmd."
\t@echo "cpmdlibs      compile both libraries for integration with cpmd."
\t@echo "gneci-vasp    compile neci library for integration with gamma-point version of vasp."
\t@echo "kneci-vasp    compile neci library for integration with k-point version of vasp."
\t@echo "vasplibs      compile both libraries for integration with vasp."
\t@echo "libs          compile all libraries for integration with cpmd and vasp."
\t@echo "utils         compile all utility programs."
\t@echo "TransLz.x     compile the TransLz utility program."
\t@echo "ConvertMolpFCID.x   compile the program to create Fock energies in the MOLPRO FCIDUMP."
\t@echo "BlockFCIMC.x  compile the BlockFCIMC utility program."
\t@echo "ModelFCIQMC.x compile the ModelFCIQMC example program."
\t@echo "ModelCompFCIQMC.x compile the ModelCompFCIQMC complex example program."
\t@echo "ConvertPOPSFILE.x compile the ConvertPOPSFILE program."
\t@echo "clean         remove all compiled objects for the current platform and optimisation level." 
\t@echo "cleanall      remove all compiled objects for all platforms and optimisation levels and the dependency files." 
\t@echo "tags          run ctags on all source files."
\t@echo "depend        update the list of dependencies.  Note that make 3.80 is buggy and running this causes an infinte loop."
\t@echo "rmdeps        remove all dependency files.  Use this instead of the depend target on 3.80."
\t@echo "help          print this message."

#-----
# Compilation macros (explicit rules)

# Some more helpful macros.
CPP_BODY = $(CPPFLAGS) $< $@
C_BODY = $(CFLAGS) $(CPPFLAGS) -c $< -o $@ 
MAKE_C_GDEPS = $(CCD) $(CFLAGS) -MM -MT \$$\(GDEST\)/$(addsuffix .o,$(basename $(notdir $@))) $< -o $@
MAKE_C_KDEPS = $(CCD) $(CFLAGS) -MM -MT \$$\(KDEST\)/$(addsuffix .o,$(basename $(notdir $@))) $< -o $@

# Include paths
INCLUDE_PATH = $(addprefix -I ,$(SRC))

# stat command for checking last modified time.
system = $(shell uname -s)
# BSD (ie OSX as far as we're concerned) has a different stat command.
ifeq ($(system),Darwin)
\tstat_cmd = stat -f %%m
else
\t# Linux systems.
\tstat_cmd = stat --format=%%Y
endif

# Compiling fortran source files...

# 1. Pre-processing.
# Provide INCLUDE_PATH as not all source files are in the same directory as
# (e.g.) macros.h.
# a) gamma-point.
$(GDEST)/%%.f90: %%.F90
\t$(CPP) $(CPP_BODY) $(GCPPFLAG) $(INCLUDE_PATH)

$(GDEST)/%%.f: %%.F
\t$(CPP) $(CPP_BODY) $(GCPPFLAG) $(INCLUDE_PATH)

# b) k-point.
$(KDEST)/%%.f90: %%.F90
\t$(CPP) -D__CMPLX $(CPP_BODY) $(KCPPFLAG) $(INCLUDE_PATH)

$(KDEST)/%%.f: %%.F
\t$(CPP) -D__CMPLX $(CPP_BODY) $(KCPPFLAG) $(INCLUDE_PATH)

# c) With an option to generate from template files.
$(GDEST)/%%.f90: $(TDEST)/%%.F90
\t$(CPP) $(CPP_BODY) $(GCPPFLAG) $(INCLUDE_PATH)

$(KDEST)/%%.f90: $(TDEST)/%%.F90
\t$(CPP) -D__CMPLX $(CPP_BODY) $(KCPPFLAG) $(INCLUDE_PATH)

$(TDEST)/%%.F90: %%.F90.template
\t$(TOOLS)/f90_template.py $< $@

# 2. Compile.

# We assume that all module files are .F90 files.
# Fool compile_mod.pl.
# It's possible that the corresponding .o rule is performed before the .mod rule.
# When doing a clean build, the .time file associated with the .mod file doesn't 
# exist unless the .mod file was created by the .mod rule.  This leads to files 
# being compiled twice.  We create the .time file if it doesn't exist if the .mod 
# file was created at the same time as the .o file (picking up files which are compiled 
# quickly) or the .mod file is newer than the .f90 file (picking up complicated files
# which take several seconds to compile).
%%.mod:
\ttest -e $@ && test ! -e $(@:.mod=.time) && ( test $(shell $(stat_cmd) $@) -eq $(shell $(stat_cmd) $<) || test $(shell $(stat_cmd) $@) -gt $(shell $(stat_cmd) $(<:.o=.f90)) ) && touch $(@:.mod=.time) || true
\tperl -w $(TOOLS)/compile_mod.pl -cmp "perl -w $(TOOLS)/compare_module_file.pl -compiler $(compiler)" -fc "$(FC) $(FFLAGS) $(F90FLAGS) %(module_flag)s$(dir $@) $(INCLUDE_PATH) -c $(<:.o=.f90) -o $<" -provides "$@" -requires "$(<:.o=.f90)"

$(F90OBJ) $(F90TMPOBJ) $(KF90OBJ) $(KF90TMPOBJ): %%.o: %%.f90
	perl -w $(TOOLS)/compile_mod.pl -cmp "perl -w $(TOOLS)/compare_module_file.pl -compiler $(compiler)" -fc "$(FC) $(FFLAGS) $(F90FLAGS) %(module_flag)s$(dir $@) $(INCLUDE_PATH) -c $< -o $@" -provides "$@" -requires "$^"

$(FOBJ) $(KFOBJ): %%.o: %%.f
	perl -w $(TOOLS)/compile_mod.pl -cmp "perl -w $(TOOLS)/compare_module_file.pl -compiler $(compiler)" -fc "$(FC) $(FFLAGS) $(F77FLAGS) %(module_flag)s$(dir $@) $(INCLUDE_PATH) -c $< -o $@" -provides "$@" -requires "$^"

# Compiling C source files...
# a) gamma-point.
$(cppOBJ): $(GDEST)/%%.o: %%.cpp
\t$(CC) $(C_BODY)

$(cOBJ): $(GDEST)/%%.o: %%.c
\t$(CC) $(C_BODY)

# b) k-point.
$(KcppOBJ): $(KDEST)/%%.o: %%.cpp
\t$(CC) -D__CMPLX $(C_BODY)

$(KcOBJ): $(KDEST)/%%.o: %%.c
\t$(CC) -D__CMPLX $(C_BODY)

# Update C dependency files.
# a) gamma-point.
$(cDEPEND_FILES): $(GDEP_DEST)/%%.d: %%.c
\t$(MAKE_C_GDEPS)

$(cppDEPEND_FILES): $(GDEP_DEST)/%%.d: %%.cpp
\t$(MAKE_C_GDEPS)

# b) k-point.
$(KcDEPEND_FILES): $(KDEP_DEST)/%%.d: %%.c
\t$(MAKE_C_KDEPS)

$(KcppDEPEND_FILES): $(KDEP_DEST)/%%.d: %%.cpp
\t$(MAKE_C_KDEPS)

#-----
# Utilities

# Macro to compile a utility Fortran program contained within a single source
# file.
# We assume that the source filename is *.f90, that the program name is based
# upon the source filename and that the utility program requires (at most) the
# same libraries as neci.
MKUTIL = $(FC) $(FFLAGS) $(F90FLAGS) $< -o $@ $(LIBS)
MKUTIL_C = $(CC) $< -o $@ $(LIBS)

# Compile bin/*.config.opt.x from utils/*.f90
# Previously defined targets point bin/*.x to bin/*.config.opt.x and from *.x to bin/*.x.
# The static pattern results in applying this to only targets of the form $(EXE)/*.$(CONFIG).$(OPT).x
# where *.x is one of the programs defined in $(UTILS).
UTILSTEM = $(notdir $(basename $(UTILS)))
UTILNAMES = $(addsuffix .$(CONFIG).$(OPT).x,$(UTILSTEM))
$(addprefix $(EXE)/,$(UTILNAMES)): $(EXE)/%%.$(CONFIG).$(OPT).x: utils/%%.f90
\t$(MKUTIL)

# Also for c++ files
UTILSTEM_C = $(notdir $(basename $(UTILS_C)))
UTILNAMES_C = $(addsuffix .$(CONFIG).$(OPT).x,$(UTILSTEM_C))
$(addprefix $(EXE)/,$(UTILNAMES_C)): $(EXE)/%%.$(CONFIG).$(OPT).x: utils/%%.cpp
\t$(MKUTIL_C)

#-----
# Include dependency files

# Dependency files will be generated if they don't exist.
ifeq ($(findstring pathf, $(compiler)), pathf)
# Use dependencies based upon module files with UPPERCASE filenames.
# This is needed for all pathscale compilers.
include $(FDEPENDUP)
else
# Use dependencies based upon module files with lowercase filenames.
include $(FDEPEND)
endif
include $(CDEPEND)
'''

def parse_options(my_args):
    '''Parse command line options given in the my_args list.

Returns the options object and a space separated list of configuration files.'''
    parser = optparse.OptionParser(usage='''mkconfig.py [options] [configuration_file(s)]

If no configuration file is given then the .default file in the specified directory is used.
A configuration file does not need to be specified with the --ls and --print options.
Multiple configuration files can only be given in conjunction with the --print option.''')
    parser.add_option('-d', '--dir', default='config/', help='Set directory containing the configuration files. Prepended to the configuration filenames if a directory is not specified in the filename.  Default: %default.')
    parser.add_option('-g', '--debug', action='store_true', default=False, help='Use the debug settings.  Default: use optimised settings.')
    parser.add_option('-l', '--ls', action='store_true', default=False, help='Print list of available configurations.')
    parser.add_option('-o', '--out', default='Makefile', help='Set the output filename to which the makefile is written.  Use -o - to write to stdout.  Default: %default.')
    parser.add_option('-p', '--print', dest='print_conf', action='store_true', default=False, help='Print settings in configuration file(s) specified, or all settings if no configuration file is specified.')

    (options, args) = parser.parse_args(my_args)

    if len(args) >= 1:
        config_file = ''
        for c in args:
            if not os.path.dirname(c):
                c = os.path.join(options.dir, c)
            config_file = '%s %s' % (config_file, c)
        config_file = config_file.strip()
    elif len(args) == 0 and os.path.exists(os.path.join(options.dir, '.default')):
        config_file = os.path.join(options.dir, '.default')
    else:
        config_file = None

    if not (options.print_conf or options.ls):
        if len(args) > 1:
            print 'Incorrect arguments.'
            parser.print_help()
            sys.exit(1)
        if not config_file:
            print '.default file not found.'
            parser.print_help()
            sys.exit(1)

    return (options, config_file)

def list_configs(config_dir):
    '''Return the path to all config files in config_dir.  We assume only config files are in config_dir'''
    if os.path.isdir(config_dir):
        return [os.path.join(config_dir, f) for f in os.listdir(config_dir)]
    else:
        raise IOError, 'Config directory specified is not a directory: %s.' % (config_dir)

def parse_config(config_file):
    '''Parse the configuration file config_file located in the directory config_dir.'''
    parser = ConfigParser.RawConfigParser()

    valid_sections = ['main', 'opt', 'dbg']

    valid_sections_upper = [s.upper() for s in valid_sections]

    valid_options = ['fc', 'fflags', 'f77flags', 'f90flags', 'module_flag', 'compiler', 'cc', 'cflags', 'ccd', 'cpp', 'cppflags', 'ld', 'ldflags', 'libs', 'max_mem']

    minimal_options = ['fc', 'module_flag', 'cc', 'cpp', 'ld', 'libs']

    if not os.path.exists(config_file):
        raise IOError,'Config file does not exist: %s' % (config_file)

    parser.read(config_file)

    for s in parser.sections():
        if s not in valid_sections and s not in valid_sections_upper:
            raise IOError, 'Invalid section in configuration file %s: %s.' % (config_file, s)

    for s in valid_sections:
        if s not in parser.sections() and s.upper() not in parser.sections():
            raise IOError, 'Section not present in configuration file %s: %s.' % (config_file, s)             

    if not parser.sections():
        raise IOError, 'No sections in configuration file %s: %s.' % (config_file, s)

    config = {}

    for s in valid_sections:
        config[s] = dict(parser.items('main'))
        if s in parser.sections():
            config[s].update(parser.items(s))
        elif s.upper() in parser.sections():
            config[s].update(parser.items(s.upper()))

    for s in valid_sections:
        for opt in config[s].keys():
            if opt not in valid_options:
                raise IOError, 'Invalid option in configuration file: %s.' % (opt)
        # Fill in blanks
        for opt in valid_options:
            if opt not in config[s].keys():
                if opt == 'max_mem':
                    config[s][opt] = 2048
                else:
                    config[s][opt] = ''

    config.pop('main')

    for s in config.keys():
        # Check minimal options.
        for opt in minimal_options:
            if not config[s][opt]:
                raise IOError, 'Required option not set: %s' % (opt)
        # Treat module_flag specially: append a space if it doesn't end in =.
        # This is to allow the same template to be used no matter how the compiler
        # insists on handling this flag.
        if not config[s]['module_flag'][-1] == '=':
            config[s]['module_flag'] = '%s ' % (config[s]['module_flag'])

    return config

def create_makefile(config_file, use_debug=False):
    '''Returns the makefile using the options given in the config_file.'''
    if use_debug:
        config = parse_config(config_file)['dbg']
        config.update(opt_level='debug')
        if 'cppflags' in config.keys():
            cppflags = config["cppflags"]
        else:
            cppflags = ""
        cppflags += " -D__DEBUG"
        config["cppflags"] = cppflags
    else:
        config = parse_config(config_file)['opt']
        config.update(opt_level='optimised')
    # Set the name in the Makefile to be the basename of the config filename.  Follow any links.
    if os.path.islink(config_file):
        config_name = os.path.basename(os.readlink(config_file))
    else:
        config_name = os.path.basename(config_file)
    config.update(config=config_name)
    return MAKEFILE_TEMPLATE % (config)

if __name__=='__main__':
    args=sys.argv[1:]
    (options, config_file) = parse_options(args)
    if options.ls:
        print 'Available configurations are: %s.' % (', '.join(list_configs(options.dir)))
    elif options.print_conf:
        if config_file:
            config_files = config_file.split()
        else:
            config_files = list_configs(options.dir)
        for config_file in config_files:
            config = parse_config(config_file)
            print 'Settings in configuration file: %s' % (config_file)
            pprint.pprint(config)
            print
    else:
        if options.out == '-':
            f = sys.stdout
        else:
            f = open(options.out, 'w')
        f.write(create_makefile(config_file, options.debug))
        if options.out != '-':
            f.close()
