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
angular.module('jtui.runner')
.service('runnerService', ['$http', '$websocket', '$q', 'projectService',
         function ($http, $websocket, $q, projectService) {


    function run(jobIds, project, debug) {

        console.log('Run jobs: ', jobIds);

        var url = '/jtui/experiments/' + project.experiment_id +
                  '/jobs/run';
        var request = $http({
            method: 'post',
            url: url,
            data: {
                project: jsyaml.safeDump(projectService.values2yaml(project)),
                job_ids: jobIds
            }
        });

        return(request.then(handleSuccess, handleError));
    }

    function getStatus(project) {

        console.log('Get status of submitted jobs...')

        var url = '/jtui/experiments/' + project.experiment_id +
                  '/jobs/status';
        var request = $http({
            method: 'post',
            url: url,
            data: {}
        });

        return(request.then(handleSuccess, handleError));
    }

    function getOutput(project) {

        console.log('Get output of submitted jobs...')

        var url = '/jtui/experiments/' + project.experiment_id +
                  '/jobs/output';
        // console.log(project)
        var request = $http({
            method: 'post',
            url: url,
            data: {
                project: jsyaml.safeDump(projectService.values2yaml(project))
            }
        });

        return(request.then(handleSuccess, handleError));
    }

    function kill(project) {

        console.log('kill submitted jobs')

        var url = '/jtui/experiments/' + project.experiment_id +
                  '/jobs/kill';
        var request = $http({
            method: 'post',
            url: url,
            data: {}
        });

        return(request.then(handleSuccess, handleError));
    }

    function handleError(response) {
        // The API response from the server should be returned in a
        // normalized format. However, if the request was not handled by the
        // server (or what not handled properly - ex. server error), then we
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

    return({
        run: run,
        kill: kill,
        getStatus: getStatus,
        getOutput: getOutput
    });

}]);
