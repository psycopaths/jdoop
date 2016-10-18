#!/bin/bash

# Copyright 2015 Marko Dimjašević
#
# This file is part of JDoop.
#
# JDoop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# JDoop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with JDoop.  If not, see <http://www.gnu.org/licenses/>.

# Script adopted from Raimondas Sasnauskas and SMACK's installation
# scripts

# Exit on error
set -e

project_root_dir=/mnt/storage/jdart-project

# Set these flags to control what to install
install_packages=1
install_z3=1
install_jpf_core=1
install_jdart=1


if [ ${install_packages} -eq 1 ]; then

    # Make sure Debian backports are enabled. This is needed for Java
    # 8 packages
    apt_source_file=/etc/apt/sources.list.d/debian-backports.list
    sudo su -c "echo 'deb http://mirrors.kernel.org/debian jessie-backports main' > ${apt_source_file}"
    sudo su -c "echo 'deb-src http://mirrors.kernel.org/debian jessie-backports main' >> ${apt_source_file}"
    
    # This is for Debian 8 (Jessie) x86-64 on Emulab
    echo 'firmware-linux-free hold' | sudo dpkg --set-selections
    echo 'grub-common hold' | sudo dpkg --set-selections
    echo 'grub-pc hold' | sudo dpkg --set-selections
    echo 'grub-pc-bin hold' | sudo dpkg --set-selections
    echo 'grub2-common hold' | sudo dpkg --set-selections
    echo 'linux-headers-3.2.0-4-all-amd64 hold' | sudo dpkg --set-selections
    echo 'linux-image-amd64 hold' | sudo dpkg --set-selections
    echo 'linux-image-3.16.0-4-amd64 hold' | sudo dpkg --set-selections
    
    sudo apt-get update
    dependencies="htop screen tree git mercurial ant ant-optional openjdk-8-jre openjdk-8-jre-headless openjdk-8-jdk antlr3 libguava-java python maven"
    sudo apt-get install --assume-yes $dependencies

    # Set Java 8 as the default Java version
    sudo update-alternatives --set java  /usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java
    sudo update-alternatives --set javac /usr/lib/jvm/java-8-openjdk-amd64/bin/javac
fi

# Make sure Java 8 is the default version
java_version=`java -version 2>&1 | grep "version" | awk -F"\"" '{print $2}' | awk -F"\." '{print $1"."$2}'`
if [ "${java_version}" != "1.8" ]; then
    echo "Error: Java 8 must be set as the default Java version" >&2
    exit 1
fi
javac_version=`javac -version 2>&1 | awk -F" " '{print $2}' | awk -F"\." '{print $1"."$2}'`
if [ "${javac_version}" != "1.8" ]; then
    echo "Error: Java compiler 8 must be set as the default Java version" >&2
    exit 1
fi

# Install Z3

if [ ${install_z3} -eq 1 ]; then

    # z3 has been packaged only for Debian Stretch (Debian 9), so we
    # will download its binary packages from a Stretch snapshot
    # archive.
    #
    # Note we're using version 4.4.0-5 as 4.4.1 Debian builds (prior
    # to and including 4.4.1-0.5) have faulty libz3java.so that breaks
    # jconstraints-z3 (jconstraints-z3 reports it cannot find the
    # library on standard paths (including LD_LIBRARY_PATH and
    # java.library.path)).

    # 4.4.0-5
    wget http://snapshot.debian.org/archive/debian/20151208T035513Z/pool/main/z/z3/libz3-dev_4.4.0-5_amd64.deb
    wget http://snapshot.debian.org/archive/debian/20151208T035513Z/pool/main/z/z3/libz3-jni_4.4.0-5_amd64.deb
    wget http://snapshot.debian.org/archive/debian/20151208T035513Z/pool/main/z/z3/libz3-java_4.4.0-5_all.deb
    wget http://snapshot.debian.org/archive/debian/20151208T035513Z/pool/main/z/z3/z3_4.4.0-5_amd64.deb

    for pkg in libz3-dev libz3-jni libz3-java z3; do
	sudo dpkg --install $pkg*.deb
    done

    if [ -f "~/.m2" ]; then
	rm ~/.m2
    fi
    mkdir -p ${project_root_dir}/.m2
    ln -s ${project_root_dir}/.m2 ~/.m2 || true
    mkdir -p ~/.m2/repository
    
    mvn install:install-file -Dfile=/usr/share/java/com.microsoft.z3.jar \
	-DgroupId=com.microsoft -DartifactId=z3 -Dversion=4.4.0 \
	-Dpackaging=jar
fi

# Install JPF modules
# JPF configuration directory

if [ ${install_jpf_core} -eq 1 ] || [ ${install_jdart} -eq 1 ]; then

    jpf_conf_dir=${project_root_dir}/.jpf
    mkdir -p $jpf_conf_dir
    ln -s ${jpf_conf_dir}/ ~/.jpf || true
    jpf_conf_file=~/.jpf/site.properties
fi


if [ ${install_jpf_core} -eq 1 ]; then

    # Install jpf-core
    jpf_core_dir=${project_root_dir}/jpf-core
    hg clone http://babelfish.arc.nasa.gov/hg/jpf/jpf-core ${jpf_core_dir}
    cd ${jpf_core_dir}
    # Revert to a commit we are sure works with JDoop
    hg update --rev 31
    ant

    echo "jpf-core = ${jpf_core_dir}" >> ${jpf_conf_file}
fi


if [ ${install_jdart} -eq 1 ]; then

    # Install jconstraints
    jconstraints_dir=${project_root_dir}/jconstraints
    git clone https://github.com/psycopaths/jconstraints.git ${jconstraints_dir}
    cd ${jconstraints_dir}
    git checkout 4b4440c # This is the jconstraints-0.9.1 tag as of
			 # Aug 23, 2016
    mvn install

    jconstraints_conf_dir=${project_root_dir}/.jconstraints
    mkdir -p ${jconstraints_conf_dir}/extensions
    ln -s ${jconstraints_conf_dir} ~/.jconstraints || true
    cp /usr/share/java/com.microsoft.z3.jar ~/.jconstraints/extensions

    # Install jconstraints-z3
    # export LD_LIBRARY_PATH=/usr/lib
    jconstraints_z3_dir=${project_root_dir}/jconstraints-z3
    git clone https://github.com/psycopaths/jconstraints-z3.git ${jconstraints_z3_dir}
    cd ${jconstraints_z3_dir}
    git checkout 1a31c98 # This is the jconstraints-z3-0.9.0 tag as of
			 # Aug 23, 2016
    sed -i -e 's/4\.4\.1/4\.4\.0/g' pom.xml
    mvn install
    cp target/jconstraints-z3-0.9.0.jar ~/.jconstraints/extensions

    echo "jconstraints = $jconstraints_dir" >> ${jpf_conf_file}

    # Install JDart
    jdart_dir=${project_root_dir}/jdart
    git clone https://github.com/psycopaths/jdart.git ${jdart_dir}
    cd ${jdart_dir}
    git checkout cd5b815 # This is a version as of Aug 29, 2016
    ant

    echo "jpf-jdart = ${jdart_dir}" >> ${jpf_conf_file}
    echo "extensions=\${jpf-core},\${jpf-jdart}" >> ${jpf_conf_file}

fi
