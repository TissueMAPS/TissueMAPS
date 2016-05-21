TissueMAPS client
=================


## Setup the TissueMAPS client

    $ cd TissueMAPS/client

Install required node modules (nodejs and its package manager `npm` must be installed on your system) by executing:

    $ npm install

Fetch all libraries:

    $ bower install

To build the client code issue the command:

    $ gulp build --prod

This will create a directory `build` with all the required contents. The
contents of this directory can now be served by a webserver such as NGINX.

If you rather want to develop TissueMAPS you can build the code using the
command

    $ gulp [dev]

This will also auto-watch files and rebuild the code as necessary.
A node-based development server will be started that will serve your files directly, so you don't need to setup NGINX.


## Building the modified openlayers source code

Building the custom openlayers code should not be necessary since the latest
version is included in the TissueMAPS distribution.
However, if any changes to the custom openlayers version are made, the code has to be rebuilt.
First all the dependencies for the openlayers build environment have to be
installed:

    $ gulp init-ol

**Note:** If you receive an error about the system not being able to find the
executable `gulp`, you need to install the grunt CLI tool: `npm install -g
gulp`.

Now either you can build the OpenLayers code in debug mode (recommended for
development) by executing

    $ gulp compile-ol-debug

It is a good idea to also build it normally since this will cause the project
to be compiled using Google's closure compiler which will warn about type errors.

**TODO**: There is currently a problem with building OpenLayers in production
so its recommended to use the debug build.

    $ gulp compile-ol

**Note:** Building openlayers might cause troubles depending on your node
version.
The version we used was 5.8.0 On OSX you can switch to another
version of a package like this: `brew switch node 5.8.0`.

These commands will build the openlayers code and put the resulting javascript
file under `TissueMAPS/client/assets/libs/`.
