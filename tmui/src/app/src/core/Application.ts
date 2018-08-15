// Copyright 2016 Markus D. Herrmann, University of Zurich and Robin Hafen
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// TODO: Rename to ViewerApp
class Application {

    viewers: Viewer[] = [];
    activeViewer: Viewer;

    static $inject = ['$q'];

    constructor(private $q: ng.IQService) {
        // Check if the executing browser is PhantomJS (= code runs in
        // testing mode.
        var isPhantom = /PhantomJS/.test(window.navigator.userAgent);
        if (!isPhantom && !ol.has.WEBGL) {
            throw new Error('TissueMAPS requires a browser supporting WebGL!');
        }
    }

    removeViewer(viewer: Viewer) {
        var idx = this.viewers.indexOf(viewer);
        if (idx > -1) {
            var viewer = this.viewers[idx];
            viewer.destroy();
            this.viewers.splice(idx, 1);
        }
    }

    showViewer(viewer: Viewer): Viewer {
        this.viewers.forEach((v) => {
            if (v !== viewer) {
                v.hide();
            }
        });
        this.show();
        viewer.show();
        this.activeViewer = viewer;
        return viewer;
    }

    /**
     * Hide the whole viewport part of TissueMAPS.
     * Note that this will keep the active viewports. After calling
     * `showViewports` the state will be restored.
     * This function is called whenever the route sate changes away from the
     * visualization state.
     */
    hide() {
        this.viewers.forEach((viewer) => {
            viewer.hide();
        });
        $('#viewer-window').hide();
    }

    /**
     * Show the viewers after hiding them with `hideViewports`.
     */
    show() {
        $('#viewer-window').show();
        this.viewers.forEach((inst) => {
            inst.viewport.update();
        });
    }

    addViewer(viewer: Viewer) {
        this.viewers.push(viewer);
    }

    // serialize(): ng.IPromise<SerializedApplication> {
    //     var instPromises = _(this.viewers).map((inst) => {
    //         return inst.serialize();
    //     });
    //     return this.$q.all(instPromises).then((sers) => {
    //         var serApp =  {
    //             activeViewerNumber: this._activeViewerNumber,
    //             viewers: sers
    //         };
    //         return serApp;
    //     });
    // }

}

angular.module('tmaps.core').service('application', Application);

// interface SerializedApplication extends Serialized<Application> {
//     activeViewerNumber: number;
//     viewers: SerializedViewer[];
// }
