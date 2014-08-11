#!/bin/bash

# Script adopted from Raimondas Sasnauskas and SMACK's installation
# scripts

# Exit on error
set -e

PROJECTS_ROOT=/mnt/storage/projects

# Set these flags to control what to install
INSTALL_PACKAGES=1
INSTALL_Z3=1
INSTALL_JPF_CORE=1
INSTALL_JPF_JDART=1

# Directories
Z3_DIR=$PROJECTS_ROOT/z3
JPF_DIR=$PROJECTS_ROOT/jpf


if [ ${INSTALL_PACKAGES} -eq 1 ]; then

    # this is for Ubuntu 12.04 x86-64 on Emulab
    echo 'linux-firmware hold' | dpkg --set-selections
    echo 'grub-common hold' | dpkg --set-selections
    echo 'grub-pc hold' | dpkg --set-selections
    echo 'grub-pc-bin hold' | dpkg --set-selections
    echo 'grub2-common hold' | dpkg --set-selections
    echo 'linux-headers-2.6.38.7-1.0emulab hold' | dpkg --set-selections
    echo 'linux-image-2.6.38.7-1.0emulab hold' | dpkg --set-selections
    
    sudo apt-get update
    sudo apt-get install -y htop screen tree mercurial ant ant-optional openjdk-7-jre openjdk-7-jre-headless openjdk-7-jre-lib openjdk-7-jdk antlr3 libguava-java python maven

fi

# Install Z3

if [ ${INSTALL_Z3} -eq 1 ]; then

    mkdir -p $Z3_DIR
    cd $Z3_DIR
    wget "http://download-codeplex.sec.s-msft.com/Download/SourceControlFileDownload.ashx?ProjectName=z3&changeSetId=0df0174d6216a9cbaeb1dab0443e9a626ec5dddb"
    unzip -o SourceControlFileDownload*
    rm -f SourceControlFileDownload*

    python scripts/mk_make.py --java
    cd build
    make -j32 all
    sudo make install
    cp $Z3_DIR/build/libz3java.so /usr/lib/
    
    mvn install:install-file -Dfile=com.microsoft.z3.jar -DgroupId=com.microsoft -DartifactId=z3 -Dversion=0.9 -Dpackaging=jar

fi

# Install JPF modules
# JPF configuration directory

if [ ${INSTALL_JPF_CORE} -eq 1 ] || [ ${INSTALL_JPF_JDART} -eq 1 ]; then

    JPF_CONF_DIR=$JPF_DIR/.jpf
    mkdir -p $JPF_CONF_DIR
    ln -s $JPF_CONF_DIR ~/.jpf
    JPF_CONF_FILE=$JPF_CONF_DIR/site.properties

fi


if [ ${INSTALL_JPF_CORE} -eq 1 ]; then

    # Install jpf-core
    JPF_CORE_DIR=$JPF_DIR/jpf-core
    hg clone http://babelfish.arc.nasa.gov/hg/jpf/jpf-core $JPF_CORE_DIR
    cd $JPF_CORE_DIR
    # Revert to a commit we are sure works with JPF-Doop
    hg update -r 1192
    ant

    echo "jpf-core = $JPF_CORE_DIR" >> $JPF_CONF_FILE

fi


if [ ${INSTALL_JPF_JDART} -eq 1 ]; then

    # Install jconstraints-z3
    export LD_LIBRARY_PATH=/usr/lib
    JCONST_Z3_DIR=$JPF_DIR/jconstraints-z3
    hg clone ssh://hg@bitbucket.org/psycopaths/jconstraints-z3 $JCONST_Z3_DIR
    cd $JCONST_Z3_DIR
    # Revert to a commit we are sure works with JPF-Doop
    hg update -r 9
    mvn install

    JCONST_CONF_DIR=$JPF_DIR/.jconstraints
    mkdir -p $JCONST_CONF_DIR/extensions
    ln -s $JCONST_CONF_DIR ~/.jconstraints
    cp target/jConstraints-z3-1.0-SNAPSHOT.jar ~/.jconstraints/extensions
    cp $Z3_DIR/build/com.microsoft.z3.jar ~/.jconstraints/extensions

    # Install jconstraints
    JCONST_DIR=$JPF_DIR/jconstraints
    hg clone ssh://hg@bitbucket.org/psycopaths/jconstraints $JCONST_DIR
    cd $JCONST_DIR
    # Revert to a commit we are sure works with JPF-Doop
    hg update -r 106
    mvn install

    echo "jconstraints = $JCONST_DIR" >> $JPF_CONF_FILE

    # Install jDART
    JDART_DIR=$JPF_DIR/jpf-jdart
    hg clone ssh://hg@bitbucket.org/psycopaths/jpf-jdart $JDART_DIR
    cd $JDART_DIR
    # Revert to a commit we are sure works with JPF-Doop
    hg update -r 226
    ant

    echo "jpf-jdart = $JDART_DIR" >> $JPF_CONF_FILE
    echo "extensions=\${jpf-core},\${jpf-jdart},\${jconstraints}" >> $JPF_CONF_FILE

fi
