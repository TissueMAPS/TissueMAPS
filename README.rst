**********
TissueMAPS
**********

Online documentation
--------------------

For the moment, documentation is available at `tissuemaps.org <https://tissuemaps.org>`_ and requires authentication. Use can login with your *Github* username.

Once repositories will be public, documentation will be hosted on `Read the Docs <https://readthedocs.org/>`_.


Installation of *TissueMAPS* Python packages during pre-release phase
---------------------------------------------------------------------

The installation guide of the documentation already assumes that packages are available on `PiPy <https://pypi.python.org/pypi>`_. For now, they still need to be installed from *Github*. This can get a bit tricky, because cloning private repositories require authentication. Best practice is to use *SSH* key-based authentication or `deploy keys <https://developer.github.com/guides/managing-deploy-keys/#deploy-keys>`_. In addition, the ``setup.py`` files also already declare the packages as requirements that can be installed from *PiPy*.

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

    PACKAGES=(jtlibrary jtmodules gc3pie tmlibrary tmserver)
    RELEASE="v0.1.0"
    for p in "${PACKAGES[@]}"
    do
        git clone github:tissuemaps/$p $HOME/$p
        cd $HOME/$p && git checkout $RELEASE && pip install -e . && cd
    done

* Packages can be either optained individually or via the main *TissueMAPS* repository. Individual repositories will by default be checked out at the latest commit. If you want the current release version you need to `checkout <https://git-scm.com/docs/git-checkout>`_ tag ``v0.1.0``. The main *TissueMAPS* repository contains the other repositories as submodules, which will automatically get checked out at the current release tag.::

    git clone --recursive https://github.com/TissueMAPS/TissueMAPS.git ~/tissuemaps
