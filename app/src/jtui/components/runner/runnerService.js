angular.module('jtui.runner')
.service('runnerService', ['$http', '$websocket', '$q', 'projectService',
         function ($http, $websocket, $q, projectService) {


    var loc = 'ws://' + document.domain + ':' + location.port + '/socket';
    console.log('Create socket: ', loc);
    var socket = $websocket.$new({
        url: loc,
        lazy: false,
        reconnect: true,
        reconnectInterval: 1000
    });

    socket.$on('$close', function () {
        console.log('Got damn it! Websocket connect closed.');
    });

    socket.$on('$open', function () {
        console.log('Websocket connection opened and registered.');
        socket.$emit('register', {});
    });
    

    function run(jobIds, project, debug) {

        console.log('Send run request to server for job #', jobIds)
        var data = {
            jobIds: jobIds,
            jtproject: jsyaml.safeDump(projectService.values2yaml(project))
        };
        console.log('Request: ', data)
        socket.$emit('run', data);
    }

    function listenToOutput() {

        console.log('Listen on output of running job...')

        var output = $q.defer();

        socket.$on('output', function (d) {
            console.log('Received: ', d);
            output.resolve(d);
        });

        return(output.promise);
    }

    function listenToStatus() {

        console.log('Listen on status of submitted jobs...')
        
        var status = $q.defer();

        socket.$on('status', function (d) {
            console.log('Received: ', d);
            status.resolve(d);
        });

        return(status.promise);
    }

    function getOutput(project) {

        console.log('Retrieve output of previous submission...')

        var request = $http({
            method: 'post',
            url: '/jtui/get_output',
            data: {
                jtproject: jsyaml.safeDump(projectService.values2yaml(project))
            }
        });

        return(request.then(handleSuccess, handleError));
    }

    function kill(project, taskId) {

        console.log('task to kill:', taskId)

        var request = $http({
            method: 'post',
            url: '/jtui/kill',
            data: {
                jtproject: jsyaml.safeDump(projectService.values2yaml(project)),
                taskId: taskId
            }
        });

        return(request.then(handleSuccess, handleError));
    }

    function submit(project) {

        var request = $http({
            method: 'post',
            url: '/jtui/submit',
            data: {
                jtproject: jsyaml.safeDump(projectService.values2yaml(project))
            }
        });

        return(request.then(handleSuccess, handleError));
    }

    return({
        run: run,
        submit: submit,
        kill: kill,
        listenToOutput: listenToOutput,
        listenToStatus: listenToStatus,
        socket: socket,
        getOutput: getOutput
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
