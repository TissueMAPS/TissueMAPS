angular.module('jtui.project')
.service('projectService', ['$http', '$q', '$sce', 'Project',
         function ($http, $q, $sce, Project) {


    function values2yaml(jtproject) {
        // The angular <input> directive converts all input to string.
        // Therefore, we'll convert the string back to YAML.
        var data = angular.copy(jtproject);  // removes the $$hashKeys elements  
        var changedHandles = _.map(data.handles, function (h) {
            for (var i in h.description.input) {
                if ('key' in h.description.input[i]) {
                    var val = h.description.input[i].key;
                } else {
                    var val = h.description.input[i].value;
                }
                var name = h.description.input[i].name;
                // console.log('value of "' + name + '" : ' + val)
                // To support arrays, we need to split the string into an array
                if (typeof val == 'string') {
                    val = val.split(',');
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
                            return jsyaml.load(v);
                    });
                    // Now we deal with arrays with a single element and empty
                    // arrays
                    if (newValue.length == 1) {
                        newValue = newValue[0];
                    } else if (newValue.length == 0) {
                        newValue = jsyaml.load(null);
                    }
                } else if (val == undefined) {
                    var newValue = jsyaml.load(null);
                } else {
                    var newValue = jsyaml.load(val);
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

    function getProject(experimentID, pipeName) {

        console.log('get project ', pipeName);
        var projectDef = $q.defer();
        var url = '/jtui/get_jtproject' +
                  '/' + experimentID +
                  '/' + pipeName;
        $http.get(url).success(function (data) {
            var proj = jsyaml.safeLoad(data.jtproject);
            console.log('returned project: ', proj)
            if (proj.pipe.description.pipeline == null) {
                proj.pipe.description.pipeline = [];
            }
            var project = new Project(
                  experimentID,
                  proj['name'],
                  proj['pipe'],
                  proj['handles']
            );

            projectDef.resolve(project);
        });

        return(projectDef.promise);
    }

    function getChannels(experimentID) {

        var channelsDef = $q.defer();
        var url = '/jtui/get_available_channels' +
                  '/' + experimentID;
        $http.get(url).success(function (data) {
            console.log('available channels: ', data.channels)
            channelsDef.resolve(data.channels)
        });

        return(channelsDef.promise)
    }

    function getModuleFigure(experimentID, pipelineName, moduleName, jobID) {

        var figureDef = $q.defer();
        var url = '/jtui/get_module_figure' +
                  '/' + experimentID +
                  '/' + pipelineName +
                  '/' + moduleName +
                  '/' + jobID;
        $http.get(url).success(function (data) {
            figureDef.resolve(data)
        });

        return(figureDef.promise)
    }

    function saveProject(project) {

        // console.log('changed project:', values2yaml(project))

        var request = $http({
            method: 'post',
            url: '/jtui/save_jtproject' + '/' + project.experiment_id,
            data: {
                jtproject: jsyaml.safeDump(values2yaml(project))
            }
        });

        return(request.then(handleSuccess, handleError));
    }

    function checkProject(project) {

        // console.log('changed project:', values2yaml(project))

        var request = $http({
            method: 'post',
            url: '/jtui/check_jtproject' + '/' + project.experiment_id,
            data: {
                jtproject: jsyaml.safeDump(values2yaml(project))
            }
        });

        return(request.then(handleSuccess, handleError));
    }

    function createJoblist(project) {

        // Remove empty pattern from project object
        project.pipe.description.images.layers = project.pipe.description.images.layers.filter(function (pat) {
            console.log(pat)
            return pat.name != ""
        });

        var request = $http({
            method: 'post',
            url: '/jtui/create_joblist' + '/' + project.experiment_id,
            data: {
                jtproject: jsyaml.safeDump(values2yaml(project))
            }
        });

        return(request.then(handleSuccess, handleError));
    }

    function createJtproject(newProject) {

        console.log('project: ', newProject)

        var request = $http({
            method: 'post',
            url: '/jtui/create_jtproject' + '/' + newProject.experiment_id,
            data: {
                pipeline: newProject.projectName,
                template: newProject.skelName
            }
        });

        return(request.then(handleSuccess, handleError));
    }

    function removeJtproject(project) {

        console.log('project: ', project)

        var request = $http({
            method: 'post',
            url: '/jtui/remove_jtproject' + '/' + project.experiment_id,
            data: {
                jtproject: jsyaml.safeDump(values2yaml(project))
            }
        });

        return(request.then(handleSuccess, handleError));
    }

    function createJoblist(project) {

        // // Remove empty pattern from project object
        // project.pipe.description.images.layers = project.pipe.description.images.layers.filter(function (pat) {
        //     console.log(pat)
        //     return pat.name != ""
        // });

        console.log('create joblist for project: ', project)

        var request = $http({
            method: 'post',
            url: '/jtui/create_joblist' + '/' + project.experiment_id,
            data: {
                jtproject: jsyaml.safeDump(values2yaml(project))
            }
        });

        return(request.then(handleSuccess, handleError));
    }

    return({
        // getProjects: getProjects,
        getProject: getProject,
        // getExperiments: getExperiments,
        getChannels: getChannels,
        getModuleFigure: getModuleFigure,
        saveProject: saveProject,
        checkProject: checkProject,
        removeJtproject: removeJtproject,
        createJoblist: createJoblist,
        createJtproject: createJtproject,
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
