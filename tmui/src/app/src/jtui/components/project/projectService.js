// Copyright (C) 2016-2019 University of Zurich.
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
angular.module('jtui.project')
.service('projectService', ['$http', '$q', 'Project',
         function ($http, $q, Project) {


    function values2yaml(jtproject) {
        // The angular <input> directive converts all input to string.
        // Therefore, we'll convert the string back to YAML.
        var data = angular.copy(jtproject);  // removes the $$hashKeys elements
        var changedHandles = _.map(data.handles, function (h) {
            for (var i in h.description.input) {
                if ('key' in h.description.input[i]) {
                    var val = h.description.input[i].key;
                    // Let's quote the value of "key" keys to be sure
                    // that they will be strings.
                    val = "'" + val + "'";
                } else {
                    var val = h.description.input[i].value;
                }
                var name = h.description.input[i].name;
                // console.log('value of "' + name + '" : ' + val)
                // To support arrays, we need to split the string into an array
                if (typeof val == 'string') {
                    if (val.indexOf(',') > -1) {
                        val = val.split(',');
                    }
                }
                if (val instanceof Array) {
                    // After splitting the string we have an array,
                    // but we need to account for the case of empty inputs
                    // ("undefined" breaks the YAML parser).
                    if (val == "" || undefined) {
                        var val = [];
                    }
                    // For non-empty input we convert each element to YAML
                    var newValue = val.map(function (v) {
                        return jsyaml.safeLoad(v);
                    });
                    // Now we deal with arrays with a single element and empty
                    // arrays
                    if (newValue.length == 1) {
                        newValue = newValue[0];
                    } else if (newValue.length == 0) {
                        newValue = jsyaml.safeLoad(null);
                    }
                } else if (val == undefined) {
                    var newValue = jsyaml.safeLoad(null);
                } else {
                    var newValue = jsyaml.safeLoad(val);
                }
                if ('key' in h.description.input[i]) {
                    h.description.input[i].key = newValue;
                } else {
                    h.description.input[i].value = newValue;
                }
            }
            return h;
        });
        data.handles = changedHandles;
        return data;
    };

    function getProject(experimentID) {

        var projectDef = $q.defer();
        var url = '/jtui/experiments/' + experimentID + '/project';
        $http.get(url).success(function (data) {
            var proj = jsyaml.safeLoad(data.jtproject);
            // console.log('received project description: ', proj)
            if (proj.pipe.description.pipeline == null) {
                proj.pipe.description.pipeline = [];
            }
            var project = new Project(
                  experimentID,
                  proj['pipe'],
                  proj['handles']
            );
            // console.log('created project: ', project)

            projectDef.resolve(project);
        });

        return(projectDef.promise);
    }

    function getChannels(experimentID) {

        var channelsDef = $q.defer();
        var url = '/jtui/experiments/' + experimentID + '/available_channels';
        $http.get(url).success(function (data) {
            // console.log('available channels: ', data.channels)
            channelsDef.resolve(data.channels)
        });

        return(channelsDef.promise)
    }

    function getObjectTypes(experimentID) {

        var objectTypesDef = $q.defer();
        var url = '/jtui/experiments/' + experimentID + '/available_object_types';
        $http.get(url).success(function (data) {
            // console.log('available object types: ', data.object_types)
            objectTypesDef.resolve(data.object_types)
        });

        return(objectTypesDef.promise)
    }

    function getModuleFigure(experimentID, moduleName, jobID) {

        var figureDef = $q.defer();
        var url = '/jtui/experiments/' + experimentID +
                  '/figure' +
                  '?' + 'job_id=' + jobID + '&' + 'module_name=' + moduleName;
        $http.get(url).success(function (data) {
            figureDef.resolve(data)
        });

        return(figureDef.promise)
    }

    function saveProject(project) {

        // console.log('changed project:', values2yaml(project))

        var url = '/jtui/experiments/' + project.experiment_id + '/project';
        var request = $http({
            method: 'post',
            url: url,
            data: {
                project: jsyaml.safeDump(values2yaml(project))
            }
        });

        return(request.then(handleSuccess, handleError));
    }

    function checkProject(project) {

        // console.log('changed project:', values2yaml(project))

        var url = '/jtui/experiments/' + project.experiment_id + '/project/check';
        var request = $http({
            method: 'post',
            url: url,
            data: {
                project: jsyaml.safeDump(values2yaml(project))
            }
        });

        return(request.then(handleSuccess, handleError));
    }

    function createJoblist(project) {

        var url = '/jtui/experiments/' + project.experiment_id + '/joblist';
        var request = $http({
            method: 'post',
            url: url,
            data: {}
        });

        return(request.then(handleSuccess, handleError));
    }

    return({
        getProject: getProject,
        getChannels: getChannels,
        getObjectTypes: getObjectTypes,
        getModuleFigure: getModuleFigure,
        saveProject: saveProject,
        checkProject: checkProject,
        createJoblist: createJoblist,
        values2yaml: values2yaml
    });

    function handleError(response) {
        // The API response from the server should be returned in a
        // normalized format. However, if the request was not handled by the
        // server (or what not handles properly - ex. server error), then we
        // may have to normalize it on our end, as best we can.
        if (
            ! angular.isObject(response.data) ||
            ! response.data.message
            ) {

            return($q.reject("An unknown error occurred."));

        }

        // Otherwise, use expected error message.
        return($q.reject(response.data.message));

    }


    // Transform the successful response, unwrapping the application data
    // from the API response payload.
    function handleSuccess(response) {

        return(response.data);

    }

}]);
