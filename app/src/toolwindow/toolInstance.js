angular.module('tmaps.toolwindow')
.service('toolInstance', ['$http', 'tmapsProxy', '$rootScope', '$window', '$websocket', '$interval', '$timeout',
         function($http, tmapsProxy, $rootScope, $window, $websocket, $interval, $timeout) {

    var self = this;

    if (angular.isDefined($window.init)) {
        this.toolConfig = $window.init.toolInstance.config;

        var serverObject = $window.init.toolInstance.serverRepr;
        this.id = serverObject['id'];
        this.appstateId = serverObject['appstate_id'];
        this.experimentId = serverObject['experiment_id'];
        this.userId = serverObject['user_id'];
    } else {
        console.log('No tmaps object on the global scope!');
    }

    function addLayerModToViewport(viewport, layermod) {
        var layermodId = layermod.id;
        var tileUrlPrefix = '/layermods/' + layermodId + '/tiles/';

        var blackAsAlpha = layermod.render_args && layermod.render_args.black_as_alpha;
        var whiteAsAlpha = layermod.render_args && layermod.render_args.white_as_alpha;

        viewport.addLayerMod({
            name: layermod.name,
            imageSize: layermod.image_size,
            pyramidPath: tileUrlPrefix,
            drawBlackPixels: !blackAsAlpha,
            drawWhitePixels: !whiteAsAlpha
        });
    }

    this.sendRequest = function(payload) {
        var url = '/tools/' + self.toolConfig.id + '/instances/' + self.id + '/request';

        $rootScope.$broadcast('toolRequestSent');

        return $http.post(url, {
            'payload': payload
        })
        .then(
        function(resp) {
            $rootScope.$broadcast('toolRequestDone');
            $rootScope.$broadcast('toolRequestSuccess');
            return resp.data.return_value;
        },
        function(err) {
            $rootScope.$broadcast('toolRequestDone');
            $rootScope.$broadcast('toolRequestFailed', err.data);
            return err.data;
        });
    };

    var withWebsocketSupport = true;

    if (withWebsocketSupport) {
        // Create a new websocket connection using ng-websocket
        this.socket = $websocket.$new(
            'ws://' + document.domain + ':' + location.port + '/toolinstance_socket'
        );

        // After the connection has opened, send a register request to the server
        // so that he can link the socket on his side to the id of this
        // ToolInstance. This enables the serverside tool object to send
        // data to the right client.
        this.socket.$on('$open', function() {
            self.socket.$emit('register', {
                instance_id: self.id
            });
            console.log('WebSocket connection opened.');
        })
        .$on('log', function(data) {
            console.log(data);
        })
        .$on('add_layermod', function(data) {
            addLayerModToViewport(tmapsProxy.viewport, data.layermod);
        })
        .$on('$close', function () {
            console.log('WebSocket connection closed.');
        });

        // When the window is being closed, deregister the instance from the server.
        $window.onbeforeunload = function(event) {
            self.socket.$emit('deregister', {
                instance_id: self.id
            });
            self.socket.$close();
        };
    }

}]);


