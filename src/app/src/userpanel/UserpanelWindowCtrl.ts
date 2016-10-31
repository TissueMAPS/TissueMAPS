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
class UserpanelWindowCtrl {

    experiments: Experiment[] = [];

    experimentQuery = {
        name: ''
    };

    user: any;

    static $inject = ['application', 'session', '$state', 'dialogService'];

    constructor(private _viewerApp: Application,
                private _session: any,
                private _$state: any,
                private _dialogService: DialogService) {
        this.user = _session.getUser();

        (new ExperimentDAO()).getAll().then((exps) => {
            this.experiments = <Experiment[]>exps;
        });
    }

    modifyExperiment(e: Experiment) {
        // Enforce re-loading views when switching between experiments
        console.log('modify experiment "' + e.name + '"')
        this._$state.go('plate', {
            stageName: 'upload',
            experimentid: e.id,
            reload: true
        });
    }

    hasChannels(e: Experiment) {
        e.getChannels()
        .then((channels) => {
            if (channels.length == 0) {
                return false;
            }
            return channels.every(function(element, index, array) {
                return element.layers.length > 0;
            });
        })
    }

    viewExperiment(e: Experiment) {
        console.log('view experiment "' + e.name + '"')
        // TODO: modal with error when experiment doesn't have any channels yet
        this._$state.go('viewer', {
            experimentid: e.id
        });
    }

    deleteExperiment(e: Experiment) {
        this._dialogService.warning('Are you sure you want to delete this experiment?')
        .then((answer) => {
            return (new ExperimentDAO()).delete(e.id)
            .then((ok) => {
                if (ok) {
                    var idx = this.experiments.indexOf(e);
                    this.experiments.splice(idx, 1);
                    return true;
                } else {
                    return false;
                }
            })
            .catch((resp) => {
                console.log(resp);
            });
        });
    }
}

angular.module('tmaps.ui').controller('UserpanelWindowCtrl', UserpanelWindowCtrl);
