angular.module('jtui.handles')
.controller('HandlesCtrl', ['$scope', '$stateParams', 'handlesService', '$timeout', '$uibModal',
            function ($scope, $stateParams, handlesService, $timeout, $uibModal) {

    // Scope inherited from parent (project)
    var currentModuleName = $stateParams.moduleName;

    // Get the current module
    for (i in $scope.project.handles) {
        if ($scope.project.handles[i].name == currentModuleName) {
          var currentModule = $scope.project.handles[i];
          var currentModuleIndex = i;
        }
    }
    $scope.module = currentModule;

    $scope.viewProps = {
        open: {
            input: true,
            output: true,
            plot: true
        }
    };

    // Get list of upstream output values that are available as input
    // values in the current module
    $scope.getArgList = function() {
        var availableArguments = [];
        var currentModuleList = $scope.project.pipe.description.pipeline;
        var currentHandles = $scope.project.handles;
        for (var i in currentModuleList) {
            // Consider only modules upstream in the pipeline
            if (currentModuleList[i].name == currentModule.name) { break; }
            // Make sure we're dealing with the correct handles object
            for (var ii in currentHandles) {
                if (currentHandles[ii].name == currentModuleList[i].name) {
                    for (var j in currentHandles[ii].description.output) {
                        if ('key' in currentHandles[ii].description.output[j]) {
                            if (currentHandles[ii].description.output[j].key != null) {
                                availableArguments.push(currentHandles[ii].description.output[j].key);
                            }
                        }
                    }
                 }
             }
        }
        // Also consider job patterns provided by Jterator
        for (var i in $scope.project.pipe.description.input.channels) {
            // skip patterns that are not yet defined, i.e. have an empty 'name'
            // if ($scope.project.pipe.description.input.channels[i].name.length > 0) {
            availableArguments.push($scope.project.pipe.description.input.channels[i].name);
            // }
        }
        // console.log('available upstream module inputs:', availableArguments)
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

        var isChannel = $scope.project.pipe.description.input.channels.some(
                function(channel) {
                    return channel.name == output_arg.key
                }
        );

        return identicalOutputs.length > 1 || isChannel;

    }

    // Determine if input argument is of class `pipeline`
    $scope.isPipeline = function(input_arg_name) {
        for (var i in currentModule.description.input) {
            if (currentModule.description.input[i].name == input_arg_name) {
                if ('key' in currentModule.description.input[i]){
                    return true;
                } else {
                    return false;
                }
            }
        }
    };

    // Determine if input argument has options
    $scope.hasOptions = function(input_arg_name) {
        for (var i in currentModule.description.input) {
            if (currentModule.description.input[i].name == input_arg_name) {
                if ('options' in currentModule.description.input[i]) {
                    return true;
                } else {
                    return false;
                }
            }
        }
    };

    // Determine if input argument is a boolean and if so provide true/false option
    $scope.isBoolean = function(input_arg_name) {
        for (var i in currentModule.description.input) {
            if (currentModule.description.input[i].name == input_arg_name) {
                if (currentModule.description.input[i].type == "Boolean" ||
                        currentModule.description.input[i].type == "Plot") {
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

