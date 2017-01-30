**********
TissueMAPS
**********

Online documentation is available at `tissuemaps.org <http://tissuemaps.org/>`_.


Installation of *TissueMAPS* Python packages during pre-release phase
---------------------------------------------------------------------

The installation guide of the documentation already assumes that packages are available on `PiPy <https://pypi.python.org/pypi>`_. For now, they still need to be installed from *Github*. Best practice is to use *SSH* key-based authentication. Please note that the ``setup.py`` files also already declare the packages as *PiPy* requirements. Therefore, the order of installing the modules is important.

You may find the following steps helpful:

* Create a *SSH* key-pair::

    ssh-keygen -f ~/.ssh/github

* Add the following lines to your ``~/.ssh/config`` file::

    Host github

        HostName        github.com
        User            git
        IdentityFile    ~/.ssh/github

* Add the public key ``~/.ssh/github.pub`` to your *Github* account, see `Github docs <https://help.github.com/articles/adding-a-new-ssh-key-to-your-github-account/>`_.

* **After** you have installed all non-Python dependencies as described in the installation guide, you can use the following script to create a virtual environment and install all *TissueMAPS* packages into it::

    #!/bin/bash
    sudo pip install virtualenv virtualenvwrapper
    export WORKON_HOME=$HOME/.virtualenvs
    source /usr/local/bin/virtualenvwrapper.sh
    workon tissuemaps || mkvirtualenv tissuemaps

    if [[ $(python -mplatform | grep -i Ubuntu) ]]
    then
        LIB_DIR=$VIRTUALENVWRAPPER_HOOK_DIR/tissuemaps/lib/python2.7/site-packages
        if [ ! -e $LIB_DIR/cv2.so ]
        then
            ln -s /usr/local/lib/python2.7/dist-packages/cv2.so $LIB_DIR/cv2.so
        fi
    elif [[ $(python -mplatform | grep -i Darwin) ]]
    then
        if [ ! -e $LIB_DIR/opencv3.pth ]
        then
            ln -s /usr/local/lib/python2.7/site-packages/opencv3.pth $LIB_DIR/opencv3.pth
        fi
    else
        exit 1
    fi
    
    git clone github:tissuemaps/gc3pie  $HOME/gc3pie
    cd $HOME/gc3pie && pip install -e . && cd
    
    PACKAGES=(jtlibrary jtmodules tmlibrary tmserver)
    RELEASE="v0.1.0"
    for p in "${PACKAGES[@]}"
    do
        git clone github:tissuemaps/$p $HOME/$p
        cd $HOME/$p && git checkout $RELEASE && pip install -e . && cd
    done

* Packages can be either optained individually (as exemplified in the above script) or via the main *TissueMAPS* repository. Individual repositories will by default point to the ``master`` branch. If you want the current release version you need to `checkout <https://git-scm.com/docs/git-checkout>`_ the latest release tag, e.g. ``v0.1.1``. The main *TissueMAPS* repository contains the other repositories as submodules, which will automatically get checked out at the current release tag::

    git clone --recursive https://github.com/TissueMAPS/TissueMAPS.git ~/tissuemaps
