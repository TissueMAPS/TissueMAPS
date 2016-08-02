angular.module('jtui.handles')
.controller('HandlesCtrl', ['$scope', '$stateParams', 'handlesService', '$timeout', '$uibModal',
            function ($scope, $stateParams, handlesService, $timeout, $uibModal) {

    // Scope inherited from parent (project)
    var currentModuleName = $stateParams.moduleName;

    // Get the current module
    for (i in $scope.project.handles) {
        if ($scope.project.handles[i].name == currentModuleName) {
          // var currentModule = $scope.project.handles[i];
          var currentModuleIndex = i;
        }
    }
    $scope.module = $scope.project.handles[currentModuleIndex];
    $scope.source = $scope.project.pipe.description.pipeline[currentModuleIndex].source.substring(
        0, $scope.project.pipe.description.pipeline[currentModuleIndex].source.lastIndexOf('.')
    );

    // Get list of upstream output values that are available as input
    // values in the current module
    $scope.getArgList = function(arg) {
        var availableArguments = [];
        var pipeline = $scope.project.pipe.description.pipeline;
        var handles = $scope.project.handles;
        var handleNames = handles.map(function(h) {return h.name});
        for (var i in pipeline) {
            var module = pipeline[i];
            // Consider only modules upstream in the pipeline
            if (module.name == $scope.module.name) { break; }
            // Make sure we're dealing with the correct handles object
            var index = handleNames.indexOf(module.name);
            var handle = handles[index];
            for (var j in handle.description.output) {
                var upstreamOutputHandle = handle.description.output[j];
                if ('key' in upstreamOutputHandle) {
                    // Only handles with matching type
                    if (upstreamOutputHandle.key != null &&
                            upstreamOutputHandle.type == arg.type) {
                        availableArguments.push(
                            handle.description.output[j].key
                        );
                    }
                }
            }
        }
        // Also consider pipeline inputs provided by Jterator
        if (arg.type === 'IntensityImage') {
            var channels = $scope.project.pipe.description.input.channels;
            for (var i in channels) {
                availableArguments.push(channels[i].name);
            }
        }
        return availableArguments
    }

    $scope.isDuplicate = function(output_arg) {

        var allOutputs = $scope.project.handles.map(function (h) {
            return h.description.output;
        });
        allOutputs = [].concat.apply([], allOutputs);

        var identicalOutputs = _(allOutputs).filter(function (out) {
            if (!_.isNull(out)) {
                return !_.isNull(out.key) && (out.key == output_arg.key);
            }
        });

        // Channels (pipline inputs) have to be considered as well, because
        // they can also be piped.
        var isChannel = $scope.project.pipe.description.input.channels.some(
            function(channel) {
                return channel.name == output_arg.key
            }
        );

        return identicalOutputs.length > 1 || isChannel;

    }

    // Determine if input argument is of class `pipeline`
    $scope.isPipeline = function(input_arg_name) {
        for (var i in $scope.module.description.input) {
            if ($scope.module.description.input[i].name == input_arg_name) {
                if ('key' in $scope.module.description.input[i]){
                    return true;
                } else {
                    return false;
                }
            }
        }
    };

    // Determine if input argument has options
    $scope.hasOptions = function(input_arg_name) {
        for (var i in $scope.module.description.input) {
            if ($scope.module.description.input[i].name == input_arg_name) {
                if ('options' in $scope.module.description.input[i]) {
                    return true;
                } else {
                    return false;
                }
            }
        }
    };

    // Determine if input argument is a boolean and if so provide true/false option
    $scope.isBoolean = function(input_arg_name) {
        for (var i in $scope.module.description.input) {
            if ($scope.module.description.input[i].name == input_arg_name) {
                if ($scope.module.description.input[i].type == "Boolean" ||
                        $scope.module.description.input[i].type == "Plot") {
                    return true;
                } else {
                    false;
                }
            }
        }
    };
    $scope.boolOptions = [true, false]

    $scope.getHelpForModule = function(moduleName) {
        console.log('get help for module \"' + moduleName + '\"')

        // Use the name of the executable file
        var ixPipe = $scope.project.pipe.description.pipeline.map(function(e) { 
                return e.name;
            }).indexOf(moduleName);
        var moduleFilename = $scope.project.pipe.description.pipeline[ixPipe].module;
        moduleName = moduleFilename.split(/([^\/\.]+)\.\w+$/)[1];

        var modalInst = $uibModal.open({
            templateUrl: 'components/handles/modals/handlesHelp.html',
            resolve: {
                help: ['handlesService', function(handlesService){
                            return handlesService.getHelp(moduleName).then(function(helpFile) {
                                console.log(helpFile)
                                return helpFile;
                            });
                }]
            },
            controller: 'HandlesHelpCtrl'
        });

        modalInst.result.then(function() {});

    };


    $scope.convert2yaml = function(inarg, $index) {
        console.log('input value:', typeof inarg.value)
        var newinarg = jsyaml.load(inarg.value);
        console.log('converted value: '. newinarg)
        $scope.module.description.input[$index].value = newinarg;
        // console.log('input value:', typeof newinarg)
    };


}]);

